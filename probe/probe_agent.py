import configparser
import json
import logging
import os
import platform
import socket
import sys
import threading
import time
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from uuid import getnode

import psutil
import requests
import win32event
import win32service
import win32serviceutil
import servicemanager

from collectors import cpu, memory, disk, network, processes, services
from collectors import event_logs, hardware, software, security

SERVICE_NAME = "PCMonitorProbe"
SERVICE_DISPLAY = "Numbers10 PC Monitor Probe"
SERVICE_DESC = "Collects system metrics and sends to Numbers10 PCMonitor server"


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def setup_logging():
    base_dir = get_base_dir()
    log_file = os.path.join(base_dir, "probe_errors.log")

    logger = logging.getLogger("pcmonitor")
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    return logger


def load_config():
    base_dir = get_base_dir()
    config = configparser.ConfigParser()
    config_path = os.path.join(base_dir, "config.ini")
    config.read(config_path)

    # Check for embedded token (baked-in builds)
    embedded_token_path = os.path.join(base_dir, "embedded_token.txt")
    if os.path.exists(embedded_token_path):
        with open(embedded_token_path, "r") as f:
            token = f.read().strip()
            if token and not config.has_option("server", "company_token"):
                config.set("server", "company_token", token)
            elif token:
                existing = config.get("server", "company_token", fallback="")
                if not existing or existing == "COMPANY_SPECIFIC_TOKEN_HERE":
                    config.set("server", "company_token", token)

    return config, config_path


def save_config(config, config_path):
    with open(config_path, "w") as f:
        config.write(f)


def get_system_info():
    mac_raw = getnode()
    mac_addr = ":".join(f"{(mac_raw >> (8 * i)) & 0xFF:02x}" for i in reversed(range(6)))

    ip_addr = "0.0.0.0"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_addr = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    cpu_model = None
    try:
        import wmi
        c = wmi.WMI()
        for proc in c.Win32_Processor():
            cpu_model = proc.Name.strip()
            break
    except Exception:
        pass

    return {
        "hostname": socket.gethostname(),
        "os_version": f"{platform.system()} {platform.release()} {platform.version()}",
        "cpu_model": cpu_model,
        "total_ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "ip_address": ip_addr,
        "mac_address": mac_addr,
    }


