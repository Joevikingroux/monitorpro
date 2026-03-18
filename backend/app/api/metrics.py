from datetime import datetime, timezone  # noqa: F401 (timezone used in span calc)
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_machine_by_api_key
from app.models.user import User
from app.models.machine import Machine
from app.models.metric import Metric
from app.schemas.metric import MetricIngestRequest, MetricBatchIngestRequest, MetricResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.post("/ingest")
async def ingest_metric(
    request: MetricIngestRequest,
    machine: Machine = Depends(get_machine_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    machine.last_seen = datetime.now(timezone.utc)
    machine.is_online = True
    db.add(machine)

    metric = Metric(
        machine_id=machine.id,
        collected_at=request.collected_at or datetime.now(timezone.utc),
        **request.model_dump(exclude={"collected_at"}),
    )
    db.add(metric)
    return {"message": "Metric ingested"}


@router.post("/ingest/batch")
async def ingest_batch(
    request: MetricBatchIngestRequest,
    machine: Machine = Depends(get_machine_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    machine.last_seen = datetime.now(timezone.utc)
    machine.is_online = True
    db.add(machine)

    for m in request.metrics:
        metric = Metric(
            machine_id=machine.id,
            collected_at=m.collected_at or datetime.now(timezone.utc),
            **m.model_dump(exclude={"collected_at"}),
        )
        db.add(metric)
    return {"message": f"Ingested {len(request.metrics)} metrics"}


@router.get("/{machine_id}", response_model=list[MetricResponse])
async def get_metrics(
    machine_id: int,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    interval: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Metric).where(Metric.machine_id == machine_id)

    if from_dt:
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        query = query.where(Metric.collected_at >= from_dt)
    if to_dt:
        if to_dt.tzinfo is None:
            to_dt = to_dt.replace(tzinfo=timezone.utc)
        query = query.where(Metric.collected_at <= to_dt)

    query = query.order_by(Metric.collected_at.asc())

    # Determine limit based on requested time range
    if from_dt:
        # Make timezone-aware if naive
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        span_hours = (datetime.now(timezone.utc) - from_dt).total_seconds() / 3600
        query = query.limit(5000 if span_hours > 48 else 3000)
    else:
        query = query.limit(120)  # ~1h default at 30s intervals

    result = await db.execute(query)
    metrics = result.scalars().all()
    return metrics


@router.get("/{machine_id}/latest", response_model=Optional[MetricResponse])
async def get_latest_metric(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Metric)
        .where(Metric.machine_id == machine_id)
        .order_by(Metric.collected_at.desc())
        .limit(1)
    )
    metric = result.scalar_one_or_none()
    return metric


@router.get("/{machine_id}/processes")
async def get_processes(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Metric)
        .where(Metric.machine_id == machine_id)
        .order_by(Metric.collected_at.desc())
        .limit(1)
    )
    metric = result.scalar_one_or_none()
    if not metric or not metric.top_processes:
        return []
    return metric.top_processes
