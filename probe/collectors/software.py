import logging

logger = logging.getLogger("pcmonitor.collectors.software")

UNINSTALL_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]


def collect():
    try:
        import winreg
        software = []
        seen = set()

        for hive_path in UNINSTALL_KEYS:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, hive_path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)

                        name = _read_value(subkey, "DisplayName")
                        if not name or name in seen:
                            winreg.CloseKey(subkey)
                            continue
                        seen.add(name)

                        software.append({
                            "name": name,
                            "version": _read_value(subkey, "DisplayVersion"),
                            "publisher": _read_value(subkey, "Publisher"),
                            "install_date": _read_value(subkey, "InstallDate"),
                        })
                        winreg.CloseKey(subkey)
                    except (OSError, WindowsError):
                        continue
                winreg.CloseKey(key)
            except (OSError, WindowsError) as e:
                logger.debug(f"Could not open registry key {hive_path}: {e}")

        software.sort(key=lambda x: x["name"].lower())
        return software
    except Exception as e:
        logger.error(f"Software collection error: {e}")
        return []


def _read_value(key, name):
    try:
        import winreg
        value, _ = winreg.QueryValueEx(key, name)
        return str(value).strip() if value else None
    except (OSError, WindowsError):
        return None
