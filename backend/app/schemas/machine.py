from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class MachineRegisterRequest(BaseModel):
    hostname: str
    os_version: Optional[str] = None
    cpu_model: Optional[str] = None
    total_ram_gb: Optional[float] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    company_token: str


class MachineRegisterResponse(BaseModel):
    machine_id: int
    api_key: str


class LatestMetricSummary(BaseModel):
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    disk_usage: Optional[List[Any]] = None
    net_latency_ms: Optional[float] = None
    collected_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MachineResponse(BaseModel):
    id: int
    company_id: int
    company_name: Optional[str] = None
    hostname: str
    display_name: Optional[str] = None
    os_version: Optional[str] = None
    cpu_model: Optional[str] = None
    total_ram_gb: Optional[float] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_online: bool = False
    registered_at: Optional[datetime] = None
    group_tag: Optional[str] = None
    notes: Optional[str] = None
    latest_metric: Optional[LatestMetricSummary] = None

    model_config = {"from_attributes": True}


class MachineUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    group_tag: Optional[str] = None
    notes: Optional[str] = None


class ServiceResponse(BaseModel):
    id: int
    machine_id: int
    service_name: str
    display_name: Optional[str] = None
    status: Optional[str] = None
    startup_type: Optional[str] = None
    last_checked: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ServiceIngestRequest(BaseModel):
    service_name: str
    display_name: Optional[str] = None
    status: Optional[str] = None
    startup_type: Optional[str] = None


class SoftwareResponse(BaseModel):
    id: int
    machine_id: int
    name: str
    version: Optional[str] = None
    publisher: Optional[str] = None
    install_date: Optional[str] = None
    scanned_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SoftwareIngestRequest(BaseModel):
    name: str
    version: Optional[str] = None
    publisher: Optional[str] = None
    install_date: Optional[str] = None


class EventLogResponse(BaseModel):
    id: int
    machine_id: int
    log_source: Optional[str] = None
    event_id: Optional[int] = None
    level: Optional[str] = None
    message: Optional[str] = None
    occurred_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventLogIngestRequest(BaseModel):
    log_source: Optional[str] = None
    event_id: Optional[int] = None
    level: Optional[str] = None
    message: Optional[str] = None
    occurred_at: Optional[datetime] = None
