import logging
from datetime import datetime

logger = logging.getLogger("pcmonitor.collectors.event_logs")


def collect(last_record_id=0):
    try:
        import wmi
        c = wmi.WMI()
        events = []

        for log_source in ["System", "Application"]:
            try:
                query = (
                    f"SELECT * FROM Win32_NTLogEvent WHERE Logfile='{log_source}' "
                    f"AND (EventType=1 OR EventType=2) "
                    f"AND RecordNumber > {last_record_id}"
                )
                results = c.query(query)

                for evt in results[:50]:
                    level = "Error" if evt.EventType == 1 else "Warning"
                    occurred_at = None
                    if evt.TimeGenerated:
                        try:
                            ts = evt.TimeGenerated.split(".")[0]
                            occurred_at = datetime.strptime(ts, "%Y%m%d%H%M%S").isoformat()
                        except Exception:
                            pass

                    events.append({
                        "log_source": log_source,
                        "event_id": evt.EventCode,
                        "level": level,
                        "message": (evt.Message or "")[:500],
                        "occurred_at": occurred_at,
                        "record_id": evt.RecordNumber,
                    })
            except Exception as e:
                logger.debug(f"Error querying {log_source} log: {e}")

        events.sort(key=lambda x: x.get("record_id", 0), reverse=True)
        return events[:50]
    except Exception as e:
        logger.error(f"Event logs collection error: {e}")
        return []
