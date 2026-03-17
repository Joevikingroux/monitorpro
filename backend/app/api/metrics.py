from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
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


@router.get("/{machine_id}", response_model=List[MetricResponse])
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
        query = query.where(Metric.collected_at >= from_dt)
    if to_dt:
        query = query.where(Metric.collected_at <= to_dt)

    query = query.order_by(Metric.collected_at.desc())

    if interval == "15m":
        query = query.limit(672)  # 7 days * 24h * 4 per hour
    elif interval == "1h":
        query = query.limit(168)  # 7 days * 24h
    else:
        query = query.limit(1000)

    result = await db.execute(query)
    metrics = result.scalars().all()

    if interval == "15m" and len(metrics) > 0:
        downsampled = []
        for i in range(0, len(metrics), max(1, len(metrics) // 672)):
            downsampled.append(metrics[i])
        return downsampled

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
