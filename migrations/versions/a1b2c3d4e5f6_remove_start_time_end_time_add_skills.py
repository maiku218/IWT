"""Remove start_time end_time add skills_acquired to work_logs

Revision ID: a1b2c3d4e5f6
Revises: 7de583e8becc
Create Date: 2026-11-08 08:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '7de583e8becc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('work_logs') as batch_op:
        batch_op.drop_column('start_time')
        batch_op.drop_column('end_time')
        batch_op.add_column(sa.Column('skills_acquired', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('work_logs') as batch_op:
        batch_op.drop_column('skills_acquired')
        batch_op.add_column(sa.Column('end_time', sa.Time(), nullable=True))
        batch_op.add_column(sa.Column('start_time', sa.Time(), nullable=True))
