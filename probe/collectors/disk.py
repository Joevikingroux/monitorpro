import logging
import psutil

logger = logging.getLogger("pcmonitor.collectors.disk")


def _get_smart_status():
    statuses = {}
    try:
        import wmi
        c = wmi.WMI()
        for disk in c.Win32_DiskDrive():
            statuses[disk.Index] = disk.Status or "Unknown"
    except Exception as e:
        logger.debug(f"Could not get SMART status: {e}")
    return statuses


def collect():
    try:
        drives = []
        partitions = psutil.disk_partitions(all=False)
        io_counters = {}
        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
        except Exception:
            pass

        for p in partitions:
            if "cdrom" in p.opts.lower() or p.fstype == "":
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                drive_letter = p.mountpoint.rstrip("\\")

                read_mb = 0.0
                write_mb = 0.0
                for disk_name, counters in io_counters.items():
                    read_mb += counters.read_bytes / (1024 ** 2)
                    write_mb += counters.write_bytes / (1024 ** 2)

                drives.append({
                    "drive": drive_letter,
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "percent": usage.percent,
                    "read_mb": round(read_mb, 2),
                    "write_mb": round(write_mb, 2),
                })
            except (PermissionError, OSError) as e:
                logger.debug(f"Skipping {p.mountpoint}: {e}")
                continue

        return drives
    except Exception as e:
        logger.error(f"Disk collection error: {e}")
        return []
