import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.metric import Metric
from app.models.alert import AlertEvent, AlertRule
from app.models.machine import Machine

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/machine/{machine_id}")
async def export_machine_metrics(
    machine_id: int,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Metric).where(Metric.machine_id == machine_id)
    if from_dt:
        query = query.where(Metric.collected_at >= from_dt)
    if to_dt:
        query = query.where(Metric.collected_at <= to_dt)
    query = query.order_by(Metric.collected_at.asc())

    result = await db.execute(query)
    metrics = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "collected_at", "cpu_percent", "cpu_freq_mhz", "cpu_temp_c",
        "ram_percent", "ram_used_gb", "ram_total_gb",
        "net_sent_mb", "net_recv_mb", "net_latency_ms",
        "gpu_percent", "gpu_temp_c", "gpu_vram_used_mb",
    ])
    for m in metrics:
        writer.writerow([
            m.collected_at, m.cpu_percent, m.cpu_freq_mhz, m.cpu_temp_c,
            m.ram_percent, m.ram_used_gb, m.ram_total_gb,
            m.net_sent_mb, m.net_recv_mb, m.net_latency_ms,
            m.gpu_percent, m.gpu_temp_c, m.gpu_vram_used_mb,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=machine_{machine_id}_metrics.csv"},
    )


@router.get("/alerts")
async def export_alerts(
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlertEvent).join(AlertRule).join(Machine, AlertEvent.machine_id == Machine.id)
    if from_dt:
        query = query.where(AlertEvent.triggered_at >= from_dt)
    if to_dt:
        query = query.where(AlertEvent.triggered_at <= to_dt)
    query = query.order_by(AlertEvent.triggered_at.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "triggered_at", "resolved_at", "machine_id", "rule_id",
        "current_value", "message", "acknowledged", "acknowledged_by",
    ])
    for e in events:
        writer.writerow([
            e.triggered_at, e.resolved_at, e.machine_id, e.rule_id,
            e.current_value, e.message, e.acknowledged, e.acknowledged_by,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alert_events.csv"},
    )
