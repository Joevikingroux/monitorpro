import logging

logger = logging.getLogger("pcmonitor.collectors.hardware")


def _get_gpu_info():
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        pynvml.nvmlShutdown()
        return {
            "gpu_percent": util.gpu,
            "gpu_temp_c": temp,
            "gpu_vram_used_mb": round(mem.used / (1024 ** 2), 1),
        }
    except Exception as e:
        logger.debug(f"GPU info unavailable (not NVIDIA or pynvml missing): {e}")
        return {"gpu_percent": None, "gpu_temp_c": None, "gpu_vram_used_mb": None}


def _get_cpu_temp_ohm():
    try:
        import wmi
        c = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        for sensor in c.Sensor():
            if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                return float(sensor.Value)
    except Exception:
        pass
    return None


def _get_cpu_temp_wmi():
    try:
        import wmi
        c = wmi.WMI()
        for temp in c.query("SELECT * FROM Win32_TemperatureProbe"):
            if temp.CurrentReading:
                return float(temp.CurrentReading) / 10.0
    except Exception:
        pass
    return None


def _get_fan_speeds():
    try:
        import wmi
        c = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        fans = []
        for sensor in c.Sensor():
            if sensor.SensorType == "Fan":
                fans.append({"name": sensor.Name, "rpm": sensor.Value})
        return fans
    except Exception:
        return []


def collect(use_ohm=False):
    try:
        cpu_temp = None
        if use_ohm:
            cpu_temp = _get_cpu_temp_ohm()
        if cpu_temp is None:
            cpu_temp = _get_cpu_temp_wmi()

        gpu = _get_gpu_info()
        fans = _get_fan_speeds() if use_ohm else []

        return {
            "cpu_temp_c": cpu_temp,
            "gpu_percent": gpu["gpu_percent"],
            "gpu_temp_c": gpu["gpu_temp_c"],
            "gpu_vram_used_mb": gpu["gpu_vram_used_mb"],
            "fan_speeds": fans,
        }
    except Exception as e:
        logger.error(f"Hardware collection error: {e}")
        return {
            "cpu_temp_c": None, "gpu_percent": None,
            "gpu_temp_c": None, "gpu_vram_used_mb": None, "fan_speeds": [],
        }
