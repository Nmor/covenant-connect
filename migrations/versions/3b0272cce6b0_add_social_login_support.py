"""add social login support

Revision ID: 3b0272cce6b0
Revises: 68e2dcb06a14
Create Date: 2024-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b0272cce6b0'
down_revision = '68e2dcb06a14'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('auth_provider_id', sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        'uq_users_provider_identity', 'users', ['auth_provider', 'auth_provider_id']
    )
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(length=256),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(length=256),
        nullable=False,
    )
    op.drop_constraint('uq_users_provider_identity', 'users', type_='unique')
    op.drop_column('users', 'auth_provider_id')
    op.drop_column('users', 'auth_provider')