def register_machine(config, config_path, logger):
    server_url = config.get("server", "url")
    company_token = config.get("server", "company_token", fallback="")
    verify_ssl = config.getboolean("server", "verify_ssl", fallback=True)

    if not company_token or company_token == "COMPANY_SPECIFIC_TOKEN_HERE":
        logger.error("No company token configured. Cannot register.")
        return None

    sys_info = get_system_info()
    sys_info["company_token"] = company_token

    logger.info(f"Registering machine {sys_info['hostname']} with server {server_url}")

    try:
        resp = requests.post(
            f"{server_url}/api/machines/register",
            json=sys_info,
            verify=verify_ssl,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            api_key = data["api_key"]
            machine_id = data["machine_id"]
            config.set("server", "api_key", api_key)
            config.set("server", "machine_id", str(machine_id))
            save_config(config, config_path)
            logger.info(f"Registration successful. Machine ID: {machine_id}")
            return api_key
        else:
            logger.error(f"Registration failed: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return None


def write_status(connected, error=None):
    """Write status file for the tray app to read."""
    status_path = os.path.join(get_base_dir(), "probe_status.json")
    tmp_path = status_path + ".tmp"
    try:
        import json as _json
        data = {
            "connected": connected,
            "last_update": datetime.utcnow().isoformat(),
            "error": error,
        }
        with open(tmp_path, "w") as f:
            _json.dump(data, f)
        os.replace(tmp_path, status_path)
    except Exception:
        pass


class ProbeWorker:
    def __init__(self, config, config_path, logger):
        self.config = config
        self.config_path = config_path
        self.logger = logger
        self.running = False
        self.metric_queue = deque(maxlen=10)
        self.last_service_time = 0
        self.last_software_time = 0
        self.last_event_log_time = 0
        self.last_security_time = 0
        self.last_event_record_id = 0

        self.server_url = config.get("server", "url")
        self.api_key = config.get("server", "api_key", fallback="")
        self.machine_id = config.get("server", "machine_id", fallback="")
        self.interval = config.getint("server", "ingest_interval_seconds", fallback=30)
        self.verify_ssl = config.getboolean("server", "verify_ssl", fallback=True)
        self.use_ohm = config.getboolean("hardware", "use_open_hardware_monitor", fallback=False)

    def _headers(self):
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _post(self, endpoint, data):
        try:
            resp = requests.post(
                f"{self.server_url}{endpoint}",
                json=data,
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=30,
            )
            return resp.status_code == 200
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Connection error posting to {endpoint}")
            return False
        except Exception as e:
            self.logger.error(f"POST {endpoint} error: {e}")
            return False

    def collect_and_send_metrics(self):
        cpu_data = cpu.collect(self.use_ohm)
        mem_data = memory.collect()
        disk_data = disk.collect()
        net_data = network.collect(self.server_url)
        proc_data = processes.collect()
        hw_data = hardware.collect(self.use_ohm)

        metric = {
            "collected_at": datetime.utcnow().isoformat(),
            "cpu_percent": cpu_data.get("cpu_percent"),
            "cpu_freq_mhz": cpu_data.get("cpu_freq_mhz"),
            "cpu_temp_c": hw_data.get("cpu_temp_c") or cpu_data.get("cpu_temp_c"),
            "ram_percent": mem_data.get("ram_percent"),
            "ram_used_gb": mem_data.get("ram_used_gb"),
            "ram_total_gb": mem_data.get("ram_total_gb"),
            "disk_usage": disk_data,
            "net_sent_mb": net_data.get("net_sent_mb"),
            "net_recv_mb": net_data.get("net_recv_mb"),
            "net_latency_ms": net_data.get("net_latency_ms"),
            "top_processes": proc_data,
            "gpu_percent": hw_data.get("gpu_percent"),
            "gpu_temp_c": hw_data.get("gpu_temp_c"),
            "gpu_vram_used_mb": hw_data.get("gpu_vram_used_mb"),
        }

        if self.metric_queue:
            batch = list(self.metric_queue)
            batch.append(metric)
            if self._post("/api/metrics/ingest/batch", {"metrics": batch}):
                self.metric_queue.clear()
                self.logger.info(f"Batch sent {len(batch)} queued metrics")
                write_status(True)
            else:
                self.metric_queue.append(metric)
                write_status(False, "Connection failed")
        else:
            if not self._post("/api/metrics/ingest", metric):
                self.metric_queue.append(metric)
                self.logger.warning("Metric queued for retry")
                write_status(False, "Connection failed")
            else:
                write_status(True)

    def collect_services(self):
        now = time.time()
        if now - self.last_service_time < 300:
            return
        self.last_service_time = now

        svc_data = services.collect()
        if svc_data and self.machine_id:
            self._post(f"/api/machines/{self.machine_id}/services", svc_data)
            self.logger.info(f"Sent {len(svc_data)} services")

    def collect_software(self):
        now = time.time()
        if now - self.last_software_time < 86400:
            return
        self.last_software_time = now

        sw_data = software.collect()
        if sw_data and self.machine_id:
            self._post(f"/api/machines/{self.machine_id}/software", sw_data)
            self.logger.info(f"Sent {len(sw_data)} software items")

    def collect_event_logs(self):
        now = time.time()
        if now - self.last_event_log_time < 300:
            return
        self.last_event_log_time = now

        events = event_logs.collect(self.last_event_record_id)
        if events and self.machine_id:
            max_id = max(e.get("record_id", 0) for e in events)
            if max_id > self.last_event_record_id:
                self.last_event_record_id = max_id
            clean_events = [
                {k: v for k, v in e.items() if k != "record_id"} for e in events
            ]
            self._post(f"/api/machines/{self.machine_id}/event-logs", clean_events)
            self.logger.info(f"Sent {len(events)} event logs")

    def collect_security(self):
        now = time.time()
        if now - self.last_security_time < 300:
            return
        self.last_security_time = now
        security.collect()

    def run(self):
        self.running = True
        self.logger.info("Probe worker started")

        # Initial software scan
        self.collect_software()

        while self.running:
            try:
                self.collect_and_send_metrics()
                self.collect_services()
                self.collect_event_logs()
                self.collect_security()
            except Exception as e:
                self.logger.error(f"Collection cycle error: {e}")

            for _ in range(self.interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.running = False
        write_status(False, "Service stopping")
        if self.metric_queue:
            self.logger.info(f"Flushing {len(self.metric_queue)} queued metrics")
            batch = list(self.metric_queue)
            self._post("/api/metrics/ingest/batch", {"metrics": batch})


class PCMonitorProbeService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY
    _svc_description_ = SERVICE_DESC

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.worker = None
        self.worker_thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.worker:
            self.worker.stop()
        if self.worker_thread:
            self.worker_thread.join(timeout=10)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        logger = setup_logging()
        logger.info("PCMonitor Probe service starting...")

        try:
            config, config_path = load_config()

            api_key = config.get("server", "api_key", fallback="")
            if not api_key:
                api_key = register_machine(config, config_path, logger)
                if not api_key:
                    logger.error("Failed to register. Service will retry on next start.")
                    return
                config, config_path = load_config()

            self.worker = ProbeWorker(config, config_path, logger)
            self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
            self.worker_thread.start()

            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        except Exception as e:
            logger.error(f"Service error: {e}")
            servicemanager.LogErrorMsg(f"PCMonitor Probe error: {e}")


def run_standalone():
    """Run probe as a standalone script (not as a Windows Service)."""
    logger = setup_logging()
    logger.info("Running PCMonitor Probe in standalone mode...")

    config, config_path = load_config()

    api_key = config.get("server", "api_key", fallback="")
    if not api_key:
        api_key = register_machine(config, config_path, logger)
        if not api_key:
            logger.error("Failed to register machine.")
            return
        config, config_path = load_config()

    worker = ProbeWorker(config, config_path, logger)
    try:
        worker.run()
    except KeyboardInterrupt:
        worker.stop()
        logger.info("Probe stopped by user")


def run_setup_wizard():
    """Interactive configuration wizard — runs when exe is double-clicked."""
    # Load existing config (includes embedded_token.txt if present)
    config, config_path = load_config()
    existing_url = config.get("server", "url", fallback="https://your-vps.com:8443")
    existing_token = config.get("server", "company_token", fallback="")
    existing_ssl = config.getboolean("server", "verify_ssl", fallback=True)

    has_valid_url = existing_url and existing_url != "https://your-vps.com:8443"
    has_valid_token = existing_token and existing_token != "COMPANY_SPECIFIC_TOKEN_HERE"

    # ── Auto-install mode ────────────────────────────────────────────────────
    # If a token is already baked in (downloaded from the dashboard), skip the
    # interactive wizard entirely and go straight to service installation.
    if has_valid_token and has_valid_url:
        print()
        print("=" * 55)
        print("  Numbers10 PCMonitor Probe — Auto Install")
        print("=" * 55)
        print()
        print(f"  Server : {existing_url}")
        print(f"  Token  : {existing_token[:8]}...{existing_token[-4:]}")
        print()
        print("  Installing service...")
        try:
            sys.argv = [sys.argv[0], "install"]
            win32serviceutil.HandleCommandLine(PCMonitorProbeService)
        except Exception as e:
            print(f"  Error: {e}")
            print("  Make sure you run as Administrator!")
        print()
        print("  Starting service...")
        try:
            time.sleep(1)
            win32serviceutil.StartService(SERVICE_NAME)
            time.sleep(2)
            status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            if status[1] == 4:
                print("  Service is running!")
            else:
                print("  Service may still be starting...")
        except Exception as e:
            print(f"  Could not start service: {e}")
            print("  Try: net start PCMonitorProbe")
        print()
        tray_path = os.path.join(get_base_dir(), "PCMonitorTray.exe")
        if os.path.exists(tray_path):
            try:
                import subprocess
                subprocess.Popen([tray_path], creationflags=0x00000008)
                print("  Tray icon started.")
            except Exception:
                pass
        print("=" * 55)
        print("  Setup complete!")
        print("=" * 55)
        input("\n  Press Enter to exit...")
        return
    # ── Interactive wizard ───────────────────────────────────────────────────

    print()
    print("=" * 55)
    print("  Numbers10 PCMonitor Probe — Setup Wizard")
    print("=" * 55)
    print()

    # Step 1: Server URL
    print("  Step 1: Server URL")
    print(f"    Current: {existing_url}")
    url = input(f"    Enter server URL [{existing_url}]: ").strip()
    if not url:
        url = existing_url
    if not url.startswith("http"):
        url = "https://" + url
    print()

    # Step 2: Company Token
    print("  Step 2: Company Token")
    print("    (Copy from the dashboard: Downloads > select company > Build & Download)")
    if existing_token and existing_token != "COMPANY_SPECIFIC_TOKEN_HERE":
        print(f"    Current: {existing_token[:8]}...{existing_token[-4:]}")
        token = input(f"    Enter token [keep existing]: ").strip()
        if not token:
            token = existing_token
    else:
        token = ""
        while not token:
            token = input("    Enter company token: ").strip()
            if not token:
                print("    Token is required!")
    print()

    # Step 3: SSL verification
    print("  Step 3: SSL Certificate Verification")
    ssl_default = "Y" if existing_ssl else "N"
    ssl_input = input(f"    Verify SSL? (Y/n) [{ssl_default}]: ").strip().lower()
    if ssl_input == "n":
        verify_ssl = False
        print("    SSL verification disabled (for self-signed certs)")
    else:
        verify_ssl = True
    print()

    # Step 4: Test connection
    print("  Testing connection...")
    try:
        resp = requests.get(
            f"{url}/api/health",
            verify=verify_ssl,
            timeout=10,
        )
        if resp.status_code == 200:
            print("    Connection successful!")
        else:
            print(f"    Server responded with {resp.status_code}")
    except requests.exceptions.SSLError:
        print("    SSL error! If using self-signed certs, set verify_ssl = N")
        if verify_ssl:
            retry = input("    Disable SSL verification? (y/N): ").strip().lower()
            if retry == "y":
                verify_ssl = False
                print("    SSL verification disabled.")
    except requests.exceptions.ConnectionError:
        print(f"    Could not connect to {url}")
        print("    The service will retry once started.")
    except Exception as e:
        print(f"    Connection test failed: {e}")
    print()

    # Step 5: Save config
    if not config.has_section("server"):
        config.add_section("server")
    config.set("server", "url", url)
    config.set("server", "company_token", token)
    config.set("server", "verify_ssl", str(verify_ssl).lower())
    if not config.has_option("server", "ingest_interval_seconds"):
        config.set("server", "ingest_interval_seconds", "30")
    if not config.has_section("hardware"):
        config.add_section("hardware")
    if not config.has_option("hardware", "use_open_hardware_monitor"):
        config.set("hardware", "use_open_hardware_monitor", "false")

    save_config(config, config_path)
    print("  Configuration saved!")
    print()

    # Step 6: Install service
    install = input("  Install as Windows Service now? (Y/n): ").strip().lower()
    if install != "n":
        print()
        print("  Installing service...")
        try:
            sys.argv = [sys.argv[0], "install"]
            win32serviceutil.HandleCommandLine(PCMonitorProbeService)
        except Exception as e:
            print(f"  Error: {e}")
            print("  Make sure you run as Administrator!")
        print()

        # Auto-start the service
        print("  Starting service...")
        try:
            time.sleep(1)
            win32serviceutil.StartService(SERVICE_NAME)
            time.sleep(2)
            status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            if status[1] == 4:  # SERVICE_RUNNING
                print("  Service is running!")
            else:
                print("  Service may still be starting...")
        except Exception as e:
            print(f"  Could not start service: {e}")
            print("  Try: net start PCMonitorProbe")
        print()

        # Step 7: Add tray app to startup and launch it
        tray_path = os.path.join(get_base_dir(), "PCMonitorTray.exe")
        if os.path.exists(tray_path):
            add_tray = input("  Add system tray monitor to Windows startup? (Y/n): ").strip().lower()
            if add_tray != "n":
                try:
                    import winreg
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                        0, winreg.KEY_SET_VALUE,
                    )
                    winreg.SetValueEx(key, "PCMonitorTray", 0, winreg.REG_SZ, tray_path)
                    winreg.CloseKey(key)
                    print("  Tray app added to startup!")
                except Exception as e:
                    print(f"  Could not add to startup: {e}")

                # Launch tray app now
                print("  Launching tray monitor...")
                try:
                    import subprocess
                    subprocess.Popen(
                        [tray_path],
                        creationflags=0x00000008,  # DETACHED_PROCESS
                    )
                    print("  Tray icon should appear by the clock.")
                except Exception as e:
                    print(f"  Could not launch tray: {e}")
                print()
    else:
        print()
        print(f"  Run '{os.path.basename(sys.executable)} install' as Admin to install later.")
        print()

    print("=" * 55)
    print("  Setup complete!")
    print("=" * 55)
    input("\n  Press Enter to exit...")


if __name__ == "__main__":
    if "--standalone" in sys.argv:
        run_standalone()
    elif len(sys.argv) == 1:
        # Double-clicked or run without args — detect if launched by SCM
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(PCMonitorProbeService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception:
            # Not launched by SCM — run the setup wizard
            run_setup_wizard()
    else:
        win32serviceutil.HandleCommandLine(PCMonitorProbeService)
