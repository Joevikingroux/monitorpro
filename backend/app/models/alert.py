from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=True)
    name = Column(String(255), nullable=False)
    metric_field = Column(String(100), nullable=False)
    operator = Column(String(10), nullable=False)  # gt, lt, eq
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=0)
    severity = Column(String(20), default="warning")  # info, warning, critical
    enabled = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)
    notify_telegram = Column(Boolean, default=False)

    events = relationship("AlertEvent", back_populates="rule", lazy="dynamic")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    current_value = Column(Float)
    message = Column(Text)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(255), nullable=True)

    rule = relationship("AlertRule", back_populates="events")
    machine = relationship("Machine", back_populates="alert_events")
