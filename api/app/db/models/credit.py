import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Integer, Enum, JSON, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class CreditTxnType(str, enum.Enum):
    WELCOME_CREDIT = "WELCOME_CREDIT"
    AD_REWARD = "AD_REWARD"
    TOOL_USAGE = "TOOL_USAGE"
    REFUND = "REFUND"
    PURCHASE = "PURCHASE"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"

class CreditLedger(Base):
    __tablename__ = 'credit_ledger'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[CreditTxnType] = mapped_column(Enum(CreditTxnType, native_enum=False, name="credit_txn_type", values_callable=lambda x: [e.value for e in x]), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="credit_ledger")

class AdRewardEvent(Base):
    __tablename__ = 'ad_reward_events'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    provider_reference_id: Mapped[str] = mapped_column(String, nullable=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('provider', 'provider_reference_id', name='uq_ad_reward_provider_ref'),
    )

    user = relationship("User", back_populates="ad_reward_events")
