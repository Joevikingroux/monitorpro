import logging
from datetime import datetime

import psutil

logger = logging.getLogger("pcmonitor.collectors.security")


def _get_firewall_status():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile",
        )
        value, _ = winreg.QueryValueEx(key, "EnableFirewall")
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        pass
    return None


def _get_antivirus_status():
    try:
        import wmi
        c = wmi.WMI(namespace="root\\SecurityCenter2")
        products = []
        for av in c.AntiVirusProduct():
            state = av.productState
            enabled = bool((state >> 12) & 0x1)
            products.append({
                "name": av.displayName,
                "enabled": enabled,
            })
        return products
    except Exception as e:
        logger.debug(f"Could not get AV status: {e}")
        return []


def _get_pending_updates():
    try:
        import wmi
        c = wmi.WMI()
        hotfixes = c.Win32_QuickFixEngineering()
        return len(hotfixes)
    except Exception:
        return 0


def collect():
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()

        return {
            "firewall_enabled": _get_firewall_status(),
            "antivirus_status": _get_antivirus_status(),
            "installed_updates_count": _get_pending_updates(),
            "last_boot_time": boot_time,
        }
    except Exception as e:
        logger.error(f"Security collection error: {e}")
        return {
            "firewall_enabled": None,
            "antivirus_status": [],
            "installed_updates_count": 0,
            "last_boot_time": None,
        }
