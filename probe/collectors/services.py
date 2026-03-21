import logging

logger = logging.getLogger("pcmonitor.collectors.services")


def collect():
    try:
        import wmi
        c = wmi.WMI()
        services = []
        for svc in c.Win32_Service():
            services.append({
                "service_name": svc.Name,
                "display_name": svc.DisplayName,
                "status": svc.State,
                "startup_type": svc.StartMode,
            })
        return services
    except Exception as e:
        logger.error(f"Services collection error: {e}")
        return []
