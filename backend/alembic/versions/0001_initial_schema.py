"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'services',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('type', sa.String(50)),
        sa.Column('created_at', sa.DateTime),
        sa.UniqueConstraint('code', name='u_services_code'),
    )

    op.create_table(
        'beds',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bed_code', sa.String(100)),
        sa.Column('active', sa.Boolean),
        sa.Column('created_at', sa.DateTime),
    )

    op.create_table(
        'service_capacity',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('as_of', sa.DateTime, nullable=False),
        sa.Column('beds_total', sa.Integer, nullable=False),
        sa.Column('notes', sa.Text),
        sa.UniqueConstraint('service_id', 'as_of', name='u_service_capacity_asof'),
    )

    op.create_table(
        'admissions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='SET NULL')),
        sa.Column('admitted_at', sa.DateTime, nullable=False),
        sa.Column('discharged_at', sa.DateTime),
        sa.Column('patient_hash', sa.String(128)),
        sa.Column('age_group', sa.String(50)),
        sa.Column('sex', sa.String(10)),
        sa.Column('source', sa.String(100)),
        sa.Column('reason', sa.String(200)),
        sa.Column('bed_id', sa.Integer, sa.ForeignKey('beds.id', ondelete='SET NULL')),
        sa.Column('status', sa.String(50)),
    )

    op.create_table(
        'occupancy_snapshots',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_at', sa.DateTime, nullable=False),
        sa.Column('occupied_beds', sa.Integer, nullable=False),
        sa.Column('available_beds', sa.Integer),
        sa.Column('notes', sa.Text),
    )
    op.create_index('ix_occupancy_service_snapshot', 'occupancy_snapshots', ['service_id', 'snapshot_at'])

    op.create_table(
        'activity_records',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_start', sa.DateTime, nullable=False),
        sa.Column('period_end', sa.DateTime, nullable=False),
        sa.Column('admissions_count', sa.Integer, default=0),
        sa.Column('discharges_count', sa.Integer, default=0),
        sa.Column('visits_count', sa.Integer, default=0),
        sa.Column('metric_payload', postgresql.JSONB),
    )
    op.create_index('ix_activity_service_period', 'activity_records', ['service_id', 'period_start', 'period_end'])

    op.create_table(
        'staff_levels',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('as_of', sa.DateTime, nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('headcount', sa.Integer, nullable=False),
        sa.Column('fte', sa.Numeric),
        sa.Column('notes', sa.Text),
    )
    op.create_index('ix_staff_service_asof_role', 'staff_levels', ['service_id', 'as_of', 'role'])

    op.create_table(
        'budgets',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('budget_amount', sa.Numeric, nullable=False),
        sa.Column('currency', sa.String(10)),
    )
    op.create_unique_constraint('u_budget_service_year', 'budgets', ['service_id', 'year'])

    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='SET NULL')),
        sa.Column('period_start', sa.DateTime),
        sa.Column('period_end', sa.DateTime),
        sa.Column('amount', sa.Numeric, nullable=False),
        sa.Column('currency', sa.String(10)),
        sa.Column('category', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('recorded_at', sa.DateTime),
    )

    op.create_table(
        'energy_consumption',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='SET NULL')),
        sa.Column('measured_at', sa.DateTime, nullable=False),
        sa.Column('consumption_kwh', sa.Numeric, nullable=False),
        sa.Column('cost', sa.Numeric),
        sa.Column('source', sa.String(100)),
        sa.Column('metadata_json', postgresql.JSONB),
    )

    op.create_table(
        'analyses',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('triggered_by', sa.String(200)),
        sa.Column('triggered_at', sa.DateTime, nullable=False),
        sa.Column('kpi_snapshot', postgresql.JSONB),
        sa.Column('anomalies', postgresql.JSONB),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('notes', sa.Text),
    )

    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('analysis_id', sa.Integer, sa.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='SET NULL')),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('type', sa.String(50)),
        sa.Column('status', sa.String(20)),
        sa.Column('created_at', sa.DateTime),
    )



def downgrade():
    op.drop_table('recommendations')
    op.drop_table('analyses')
    op.drop_table('energy_consumption')
    op.drop_table('expenses')
    op.drop_table('budgets')
    op.drop_index('ix_staff_service_asof_role', table_name='staff_levels')
    op.drop_table('staff_levels')
    op.drop_index('ix_activity_service_period', table_name='activity_records')
    op.drop_table('activity_records')
    op.drop_index('ix_occupancy_service_snapshot', table_name='occupancy_snapshots')
    op.drop_table('occupancy_snapshots')
    op.drop_table('admissions')
    op.drop_table('service_capacity')
    op.drop_table('beds')
    op.drop_table('services')
