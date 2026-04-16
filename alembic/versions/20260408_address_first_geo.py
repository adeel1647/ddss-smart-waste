"""add address-first geocoding fields for bins and sites

Revision ID: 20260408_address_first_geo
Revises: 
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = '20260408_address_first_geo'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # sites
    op.add_column('sites', sa.Column('postcode', sa.String(length=16), nullable=True))
    op.add_column('sites', sa.Column('address_line_1', sa.String(length=160), nullable=True))
    op.add_column('sites', sa.Column('address_line_2', sa.String(length=160), nullable=True))
    op.add_column('sites', sa.Column('city', sa.String(length=80), nullable=True))
    op.add_column('sites', sa.Column('county', sa.String(length=80), nullable=True))
    op.add_column('sites', sa.Column('country', sa.String(length=80), nullable=True))
    op.add_column('sites', sa.Column('formatted_address', sa.String(length=255), nullable=True))
    op.add_column('sites', sa.Column('geocode_place_id', sa.String(length=120), nullable=True))
    op.add_column('sites', sa.Column('geocode_source', sa.String(length=32), nullable=True))
    op.add_column('sites', sa.Column('geocode_confidence', sa.Float(), nullable=True))
    op.create_index(op.f('ix_sites_postcode'), 'sites', ['postcode'], unique=False)
    op.create_index(op.f('ix_sites_city'), 'sites', ['city'], unique=False)
    op.create_index(op.f('ix_sites_geocode_place_id'), 'sites', ['geocode_place_id'], unique=False)

    # bins
    op.add_column('bins', sa.Column('address_line_1', sa.String(length=160), nullable=True))
    op.add_column('bins', sa.Column('address_line_2', sa.String(length=160), nullable=True))
    op.add_column('bins', sa.Column('city', sa.String(length=80), nullable=True))
    op.add_column('bins', sa.Column('county', sa.String(length=80), nullable=True))
    op.add_column('bins', sa.Column('country', sa.String(length=80), nullable=True))
    op.add_column('bins', sa.Column('formatted_address', sa.String(length=255), nullable=True))
    op.add_column('bins', sa.Column('geocode_place_id', sa.String(length=120), nullable=True))
    op.add_column('bins', sa.Column('geocode_source', sa.String(length=32), nullable=True))
    op.add_column('bins', sa.Column('geocode_confidence', sa.Float(), nullable=True))
    op.create_index(op.f('ix_bins_city'), 'bins', ['city'], unique=False)
    op.create_index(op.f('ix_bins_geocode_place_id'), 'bins', ['geocode_place_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_bins_geocode_place_id'), table_name='bins')
    op.drop_index(op.f('ix_bins_city'), table_name='bins')
    op.drop_column('bins', 'geocode_confidence')
    op.drop_column('bins', 'geocode_source')
    op.drop_column('bins', 'geocode_place_id')
    op.drop_column('bins', 'formatted_address')
    op.drop_column('bins', 'country')
    op.drop_column('bins', 'county')
    op.drop_column('bins', 'city')
    op.drop_column('bins', 'address_line_2')
    op.drop_column('bins', 'address_line_1')

    op.drop_index(op.f('ix_sites_geocode_place_id'), table_name='sites')
    op.drop_index(op.f('ix_sites_city'), table_name='sites')
    op.drop_index(op.f('ix_sites_postcode'), table_name='sites')
    op.drop_column('sites', 'geocode_confidence')
    op.drop_column('sites', 'geocode_source')
    op.drop_column('sites', 'geocode_place_id')
    op.drop_column('sites', 'formatted_address')
    op.drop_column('sites', 'country')
    op.drop_column('sites', 'county')
    op.drop_column('sites', 'city')
    op.drop_column('sites', 'address_line_2')
    op.drop_column('sites', 'address_line_1')
    op.drop_column('sites', 'postcode')
