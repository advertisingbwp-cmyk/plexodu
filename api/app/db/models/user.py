import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import CITEXT
from app.db.base import Base

class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String().with_variant(CITEXT(), "postgresql"), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    credit_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    youtube_connection = relationship("YoutubeConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_ledger = relationship("CreditLedger", back_populates="user", cascade="all, delete-orphan")
    ad_reward_events = relationship("AdRewardEvent", back_populates="user", cascade="all, delete-orphan")
    history_entries = relationship("HistoryEntry", back_populates="user", cascade="all, delete-orphan")
