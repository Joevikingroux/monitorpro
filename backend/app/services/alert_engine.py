import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.machine import Machine
from app.models.metric import Metric
from app.models.alert import AlertRule, AlertEvent

logger = logging.getLogger("pcmonitor.alert_engine")

# Track breach start times: {(rule_id, machine_id): first_breach_time}
_breach_tracker: dict = {}


async def run_alert_check():
    try:
        async with async_session() as db:
            await _check_machine_online_status(db)
            await _evaluate_alert_rules(db)
            await db.commit()
    except Exception as e:
        logger.error(f"Alert engine error: {e}")


async def _check_machine_online_status(db: AsyncSession):
    threshold = datetime.now(timezone.utc) - timedelta(minutes=3)
    result = await db.execute(
        select(Machine).where(Machine.is_online == True, Machine.last_seen < threshold)  # noqa: E712
    )
    for machine in result.scalars().all():
        machine.is_online = False
        db.add(machine)
        logger.info(f"Machine {machine.hostname} marked offline (last seen: {machine.last_seen})")


async def _evaluate_alert_rules(db: AsyncSession):
    from app.services.notifier import send_alert_notification

    result = await db.execute(select(AlertRule).where(AlertRule.enabled == True))  # noqa: E712
    rules = result.scalars().all()

    for rule in rules:
        machines = await _get_applicable_machines(db, rule)
        for machine in machines:
            latest = await _get_latest_metric(db, machine.id)
            if not latest:
                continue

            value = _get_metric_value(latest, rule.metric_field)
            if value is None:
                continue

            breached = _evaluate_condition(value, rule.operator, rule.threshold)
            key = (rule.id, machine.id)

            if breached:
                if key not in _breach_tracker:
                    _breach_tracker[key] = datetime.now(timezone.utc)

                elapsed = (datetime.now(timezone.utc) - _breach_tracker[key]).total_seconds()
                if elapsed >= rule.duration_seconds:
                    existing = await db.execute(
                        select(AlertEvent).where(
                            AlertEvent.rule_id == rule.id,
                            AlertEvent.machine_id == machine.id,
                            AlertEvent.resolved_at == None,  # noqa: E711
                        )
                    )
                    if not existing.scalar_one_or_none():
                        event = AlertEvent(
                            rule_id=rule.id,
                            machine_id=machine.id,
                            current_value=value,
                            message=f"{rule.name}: {rule.metric_field} is {value} "
                                    f"({rule.operator} {rule.threshold})",
                        )
                        db.add(event)
                        logger.warning(
                            f"Alert triggered: {rule.name} on {machine.hostname} "
                            f"({rule.metric_field}={value})"
                        )
                        try:
                            await send_alert_notification(db, rule, machine, value)
                        except Exception as e:
                            logger.error(f"Notification error: {e}")
            else:
                _breach_tracker.pop(key, None)
                unresolved = await db.execute(
                    select(AlertEvent).where(
                        AlertEvent.rule_id == rule.id,
                        AlertEvent.machine_id == machine.id,
                        AlertEvent.resolved_at == None,  # noqa: E711
                    )
                )
                for event in unresolved.scalars().all():
                    event.resolved_at = datetime.now(timezone.utc)
                    db.add(event)
                    logger.info(f"Alert auto-resolved: {rule.name} on {machine.hostname}")


async def _get_applicable_machines(db: AsyncSession, rule: AlertRule):
    query = select(Machine).where(Machine.is_online == True)  # noqa: E712
    if rule.machine_id:
        query = query.where(Machine.id == rule.machine_id)
    elif rule.company_id:
        query = query.where(Machine.company_id == rule.company_id)
    result = await db.execute(query)
    return result.scalars().all()


async def _get_latest_metric(db: AsyncSession, machine_id: int):
    result = await db.execute(
        select(Metric)
        .where(Metric.machine_id == machine_id)
        .order_by(Metric.collected_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _get_metric_value(metric: Metric, field: str):
    if hasattr(metric, field):
        return getattr(metric, field)
    if field == "disk_percent" and metric.disk_usage:
        max_pct = max((d.get("percent", 0) for d in metric.disk_usage), default=None)
        return max_pct
    return None


def _evaluate_condition(value: float, operator: str, threshold: float) -> bool:
    if operator == "gt":
        return value > threshold
    elif operator == "lt":
        return value < threshold
    elif operator == "eq":
        return value == threshold
    return False
