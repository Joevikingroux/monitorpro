"""
Numbers10 PCMonitor Probe — Windows Service Installer

Usage:
    python installer.py install    — Install and start the service
    python installer.py remove     — Stop and uninstall the service
    python installer.py start      — Start the service
    python installer.py stop       — Stop the service
    python installer.py restart    — Restart the service
"""
import sys
import os
import time

import win32serviceutil
import win32service
import win32api


def install_service():
    print("Installing PCMonitorProbe service...")
    try:
        # Get the path to probe_agent.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        agent_path = os.path.join(base_dir, "probe_agent.py")

        if getattr(sys, "frozen", False):
            # Running as compiled exe
            exe_path = sys.executable
            win32serviceutil.InstallService(
                None,
                "PCMonitorProbe",
                "Numbers10 PC Monitor Probe",
                startType=win32service.SERVICE_AUTO_START,
                exeName=exe_path,
                description="Collects system metrics and sends to Numbers10 PCMonitor server",
            )
        else:
            # Running as Python script
            sys.argv = [agent_path, "install"]
            from probe_agent import PCMonitorProbeService
            win32serviceutil.HandleCommandLine(PCMonitorProbeService)
            return

        print("Service installed successfully.")

        # Start the service
        print("Starting service...")
        try:
            win32serviceutil.StartService("PCMonitorProbe")
            print("Service started.")
        except Exception as e:
            print(f"Could not auto-start service: {e}")
            print("Start manually: net start PCMonitorProbe")

    except Exception as e:
        print(f"Installation error: {e}")
        sys.exit(1)


def remove_service():
    print("Stopping PCMonitorProbe service...")
    try:
        win32serviceutil.StopService("PCMonitorProbe")
        time.sleep(2)
    except Exception:
        pass

    print("Removing PCMonitorProbe service...")
    try:
        if getattr(sys, "frozen", False):
            win32serviceutil.RemoveService("PCMonitorProbe")
        else:
            from probe_agent import PCMonitorProbeService
            sys.argv = [sys.argv[0], "remove"]
            win32serviceutil.HandleCommandLine(PCMonitorProbeService)
            return
        print("Service removed successfully.")
    except Exception as e:
        print(f"Removal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "install":
        install_service()
    elif command == "remove":
        remove_service()
    elif command in ("start", "stop", "restart"):
        from probe_agent import PCMonitorProbeService
        win32serviceutil.HandleCommandLine(PCMonitorProbeService)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
