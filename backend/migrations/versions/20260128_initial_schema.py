"""Initial schema with audit_logs, processed_tickets, system_config

Revision ID: 001_initial
Revises:
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ticket_id', sa.String(50), nullable=False),
        sa.Column('ticket_key', sa.String(50), nullable=False),
        sa.Column('ticket_snapshot', postgresql.JSONB, nullable=False),
        sa.Column('confidence_scores', postgresql.JSONB, nullable=False),
        sa.Column('matched_response_id', sa.String(100), nullable=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('escalation_reason', sa.String(500), nullable=True),
        sa.Column('comment_id', sa.String(50), nullable=True),
        sa.Column('comment_posted_at', sa.DateTime, nullable=True),
        sa.Column('retracted_at', sa.DateTime, nullable=True),
        sa.Column('retracted_by', sa.String(100), nullable=True),
        sa.Column('system_version', sa.String(20), nullable=False),
        sa.Column('config_version', sa.String(20), nullable=False),
        sa.Column('processing_duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("action IN ('auto_respond', 'escalate', 'shadow')", name='valid_action'),
        sa.CheckConstraint(
            "(action = 'escalate' AND escalation_reason IS NOT NULL) OR (action != 'escalate')",
            name='escalation_reason_required'
        ),
        sa.CheckConstraint(
            "(action = 'auto_respond' AND matched_response_id IS NOT NULL) OR (action != 'auto_respond')",
            name='matched_response_required'
        ),
    )

    # Create indexes for audit_logs
    op.create_index('idx_audit_logs_ticket_id', 'audit_logs', ['ticket_id'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'], postgresql_using='btree')
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_retracted_at', 'audit_logs', ['retracted_at'], postgresql_where=sa.text('retracted_at IS NOT NULL'))

    # Create function to prevent audit log mutations
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs table is append-only';
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger for audit_logs immutability
    op.execute("""
        CREATE TRIGGER audit_log_immutability
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
    """)

    # Create processed_tickets table
    op.create_table(
        'processed_tickets',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('ticket_id', sa.String(50), nullable=False, unique=True),
        sa.Column('ticket_key', sa.String(50), nullable=False),
        sa.Column('first_processed_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_seen_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('times_seen', sa.Integer, nullable=False, server_default=sa.text('1')),
    )

    # Create index for processed_tickets
    op.create_index('idx_processed_tickets_ticket_id', 'processed_tickets', ['ticket_id'])

    # Create system_config table
    op.create_table(
        'system_config',
        sa.Column('id', sa.Integer, primary_key=True, default=1),
        sa.Column('automation_enabled', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('disabled_at', sa.DateTime, nullable=True),
        sa.Column('disabled_by', sa.String(100), nullable=True),
        sa.Column('disable_reason', sa.Text, nullable=True),
        sa.Column('shadow_mode_active', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('shadow_mode_until', sa.DateTime, nullable=True),
        sa.Column('error_rate_last_hour', sa.DECIMAL(5, 4), server_default=sa.text('0.0000')),
        sa.Column('last_error_rate_check', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('id = 1', name='system_config_singleton'),
    )

    # Initialize system_config with default values
    op.execute("""
        INSERT INTO system_config (id) VALUES (1)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    """Drop all tables and functions."""
    op.drop_table('system_config')
    op.drop_table('processed_tickets')

    # Drop trigger and function for audit_logs
    op.execute('DROP TRIGGER IF EXISTS audit_log_immutability ON audit_logs;')
    op.execute('DROP FUNCTION IF EXISTS prevent_audit_log_mutation();')

    op.drop_table('audit_logs')
