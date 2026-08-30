"""initial

Revision ID: 0001
Revises: 
Create Date: 2026-08-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    op.execute('CREATE EXTENSION IF NOT EXISTS citext')
    
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('username', sa.String(), nullable=False, unique=True),
        sa.Column('email', postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('credit_balance', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    
    op.create_table('email_verification_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_consumed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_table('password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_consumed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_table('youtube_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('youtube_channel_id', sa.String(), nullable=True),
        sa.Column('access_token_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )

    credit_txn_type = postgresql.ENUM('WELCOME_CREDIT', 'AD_REWARD', 'TOOL_USAGE', 'REFUND', 'PURCHASE', 'MANUAL_ADJUSTMENT', name='credit_txn_type')
    credit_txn_type.create(op.get_bind())
    
    op.create_table('credit_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('WELCOME_CREDIT', 'AD_REWARD', 'TOOL_USAGE', 'REFUND', 'PURCHASE', 'MANUAL_ADJUSTMENT', name='credit_txn_type'), nullable=False),
        sa.Column('reference_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('ix_credit_ledger_user_id', 'credit_ledger', ['user_id'])
    op.execute("CREATE UNIQUE INDEX one_welcome_credit_per_user ON credit_ledger (user_id) WHERE type = 'WELCOME_CREDIT'")

    op.create_table('ad_reward_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('provider_reference_id', sa.String(), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('provider', 'provider_reference_id', name='uq_ad_reward_provider_ref')
    )

    tool_type = postgresql.ENUM('VIDEO_ANALYZER', 'KEYWORD_TOOL', 'TREND_ANALYZER', 'COMPETITOR_ANALYSIS', 'AI_ASSISTANT', 'SEO_SCORE', name='tool_type')
    tool_type.create(op.get_bind())

    op.create_table('history_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_type', sa.Enum('VIDEO_ANALYZER', 'KEYWORD_TOOL', 'TREND_ANALYZER', 'COMPETITOR_ANALYSIS', 'AI_ASSISTANT', 'SEO_SCORE', name='tool_type'), nullable=False),
        sa.Column('input_params', sa.JSON(), nullable=False),
        sa.Column('output_results', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('ix_history_entries_user_id', 'history_entries', ['user_id'])
    
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
       NEW.updated_at = now();
       RETURN NEW;
    END;
    $$ language 'plpgsql';
    """)
    
    op.execute("""
    CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
    """)

def downgrade() -> None:
    pass
