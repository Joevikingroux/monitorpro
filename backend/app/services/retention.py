import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.database import async_session
from app.models.metric import Metric
from app.models.machine import Machine
from app.models.company import Company

logger = logging.getLogger("pcmonitor.retention")


async def run_retention_cleanup():
    try:
        async with async_session() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=settings.RETENTION_DAYS)

            count_result = await db.execute(
                select(func.count(Metric.id)).where(Metric.collected_at < cutoff)
            )
            count = count_result.scalar() or 0

            if count > 0:
                await db.execute(delete(Metric).where(Metric.collected_at < cutoff))
                await db.commit()
                logger.info(f"Retention cleanup: deleted {count} metrics older than {cutoff}")
            else:
                logger.info("Retention cleanup: no old metrics to delete")

            # Clean up data for deactivated companies older than retention period
            inactive_result = await db.execute(
                select(Company).where(Company.is_active == False)  # noqa: E712
            )
            for company in inactive_result.scalars().all():
                machine_result = await db.execute(
                    select(Machine).where(Machine.company_id == company.id)
                )
                for machine in machine_result.scalars().all():
                    metric_count = await db.execute(
                        select(func.count(Metric.id)).where(
                            Metric.machine_id == machine.id,
                            Metric.collected_at < cutoff,
                        )
                    )
                    old_count = metric_count.scalar() or 0
                    if old_count > 0:
                        await db.execute(
                            delete(Metric).where(
                                Metric.machine_id == machine.id,
                                Metric.collected_at < cutoff,
                            )
                        )
                        logger.info(
                            f"Cleaned {old_count} old metrics for deactivated company "
                            f"{company.name}, machine {machine.hostname}"
                        )
            await db.commit()

    except Exception as e:
        logger.error(f"Retention cleanup error: {e}")
