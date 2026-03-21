import logging
import psutil

logger = logging.getLogger("pcmonitor.collectors.cpu")

_cpu_model_cache = None


def _get_cpu_model():
    global _cpu_model_cache
    if _cpu_model_cache:
        return _cpu_model_cache
    try:
        import wmi
        c = wmi.WMI()
        for proc in c.Win32_Processor():
            _cpu_model_cache = proc.Name.strip()
            return _cpu_model_cache
    except Exception as e:
        logger.debug(f"Could not get CPU model via WMI: {e}")
    return None


def _get_cpu_temp(use_ohm=False):
    try:
        import wmi
        if use_ohm:
            try:
                c = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                for sensor in c.Sensor():
                    if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                        return float(sensor.Value)
            except Exception:
                pass
        c = wmi.WMI()
        for temp in c.query("SELECT * FROM Win32_TemperatureProbe"):
            if temp.CurrentReading:
                return float(temp.CurrentReading) / 10.0
    except Exception as e:
        logger.debug(f"Could not get CPU temperature: {e}")
    return None


def collect(use_ohm=False):
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(percpu=True)

        freq = psutil.cpu_freq()
        cpu_freq_mhz = freq.current if freq else None

        cpu_temp = _get_cpu_temp(use_ohm)
        cpu_model = _get_cpu_model()

        return {
            "cpu_percent": cpu_percent,
            "cpu_percent_per_core": cpu_per_core,
            "cpu_freq_mhz": cpu_freq_mhz,
            "cpu_temp_c": cpu_temp,
            "cpu_model": cpu_model,
        }
    except Exception as e:
        logger.error(f"CPU collection error: {e}")
        return {
            "cpu_percent": None,
            "cpu_percent_per_core": [],
            "cpu_freq_mhz": None,
            "cpu_temp_c": None,
            "cpu_model": None,
        }
