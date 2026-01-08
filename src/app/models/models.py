
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.app.core.database import Base


class Session(Base):
    __tablename__ = "session"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    module = Column(String(255), nullable=True)
    drive_link = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    job_status = Column(String(50), default="Pending")

    snippets = relationship(
        "Snippet", back_populates="session", cascade="all, delete-orphan")


class Snippet(Base):
    __tablename__ = "snippet"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    start_second = Column(Integer, nullable=False)
    end_second = Column(Integer, nullable=False)
    intro_id = Column(Integer, nullable=True)
    style_name = Column(String(100), nullable=True)
    intro_metadata = Column(Text, nullable=True)  # JSON string

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="snippets")
