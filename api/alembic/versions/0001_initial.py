"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table('workspaces',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(64), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_workspaces_slug', 'workspaces', ['slug'])

    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workspace_id', sa.String(36), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_workspace_id', 'users', ['workspace_id'])

    op.create_table('tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workspace_id', sa.String(36), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('status', sa.String(32), default='draft'),
        sa.Column('schedule_cron', sa.String(100), nullable=True),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('latest_run_id', sa.String(36), nullable=True),
        sa.Column('latest_dataset_version_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_tasks_workspace_id', 'tasks', ['workspace_id'])

    op.create_table('workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('requirement_spec', sa.JSON(), nullable=False),
        sa.Column('dag', sa.JSON(), nullable=False),
        sa.Column('assumptions', sa.JSON(), default=list),
        sa.Column('estimated_time_s', sa.Float(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('approved', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_workflows_task_id', 'workflows', ['task_id'])

    op.create_table('runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.id'), nullable=False),
        sa.Column('status', sa.String(32), default='queued'),
        sa.Column('node_states', sa.JSON(), default=dict),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pages_fetched', sa.Integer(), default=0),
        sa.Column('records_found', sa.Integer(), default=0),
        sa.Column('records_validated', sa.Integer(), default=0),
        sa.Column('records_deduped', sa.Integer(), default=0),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('total_cost_usd', sa.Float(), default=0.0),
        sa.Column('compliance_report', sa.JSON(), nullable=True),
        sa.Column('demo_mode', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_runs_task_id', 'runs', ['task_id'])
    op.create_index('ix_runs_status', 'runs', ['status'])

    op.create_table('run_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('node_id', sa.String(64), nullable=True),
        sa.Column('message', sa.Text(), default=''),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('level', sa.String(16), default='info'),
    )
    op.create_index('ix_run_events_run_id', 'run_events', ['run_id'])

    op.create_table('sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('domain', sa.String(500), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('robots_allowed', sa.Boolean(), nullable=True),
        sa.Column('robots_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pages_fetched', sa.Integer(), default=0),
        sa.Column('records_yielded', sa.Integer(), default=0),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('skipped_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_sources_run_id', 'sources', ['run_id'])

    op.create_table('snapshots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('http_status', sa.Integer(), default=200),
        sa.Column('content_type', sa.String(128), default='text/html'),
        sa.Column('size_bytes', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_snapshots_source_id', 'snapshots', ['source_id'])

    op.create_table('records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('cluster_id', sa.String(36), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('quality_score', sa.Float(), default=0.0),
        sa.Column('quality_flags', sa.JSON(), default=list),
        sa.Column('is_quarantined', sa.Boolean(), default=False),
        sa.Column('quarantine_reasons', sa.JSON(), default=list),
        sa.Column('is_duplicate', sa.Boolean(), default=False),
        sa.Column('corroboration_count', sa.Integer(), default=1),
        sa.Column('pii_flagged', sa.Boolean(), default=False),
        sa.Column('entity_type', sa.String(64), default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_records_run_id', 'records', ['run_id'])
    op.create_index('ix_records_cluster_id', 'records', ['cluster_id'])

    op.create_table('field_values',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('record_id', sa.String(36), sa.ForeignKey('records.id'), nullable=False),
        sa.Column('field_name', sa.String(128), nullable=False),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('evidence_snippet', sa.Text(), nullable=True),
        sa.Column('extraction_method', sa.String(32), default='unknown'),
        sa.Column('confidence', sa.Float(), default=1.0),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('snapshot_id', sa.String(36), sa.ForeignKey('snapshots.id'), nullable=True),
        sa.Column('verified', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_field_values_record_id', 'field_values', ['record_id'])

    op.create_table('dataset_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('record_count', sa.Integer(), default=0),
        sa.Column('diff_summary', sa.JSON(), nullable=True),
        sa.Column('previous_version_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_dataset_versions_task_id', 'dataset_versions', ['task_id'])

    op.create_table('dedupe_clusters',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('canonical_record_id', sa.String(36), sa.ForeignKey('records.id'), nullable=False),
        sa.Column('member_record_ids', sa.JSON(), default=list),
        sa.Column('merge_method', sa.String(32), nullable=False),
        sa.Column('confidence', sa.Float(), default=1.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('exports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('format', sa.String(16), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('include_provenance', sa.Boolean(), default=True),
        sa.Column('record_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('llm_calls',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id'), nullable=True),
        sa.Column('model', sa.String(64), nullable=False),
        sa.Column('purpose', sa.String(128), nullable=False),
        sa.Column('input_tokens', sa.Integer(), default=0),
        sa.Column('output_tokens', sa.Integer(), default=0),
        sa.Column('cost_usd', sa.Float(), default=0.0),
        sa.Column('latency_ms', sa.Integer(), default=0),
        sa.Column('cached', sa.Boolean(), default=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_llm_calls_run_id', 'llm_calls', ['run_id'])

    op.create_table('schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('cron_expr', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_schedules_task_id', 'schedules', ['task_id'])


def downgrade() -> None:
    op.drop_table('schedules')
    op.drop_table('llm_calls')
    op.drop_table('exports')
    op.drop_table('dedupe_clusters')
    op.drop_table('dataset_versions')
    op.drop_table('field_values')
    op.drop_table('records')
    op.drop_table('snapshots')
    op.drop_table('sources')
    op.drop_table('run_events')
    op.drop_table('runs')
    op.drop_table('workflows')
    op.drop_table('tasks')
    op.drop_table('users')
    op.drop_table('workspaces')
