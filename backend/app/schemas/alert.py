from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AlertRuleCreate(BaseModel):
    company_id: Optional[int] = None
    machine_id: Optional[int] = None
    name: str
    metric_field: str
    operator: str  # gt, lt, eq
    threshold: float
    duration_seconds: int = 0
    severity: str = "warning"  # info, warning, critical
    enabled: bool = True
    notify_email: bool = False
    notify_telegram: bool = False


class AlertRuleUpdate(BaseModel):
    company_id: Optional[int] = None
    machine_id: Optional[int] = None
    name: Optional[str] = None
    metric_field: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    duration_seconds: Optional[int] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    company_id: Optional[int] = None
    machine_id: Optional[int] = None
    name: str
    metric_field: str
    operator: str
    threshold: float
    duration_seconds: int
    severity: str
    enabled: bool
    notify_email: bool
    notify_telegram: bool
    machine_name: Optional[str] = None
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertEventResponse(BaseModel):
    id: int
    rule_id: int
    machine_id: int
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    current_value: Optional[float] = None
    message: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    machine_name: Optional[str] = None
    rule_name: Optional[str] = None
    severity: Optional[str] = None
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CompanyCreate(BaseModel):
    name: str
    slug: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    alert_email: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    alert_email: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    slug: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    is_active: bool = True
    alert_email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    machine_count: Optional[int] = 0
    online_count: Optional[int] = 0
    alert_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class CompanyTokenResponse(BaseModel):
    token: str
    message: str = "Save this token — it will not be shown again."
