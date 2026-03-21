import logging
import psutil

logger = logging.getLogger("pcmonitor.collectors.memory")


def collect():
    try:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "ram_percent": vm.percent,
            "ram_used_gb": round(vm.used / (1024 ** 3), 2),
            "ram_total_gb": round(vm.total / (1024 ** 3), 2),
            "swap_percent": swap.percent,
            "swap_used_gb": round(swap.used / (1024 ** 3), 2),
            "swap_total_gb": round(swap.total / (1024 ** 3), 2),
        }
    except Exception as e:
        logger.error(f"Memory collection error: {e}")
        return {
            "ram_percent": None, "ram_used_gb": None, "ram_total_gb": None,
            "swap_percent": None, "swap_used_gb": None, "swap_total_gb": None,
        }
