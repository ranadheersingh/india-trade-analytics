"""Add state_key to uq_trade_monthly constraint

State-aware sources (DGCIS, NIRYAT) need state-level uniqueness.
Existing rows have state_key=NULL which means the constraint was
effectively (date, direction, hs, country, NULL, source) for them —
no duplicates because Comtrade always wrote NULL state_key.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "002_state_key_uq"
down_revision = "813fa6ba88d2"  # Adjust if your initial migration has a different revision id
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_trade_monthly", "fact_trade_monthly", schema="dw")
    op.create_unique_constraint(
        "uq_trade_monthly",
        "fact_trade_monthly",
        ["date_key", "direction", "hs_code_key", "country_key", "state_key", "source_system"],
        schema="dw",
    )


def downgrade() -> None:
    op.drop_constraint("uq_trade_monthly", "fact_trade_monthly", schema="dw")
    op.create_unique_constraint(
        "uq_trade_monthly",
        "fact_trade_monthly",
        ["date_key", "direction", "hs_code_key", "country_key", "source_system"],
        schema="dw",
    )
