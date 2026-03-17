from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, generate_api_key, hash_api_key
from app.models.user import User
from app.models.company import Company
from app.models.machine import Machine
from app.models.alert import AlertEvent, AlertRule
from app.schemas.alert import (
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyTokenResponse,
    AlertEventResponse,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.is_active == True))
    companies = result.scalars().all()

    responses = []
    for c in companies:
        machine_result = await db.execute(
            select(func.count(Machine.id)).where(Machine.company_id == c.id)
        )
        machine_count = machine_result.scalar() or 0

        online_result = await db.execute(
            select(func.count(Machine.id)).where(
                Machine.company_id == c.id, Machine.is_online == True
            )
        )
        online_count = online_result.scalar() or 0

        alert_result = await db.execute(
            select(func.count(AlertEvent.id))
            .join(Machine, AlertEvent.machine_id == Machine.id)
            .where(
                Machine.company_id == c.id,
                AlertEvent.resolved_at == None,
                AlertEvent.acknowledged == False,
            )
        )
        alert_count = alert_result.scalar() or 0

        responses.append(CompanyResponse(
            id=c.id, name=c.name, slug=c.slug,
            contact_name=c.contact_name, contact_email=c.contact_email,
            notes=c.notes, created_at=c.created_at, is_active=c.is_active,
            alert_email=c.alert_email, telegram_chat_id=c.telegram_chat_id,
            machine_count=machine_count, online_count=online_count,
            alert_count=alert_count,
        ))
    return responses


@router.post("/", response_model=CompanyTokenResponse)
async def create_company(
    request: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Company).where(Company.slug == request.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")

    token = generate_api_key()
    company = Company(
        name=request.name,
        slug=request.slug,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        notes=request.notes,
        alert_email=request.alert_email,
        telegram_chat_id=request.telegram_chat_id,
        token_hash=hash_api_key(token),
    )
    db.add(company)
    await db.flush()
    return CompanyTokenResponse(token=token)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    machine_result = await db.execute(
        select(func.count(Machine.id)).where(Machine.company_id == company_id)
    )
    online_result = await db.execute(
        select(func.count(Machine.id)).where(
            Machine.company_id == company_id, Machine.is_online == True
        )
    )

    return CompanyResponse(
        id=company.id, name=company.name, slug=company.slug,
        contact_name=company.contact_name, contact_email=company.contact_email,
        notes=company.notes, created_at=company.created_at, is_active=company.is_active,
        alert_email=company.alert_email, telegram_chat_id=company.telegram_chat_id,
        machine_count=machine_result.scalar() or 0,
        online_count=online_result.scalar() or 0,
    )


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    request: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.add(company)
    await db.flush()
    await db.refresh(company)

    return CompanyResponse(
        id=company.id, name=company.name, slug=company.slug,
        contact_name=company.contact_name, contact_email=company.contact_email,
        notes=company.notes, created_at=company.created_at, is_active=company.is_active,
        alert_email=company.alert_email, telegram_chat_id=company.telegram_chat_id,
    )


@router.delete("/{company_id}")
async def delete_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.is_active = False
    db.add(company)
    return {"message": "Company deactivated"}


@router.post("/{company_id}/token", response_model=CompanyTokenResponse)
async def regenerate_token(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    token = generate_api_key()
    company.token_hash = hash_api_key(token)
    db.add(company)
    return CompanyTokenResponse(token=token)


@router.get("/{company_id}/machines")
async def company_machines(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Machine).where(Machine.company_id == company_id)
    )
    machines = result.scalars().all()
    return machines


@router.get("/{company_id}/alerts")
async def company_alerts(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertEvent)
        .join(Machine, AlertEvent.machine_id == Machine.id)
        .where(
            Machine.company_id == company_id,
            AlertEvent.resolved_at == None,
        )
        .order_by(AlertEvent.triggered_at.desc())
        .limit(50)
    )
    return result.scalars().all()
