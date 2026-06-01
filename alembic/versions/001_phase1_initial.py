"""Phase 1 initial migration (no business tables yet).

Revision ID: 001_phase1_initial
Revises:
Create Date: 2026-06-01

"""

from typing import Sequence, Union

revision: str = "001_phase1_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
