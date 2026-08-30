import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, LargeBinary, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class YoutubeConnection(Base):
    __tablename__ = 'youtube_connections'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    google_email: Mapped[str | None] = mapped_column(String, nullable=True)
    youtube_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(String, nullable=True)
    channel_avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    scopes: Mapped[str | None] = mapped_column(String, nullable=True)
    access_token_encrypted = Column(LargeBinary, nullable=False)
    refresh_token_encrypted = Column(LargeBinary, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="youtube_connection")
