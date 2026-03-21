import logging
import socket
import time
from urllib.parse import urlparse

import psutil

logger = logging.getLogger("pcmonitor.collectors.network")


def _ping_latency(server_url):
    try:
        parsed = urlparse(server_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        start = time.time()
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        return round((time.time() - start) * 1000, 2)
    except Exception as e:
        logger.debug(f"Ping latency error: {e}")
        return None


def collect(server_url=""):
    try:
        net_io = psutil.net_io_counters()
        net_sent_mb = round(net_io.bytes_sent / (1024 ** 2), 2)
        net_recv_mb = round(net_io.bytes_recv / (1024 ** 2), 2)

        interfaces = []
        try:
            addrs = psutil.net_if_addrs()
            for iface_name, addr_list in addrs.items():
                ip = None
                mac = None
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                    elif addr.family == psutil.AF_LINK:
                        mac = addr.address
                if ip and not ip.startswith("127."):
                    interfaces.append({"name": iface_name, "ip": ip, "mac": mac})
        except Exception:
            pass

        latency = _ping_latency(server_url) if server_url else None

        active_connections = 0
        try:
            active_connections = len(psutil.net_connections())
        except (psutil.AccessDenied, OSError):
            pass

        return {
            "net_sent_mb": net_sent_mb,
            "net_recv_mb": net_recv_mb,
            "net_latency_ms": latency,
            "interfaces": interfaces,
            "active_connections": active_connections,
        }
    except Exception as e:
        logger.error(f"Network collection error: {e}")
        return {
            "net_sent_mb": None, "net_recv_mb": None,
            "net_latency_ms": None, "interfaces": [], "active_connections": 0,
        }
