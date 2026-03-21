from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.machine import Machine
from app.models.company import Company
from app.models.alert import AlertRule, AlertEvent
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse, AlertEventResponse,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_rules(
    company_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlertRule)
    if company_id:
        query = query.where(
            (AlertRule.company_id == company_id) | (AlertRule.company_id == None)  # noqa: E711
        )
    result = await db.execute(query)
    rules = result.scalars().all()

    responses = []
    for r in rules:
        machine_name = None
        company_name = None
        if r.machine_id:
            m_result = await db.execute(select(Machine).where(Machine.id == r.machine_id))
            machine = m_result.scalar_one_or_none()
            machine_name = machine.hostname if machine else None
        if r.company_id:
            c_result = await db.execute(select(Company).where(Company.id == r.company_id))
            company = c_result.scalar_one_or_none()
            company_name = company.name if company else None

        responses.append(AlertRuleResponse(
            **{c.name: getattr(r, c.name) for c in AlertRule.__table__.columns},
            machine_name=machine_name,
            company_name=company_name,
        ))
    return responses


@router.post("/rules", response_model=AlertRuleResponse)
async def create_rule(
    request: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = AlertRule(**request.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return AlertRuleResponse(
        **{c.name: getattr(rule, c.name) for c in AlertRule.__table__.columns},
    )


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: int,
    request: AlertRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return AlertRuleResponse(
        **{c.name: getattr(rule, c.name) for c in AlertRule.__table__.columns},
    )


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    # Delete associated events first to avoid NOT NULL FK constraint error
    await db.execute(delete(AlertEvent).where(AlertEvent.rule_id == rule_id))
    await db.delete(rule)
    return {"message": "Rule deleted"}


@router.get("/events")
async def list_events(
    machine_id: Optional[int] = None,
    company_id: Optional[int] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlertEvent).join(AlertRule).join(
        Machine, AlertEvent.machine_id == Machine.id
    ).join(Company, Machine.company_id == Company.id)

    if machine_id:
        query = query.where(AlertEvent.machine_id == machine_id)
    if company_id:
        query = query.where(Machine.company_id == company_id)
    if severity:
        query = query.where(AlertRule.severity == severity)
    if acknowledged is not None:
        query = query.where(AlertEvent.acknowledged == acknowledged)  # noqa: E712
    if from_dt:
        query = query.where(AlertEvent.triggered_at >= from_dt)
    if to_dt:
        query = query.where(AlertEvent.triggered_at <= to_dt)

    query = query.order_by(AlertEvent.triggered_at.desc()).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    responses = []
    for e in events:
        rule_result = await db.execute(select(AlertRule).where(AlertRule.id == e.rule_id))
        rule = rule_result.scalar_one_or_none()
        machine_result = await db.execute(
            select(Machine).options(selectinload(Machine.company)).where(Machine.id == e.machine_id)
        )
        machine = machine_result.scalar_one_or_none()

        responses.append(AlertEventResponse(
            id=e.id, rule_id=e.rule_id, machine_id=e.machine_id,
            triggered_at=e.triggered_at, resolved_at=e.resolved_at,
            current_value=e.current_value, message=e.message,
            acknowledged=e.acknowledged, acknowledged_by=e.acknowledged_by,
            machine_name=machine.hostname if machine else None,
            rule_name=rule.name if rule else None,
            severity=rule.severity if rule else None,
            company_name=machine.company.name if machine and machine.company else None,
        ))
    return responses


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertEvent).where(AlertEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    return {"message": "Event deleted"}


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertEvent).where(AlertEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.acknowledged = True
    event.acknowledged_by = current_user.email
    db.add(event)
    return {"message": "Alert acknowledged"}


@router.post("/test/email")
async def test_email(
    current_user: User = Depends(get_current_user),
):
    from app.core.config import settings
    if not settings.SMTP_HOST:
        raise HTTPException(status_code=400, detail="SMTP_HOST not configured in .env")
    if not settings.ALERT_EMAIL:
        raise HTTPException(status_code=400, detail="ALERT_EMAIL not configured in .env")
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Numbers10 PCMonitor — Test Email"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = settings.ALERT_EMAIL
        msg.attach(MIMEText(
            "<html><body style='background:#000;color:#94a3b8;font-family:Inter,sans-serif;padding:20px;'>"
            "<div style='max-width:500px;margin:0 auto;background:rgba(10,18,32,0.9);"
            "border:1px solid rgba(45,212,191,0.3);border-radius:12px;padding:24px;'>"
            "<h2 style='color:#2dd4bf;margin:0 0 12px;'>✓ Test Email</h2>"
            "<p style='color:#94a3b8;'>Your Numbers10 PCMonitor email notifications are working correctly.</p>"
            "</div></body></html>",
            "html"
        ))
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_PORT == 465,
            start_tls=settings.SMTP_PORT == 587,
        )
        return {"message": f"Test email sent to {settings.ALERT_EMAIL}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/telegram")
async def test_telegram(
    current_user: User = Depends(get_current_user),
):
    from app.core.config import settings
    if not settings.TELEGRAM_TOKEN:
        raise HTTPException(status_code=400, detail="TELEGRAM_TOKEN not configured in .env")
    if not settings.TELEGRAM_CHAT_ID:
        raise HTTPException(status_code=400, detail="TELEGRAM_CHAT_ID not configured in .env")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": "✅ <b>Numbers10 PCMonitor</b>\n\nTest message — Telegram notifications are working correctly.",
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
        if resp.status_code == 200:
            return {"message": "Test Telegram message sent"}
        raise HTTPException(status_code=500, detail=f"Telegram API error: {resp.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/unresolved")
async def unresolved_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count(AlertEvent.id)).where(
            AlertEvent.resolved_at == None,  # noqa: E711
            AlertEvent.acknowledged == False,  # noqa: E712
        )
    )
    count = result.scalar()

    critical_result = await db.execute(
        select(func.count(AlertEvent.id))
        .join(AlertRule)
        .where(
            AlertEvent.resolved_at == None,  # noqa: E711
            AlertEvent.acknowledged == False,  # noqa: E712
            AlertRule.severity == "critical",
        )
    )
    critical_count = critical_result.scalar()

    return {"total": count, "critical": critical_count}
