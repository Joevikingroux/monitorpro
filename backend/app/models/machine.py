from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    hostname = Column(String(255), nullable=False)
    display_name = Column(String(255))
    api_key_hash = Column(String(64), unique=True, nullable=False, index=True)
    os_version = Column(String(255))
    cpu_model = Column(String(255))
    total_ram_gb = Column(Float)
    ip_address = Column(String(45))
    mac_address = Column(String(17))
    last_seen = Column(DateTime(timezone=True))
    is_online = Column(Boolean, default=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    group_tag = Column(String(255))
    notes = Column(Text)

    company = relationship("Company", back_populates="machines")
    metrics = relationship("Metric", back_populates="machine", lazy="dynamic")
    alert_events = relationship("AlertEvent", back_populates="machine", lazy="dynamic")
