"""add kpi_daily table

Revision ID: 0002_add_kpi_daily
Revises: 0001_initial_schema
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_kpi_daily'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'kpi_daily',
        sa.Column('day', sa.Date(), primary_key=True),
        sa.Column('admissions_total', sa.Integer),
        sa.Column('discharges_total', sa.Integer),
        sa.Column('occupied_beds_total', sa.Integer),
        sa.Column('capacity_total', sa.Integer),
        sa.Column('occupancy_rate', sa.Numeric),
        sa.Column('expenses_total', sa.Numeric),
        sa.Column('energy_total', sa.Numeric),
    )


def downgrade():
    op.drop_table('kpi_daily')
