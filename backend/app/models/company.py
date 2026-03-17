from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    token_hash = Column(String(64), index=True)
    alert_email = Column(String(255))
    telegram_chat_id = Column(String(255))

    machines = relationship("Machine", back_populates="company", lazy="selectin")
