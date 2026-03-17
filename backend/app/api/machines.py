from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import (
    generate_api_key, hash_api_key, get_current_user, get_machine_by_api_key,
)
from app.models.user import User
from app.models.company import Company
from app.models.machine import Machine
from app.models.event_log import WindowsService, SoftwareInventory, EventLog
from app.schemas.machine import (
    MachineRegisterRequest, MachineRegisterResponse, MachineResponse,
    MachineUpdateRequest, ServiceResponse, SoftwareResponse, EventLogResponse,
    ServiceIngestRequest, SoftwareIngestRequest, EventLogIngestRequest,
)

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.post("/register", response_model=MachineRegisterResponse)
async def register_machine(request: MachineRegisterRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_api_key(request.company_token)
    result = await db.execute(
        select(Company).where(Company.token_hash == token_hash, Company.is_active == True)  # noqa: E712
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid company token")

    api_key = generate_api_key()
    machine = Machine(
        company_id=company.id,
        hostname=request.hostname,
        display_name=request.hostname,
        api_key_hash=hash_api_key(api_key),
        os_version=request.os_version,
        cpu_model=request.cpu_model,
        total_ram_gb=request.total_ram_gb,
        ip_address=request.ip_address,
        mac_address=request.mac_address,
        last_seen=datetime.now(timezone.utc),
        is_online=True,
    )
    db.add(machine)
    await db.flush()
    await db.refresh(machine)

    return MachineRegisterResponse(machine_id=machine.id, api_key=api_key)


@router.get("/", response_model=list[MachineResponse])
async def list_machines(
    company_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Machine).options(selectinload(Machine.company))
    if company_id:
        query = query.where(Machine.company_id == company_id)
    query = query.join(Company).where(Company.is_active == True)  # noqa: E712
    result = await db.execute(query)
    machines = result.scalars().all()

    return [
        MachineResponse(
            **{c.name: getattr(m, c.name) for c in Machine.__table__.columns},
            company_name=m.company.name if m.company else None,
        )
        for m in machines
    ]


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Machine).options(selectinload(Machine.company)).where(Machine.id == machine_id)
    )
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return MachineResponse(
        **{c.name: getattr(machine, c.name) for c in Machine.__table__.columns},
        company_name=machine.company.name if machine.company else None,
    )


@router.patch("/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: int,
    request: MachineUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Machine).options(selectinload(Machine.company)).where(Machine.id == machine_id)
    )
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(machine, field, value)
    db.add(machine)
    await db.flush()
    await db.refresh(machine)
    return MachineResponse(
        **{c.name: getattr(machine, c.name) for c in Machine.__table__.columns},
        company_name=machine.company.name if machine.company else None,
    )


@router.delete("/{machine_id}")
async def delete_machine(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Machine).where(Machine.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    await db.delete(machine)
    return {"message": "Machine deleted"}


@router.get("/{machine_id}/services", response_model=list[ServiceResponse])
async def get_services(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WindowsService).where(WindowsService.machine_id == machine_id)
    )
    return result.scalars().all()


@router.post("/{machine_id}/services")
async def ingest_services(
    machine_id: int,
    services: list[ServiceIngestRequest],
    machine: Machine = Depends(get_machine_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    if machine.id != machine_id:
        raise HTTPException(status_code=403, detail="Machine ID mismatch")
    await db.execute(delete(WindowsService).where(WindowsService.machine_id == machine_id))
    for svc in services:
        db.add(WindowsService(machine_id=machine_id, **svc.model_dump()))
    return {"message": f"Ingested {len(services)} services"}


@router.get("/{machine_id}/software", response_model=list[SoftwareResponse])
async def get_software(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SoftwareInventory).where(SoftwareInventory.machine_id == machine_id)
    )
    return result.scalars().all()


@router.post("/{machine_id}/software")
async def ingest_software(
    machine_id: int,
    software: list[SoftwareIngestRequest],
    machine: Machine = Depends(get_machine_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    if machine.id != machine_id:
        raise HTTPException(status_code=403, detail="Machine ID mismatch")
    await db.execute(delete(SoftwareInventory).where(SoftwareInventory.machine_id == machine_id))
    for sw in software:
        db.add(SoftwareInventory(machine_id=machine_id, **sw.model_dump()))
    return {"message": f"Ingested {len(software)} software items"}


@router.get("/{machine_id}/event-logs", response_model=list[EventLogResponse])
async def get_event_logs(
    machine_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventLog)
        .where(EventLog.machine_id == machine_id)
        .order_by(EventLog.occurred_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/{machine_id}/event-logs")
async def ingest_event_logs(
    machine_id: int,
    events: list[EventLogIngestRequest],
    machine: Machine = Depends(get_machine_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    if machine.id != machine_id:
        raise HTTPException(status_code=403, detail="Machine ID mismatch")
    for evt in events:
        db.add(EventLog(machine_id=machine_id, **evt.model_dump()))
    return {"message": f"Ingested {len(events)} event logs"}
