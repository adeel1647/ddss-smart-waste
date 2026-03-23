"""phase6 intelligence layer

Revision ID: 20260319_02
Revises: 20260319_01
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = '20260319_02'
down_revision = '20260319_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contamination_cases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organisation_id', sa.Integer(), nullable=True),
        sa.Column('site_id', sa.Integer(), nullable=True),
        sa.Column('zone_id', sa.Integer(), nullable=True),
        sa.Column('bin_id', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=24), nullable=False, server_default='manual'),
        sa.Column('contamination_type', sa.String(length=80), nullable=False, server_default='mixed_waste'),
        sa.Column('severity', sa.String(length=16), nullable=False, server_default='medium'),
        sa.Column('probability', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False, server_default='open'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('evidence_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bin_id'], ['bins.bin_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_contamination_cases_organisation_id', 'contamination_cases', ['organisation_id'])
    op.create_index('ix_contamination_cases_site_id', 'contamination_cases', ['site_id'])
    op.create_index('ix_contamination_cases_zone_id', 'contamination_cases', ['zone_id'])
    op.create_index('ix_contamination_cases_bin_id', 'contamination_cases', ['bin_id'])
    op.create_index('ix_contamination_cases_status', 'contamination_cases', ['status'])
    op.create_index('ix_contamination_cases_severity', 'contamination_cases', ['severity'])
    op.create_index('ix_contamination_cases_org_status_created', 'contamination_cases', ['organisation_id', 'status', 'created_at'])
    op.create_check_constraint('ck_contamination_cases_source', 'contamination_cases', "source IN ('manual', 'model', 'sensor', 'rule')")
    op.create_check_constraint('ck_contamination_cases_severity', 'contamination_cases', "severity IN ('low', 'medium', 'high', 'critical')")
    op.create_check_constraint('ck_contamination_cases_status', 'contamination_cases', "status IN ('open', 'investigating', 'resolved', 'dismissed')")
    op.create_check_constraint('ck_contamination_cases_probability', 'contamination_cases', '(probability IS NULL OR (probability >= 0 AND probability <= 1))')

    op.create_table(
        'model_metric_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('model_name', sa.String(length=80), nullable=False),
        sa.Column('model_version', sa.String(length=80), nullable=True),
        sa.Column('metric_name', sa.String(length=80), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('window_label', sa.String(length=80), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='ok'),
        sa.Column('meta_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_model_metric_snapshots_model_name', 'model_metric_snapshots', ['model_name'])
    op.create_index('ix_model_metric_snapshots_metric_name', 'model_metric_snapshots', ['metric_name'])
    op.create_index('ix_model_metric_snapshots_status', 'model_metric_snapshots', ['status'])
    op.create_index('ix_model_metric_snapshots_created_at', 'model_metric_snapshots', ['created_at'])
    op.create_index('ix_model_metric_snapshots_model_metric_created', 'model_metric_snapshots', ['model_name', 'metric_name', 'created_at'])
    op.create_check_constraint('ck_model_metric_snapshots_status', 'model_metric_snapshots', "status IN ('ok', 'warning', 'critical')")
    op.create_check_constraint('ck_model_metric_snapshots_sample_size', 'model_metric_snapshots', '(sample_size IS NULL OR sample_size >= 0)')


def downgrade():
    op.drop_table('model_metric_snapshots')
    op.drop_table('contamination_cases')
