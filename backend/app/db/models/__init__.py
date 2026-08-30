"""
Models package — import all ORM models here so that:
1. Alembic autogenerate sees them via Base.metadata.
2. The test conftest can import __all__ to ensure all models are loaded
   before Base.metadata.create_all() runs.
"""

from app.db.base import Base
from app.db.models.user import User
from app.db.models.session import Session
from app.db.models.token import EmailVerificationToken, PasswordResetToken
from app.db.models.youtube import YoutubeConnection
from app.db.models.credit import AdRewardEvent, CreditLedger, CreditTxnType
from app.db.models.history import HistoryEntry, ToolType

__all__ = [
    "Base",
    "User",
    "Session",
    "EmailVerificationToken",
    "PasswordResetToken",
    "YoutubeConnection",
    "AdRewardEvent",
    "CreditLedger",
    "CreditTxnType",
    "HistoryEntry",
    "ToolType",
]
