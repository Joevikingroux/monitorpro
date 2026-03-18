from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index, Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False)

    cpu_percent = Column(Float)
    cpu_freq_mhz = Column(Float)
    cpu_temp_c = Column(Float)

    ram_percent = Column(Float)
    ram_used_gb = Column(Float)
    ram_total_gb = Column(Float)

    disk_usage = Column(JSONB)
    net_sent_mb = Column(Float)
    net_recv_mb = Column(Float)
    net_latency_ms = Column(Float)

    top_processes = Column(JSONB)

    gpu_percent = Column(Float)
    gpu_temp_c = Column(Float)
    gpu_vram_used_mb = Column(Float)

    firewall_enabled = Column(Boolean, nullable=True)
    av_status = Column(String(255), nullable=True)
    last_boot_time = Column(DateTime(timezone=True), nullable=True)
    installed_updates = Column(Integer, nullable=True)

    machine = relationship("Machine", back_populates="metrics")

    __table_args__ = (
        Index("ix_metrics_machine_collected", "machine_id", collected_at.desc()),
    )
