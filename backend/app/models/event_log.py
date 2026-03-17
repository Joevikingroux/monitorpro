from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from app.core.database import Base


class WindowsService(Base):
    __tablename__ = "windows_services"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    service_name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    status = Column(String(50))
    startup_type = Column(String(50))
    last_checked = Column(DateTime(timezone=True), server_default=func.now())


class SoftwareInventory(Base):
    __tablename__ = "software_inventory"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    version = Column(String(255))
    publisher = Column(String(255))
    install_date = Column(String(50))
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    log_source = Column(String(255))
    event_id = Column(Integer)
    level = Column(String(50))
    message = Column(Text)
    occurred_at = Column(DateTime(timezone=True))
