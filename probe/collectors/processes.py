import logging
import psutil

logger = logging.getLogger("pcmonitor.collectors.processes")


def collect():
    try:
        procs = []
        for proc in psutil.process_iter(["name", "pid", "cpu_percent", "memory_info", "status"]):
            try:
                info = proc.info
                if info["name"] and info["name"].lower() != "system idle process":
                    procs.append({
                        "name": info["name"],
                        "pid": info["pid"],
                        "cpu_percent": info["cpu_percent"] or 0.0,
                        "ram_mb": round(info["memory_info"].rss / (1024 ** 2), 1) if info["memory_info"] else 0,
                        "status": info["status"] or "unknown",
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        top_cpu = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:10]
        top_ram = sorted(procs, key=lambda x: x["ram_mb"], reverse=True)[:10]

        combined = {p["pid"]: p for p in top_cpu}
        for p in top_ram:
            combined[p["pid"]] = p

        return list(combined.values())[:20]
    except Exception as e:
        logger.error(f"Process collection error: {e}")
        return []
