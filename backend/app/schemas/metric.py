from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class MetricIngestRequest(BaseModel):
    collected_at: Optional[datetime] = None
    cpu_percent: Optional[float] = Field(None, ge=0, le=100)
    cpu_freq_mhz: Optional[float] = Field(None, ge=0, le=10000)
    cpu_temp_c: Optional[float] = Field(None, ge=-50, le=200)
    ram_percent: Optional[float] = Field(None, ge=0, le=100)
    ram_used_gb: Optional[float] = Field(None, ge=0, le=2048)
    ram_total_gb: Optional[float] = Field(None, ge=0, le=2048)
    disk_usage: Optional[List[Any]] = None
    net_sent_mb: Optional[float] = Field(None, ge=0)
    net_recv_mb: Optional[float] = Field(None, ge=0)
    net_latency_ms: Optional[float] = Field(None, ge=0, le=60000)
    top_processes: Optional[List[Any]] = None
    gpu_percent: Optional[float] = Field(None, ge=0, le=100)
    gpu_temp_c: Optional[float] = Field(None, ge=-50, le=200)
    gpu_vram_used_mb: Optional[float] = Field(None, ge=0)


class MetricBatchIngestRequest(BaseModel):
    metrics: List[MetricIngestRequest] = Field(..., max_length=10)


class MetricResponse(BaseModel):
    id: int
    machine_id: int
    collected_at: Optional[datetime] = None
    cpu_percent: Optional[float] = None
    cpu_freq_mhz: Optional[float] = None
    cpu_temp_c: Optional[float] = None
    ram_percent: Optional[float] = None
    ram_used_gb: Optional[float] = None
    ram_total_gb: Optional[float] = None
    disk_usage: Optional[List[Any]] = None
    net_sent_mb: Optional[float] = None
    net_recv_mb: Optional[float] = None
    net_latency_ms: Optional[float] = None
    top_processes: Optional[List[Any]] = None
    gpu_percent: Optional[float] = None
    gpu_temp_c: Optional[float] = None
    gpu_vram_used_mb: Optional[float] = None

    model_config = {"from_attributes": True}
