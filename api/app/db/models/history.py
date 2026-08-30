import uuid
import enum
from sqlalchemy import Column, DateTime, ForeignKey, func, JSON, Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class ToolType(str, enum.Enum):
    VIDEO_ANALYZER = "VIDEO_ANALYZER"
    KEYWORD_TOOL = "KEYWORD_TOOL"
    TREND_ANALYZER = "TREND_ANALYZER"
    COMPETITOR_ANALYSIS = "COMPETITOR_ANALYSIS"
    AI_ASSISTANT = "AI_ASSISTANT"
    SEO_SCORE = "SEO_SCORE"

class HistoryEntry(Base):
    __tablename__ = 'history_entries'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_type: Mapped[ToolType] = mapped_column(Enum(ToolType, native_enum=False, name="tool_type", values_callable=lambda x: [e.value for e in x]), nullable=False)
    input_params = Column(JSON, nullable=False)
    output_results = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="history_entries")
