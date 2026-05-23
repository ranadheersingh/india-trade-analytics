"""Phase 2-4 transaction tables

Adds: dim_exporter, dim_importer, dim_port, dim_transport_mode,
      fact_export_transactions, fact_import_transactions, fact_shipment_tracking

Revision ID: 003_phase2_tables
Revises: 002_state_key_uq
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_phase2_tables"
down_revision = "002_state_key_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # dim_transport_mode                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "dim_transport_mode",
        sa.Column("transport_mode_key", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("transport_mode_code", sa.String(10), nullable=False),
        sa.Column("transport_mode_name", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("transport_mode_key"),
        sa.UniqueConstraint("transport_mode_code", name="uq_transport_mode_code"),
        schema="dw",
    )
    op.create_index("idx_transport_mode_code", "dim_transport_mode", ["transport_mode_code"], schema="dw")

    # ------------------------------------------------------------------ #
    # dim_exporter                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "dim_exporter",
        sa.Column("exporter_key", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("iec_code", sa.String(10), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("pan_number", sa.String(10), nullable=True),
        sa.Column("gst_number", sa.String(15), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state_code", sa.String(5), nullable=True),
        sa.Column("pincode", sa.String(6), nullable=True),
        sa.Column("contact_person", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(15), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("first_export_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_export_date", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("exporter_key"),
        sa.UniqueConstraint("iec_code", name="uq_exporter_iec"),
        sa.ForeignKeyConstraint(["state_code"], ["dw.dim_state.state_code"], name="fk_exporter_state"),
        schema="dw",
    )
    op.create_index("idx_exporter_iec", "dim_exporter", ["iec_code"], schema="dw")

    # ------------------------------------------------------------------ #
    # dim_importer                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "dim_importer",
        sa.Column("importer_key", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("importer_name", sa.String(255), nullable=False),
        sa.Column("country_key", sa.BigInteger(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("contact_person", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(15), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("importer_key"),
        sa.ForeignKeyConstraint(["country_key"], ["dw.dim_country.country_key"], name="fk_importer_country"),
        schema="dw",
    )

    # ------------------------------------------------------------------ #
    # dim_port                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "dim_port",
        sa.Column("port_key", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("port_code", sa.String(10), nullable=False),
        sa.Column("port_name", sa.String(100), nullable=False),
        sa.Column("country_key", sa.BigInteger(), nullable=False),
        sa.Column("port_type", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("port_key"),
        sa.UniqueConstraint("port_code", name="uq_port_code"),
        sa.ForeignKeyConstraint(["country_key"], ["dw.dim_country.country_key"], name="fk_port_country"),
        schema="dw",
    )
    op.create_index("idx_port_code", "dim_port", ["port_code"], schema="dw")

    # ------------------------------------------------------------------ #
    # fact_export_transactions                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "fact_export_transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("transaction_id", sa.String(50), nullable=False),
        sa.Column("export_date_key", sa.Integer(), nullable=False),
        sa.Column("exporter_key", sa.BigInteger(), nullable=False),
        sa.Column("destination_country_key", sa.BigInteger(), nullable=False),
        sa.Column("hs_code_key", sa.BigInteger(), nullable=False),
        sa.Column("port_key", sa.BigInteger(), nullable=True),
        sa.Column("transport_mode_key", sa.BigInteger(), nullable=False),
        sa.Column("value_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=True),
        sa.Column("quantity_unit", sa.String(20), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("exchange_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("value_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("shipment_status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("bill_of_lading", sa.String(50), nullable=True),
        sa.Column("container_number", sa.String(20), nullable=True),
        sa.Column("source_system", sa.String(50), nullable=False),
        sa.Column("is_provisional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extract_date_key", sa.Integer(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "source_system", name="uq_export_transaction"),
        sa.ForeignKeyConstraint(["export_date_key"], ["dw.dim_date.date_key"], name="fk_export_date"),
        sa.ForeignKeyConstraint(["exporter_key"], ["dw.dim_exporter.exporter_key"], name="fk_export_exporter"),
        sa.ForeignKeyConstraint(["destination_country_key"], ["dw.dim_country.country_key"], name="fk_export_country"),
        sa.ForeignKeyConstraint(["hs_code_key"], ["dw.dim_hs_code.hs_code_key"], name="fk_export_hs"),
        sa.ForeignKeyConstraint(["port_key"], ["dw.dim_port.port_key"], name="fk_export_port"),
        sa.ForeignKeyConstraint(["transport_mode_key"], ["dw.dim_transport_mode.transport_mode_key"], name="fk_export_transport"),
        schema="dw",
    )
    op.create_index("idx_export_date", "fact_export_transactions", ["export_date_key"], schema="dw")
    op.create_index("idx_export_exporter", "fact_export_transactions", ["exporter_key"], schema="dw")
    op.create_index("idx_export_country", "fact_export_transactions", ["destination_country_key"], schema="dw")
    op.create_index("idx_export_hs", "fact_export_transactions", ["hs_code_key"], schema="dw")
    op.create_index("idx_export_transport", "fact_export_transactions", ["transport_mode_key"], schema="dw")
    op.create_index("idx_export_txn_id", "fact_export_transactions", ["transaction_id"], schema="dw")

    # ------------------------------------------------------------------ #
    # fact_import_transactions                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "fact_import_transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("transaction_id", sa.String(50), nullable=False),
        sa.Column("import_date_key", sa.Integer(), nullable=False),
        sa.Column("importer_key", sa.BigInteger(), nullable=False),
        sa.Column("origin_country_key", sa.BigInteger(), nullable=False),
        sa.Column("hs_code_key", sa.BigInteger(), nullable=False),
        sa.Column("port_key", sa.BigInteger(), nullable=True),
        sa.Column("transport_mode_key", sa.BigInteger(), nullable=False),
        sa.Column("value_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=True),
        sa.Column("quantity_unit", sa.String(20), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("exchange_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("value_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("shipment_status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("bill_of_lading", sa.String(50), nullable=True),
        sa.Column("container_number", sa.String(20), nullable=True),
        sa.Column("source_system", sa.String(50), nullable=False),
        sa.Column("is_provisional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extract_date_key", sa.Integer(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "source_system", name="uq_import_transaction"),
        sa.ForeignKeyConstraint(["import_date_key"], ["dw.dim_date.date_key"], name="fk_import_date"),
        sa.ForeignKeyConstraint(["importer_key"], ["dw.dim_importer.importer_key"], name="fk_import_importer"),
        sa.ForeignKeyConstraint(["origin_country_key"], ["dw.dim_country.country_key"], name="fk_import_country"),
        sa.ForeignKeyConstraint(["hs_code_key"], ["dw.dim_hs_code.hs_code_key"], name="fk_import_hs"),
        sa.ForeignKeyConstraint(["port_key"], ["dw.dim_port.port_key"], name="fk_import_port"),
        sa.ForeignKeyConstraint(["transport_mode_key"], ["dw.dim_transport_mode.transport_mode_key"], name="fk_import_transport"),
        schema="dw",
    )
    op.create_index("idx_import_date", "fact_import_transactions", ["import_date_key"], schema="dw")
    op.create_index("idx_import_importer", "fact_import_transactions", ["importer_key"], schema="dw")
    op.create_index("idx_import_country", "fact_import_transactions", ["origin_country_key"], schema="dw")
    op.create_index("idx_import_hs", "fact_import_transactions", ["hs_code_key"], schema="dw")
    op.create_index("idx_import_transport", "fact_import_transactions", ["transport_mode_key"], schema="dw")

    # ------------------------------------------------------------------ #
    # fact_shipment_tracking                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "fact_shipment_tracking",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("transaction_id", sa.String(50), nullable=False),
        sa.Column("tracking_event", sa.String(50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("status_description", sa.Text(), nullable=True),
        sa.Column("carrier_name", sa.String(100), nullable=True),
        sa.Column("vessel_name", sa.String(100), nullable=True),
        sa.Column("voyage_number", sa.String(20), nullable=True),
        sa.Column("container_number", sa.String(20), nullable=True),
        sa.Column("estimated_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("source_system", sa.String(50), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "tracking_event", "event_timestamp", name="uq_shipment_tracking"),
        schema="dw",
    )
    op.create_index("idx_tracking_transaction", "fact_shipment_tracking", ["transaction_id"], schema="dw")
    op.create_index("idx_tracking_event", "fact_shipment_tracking", ["tracking_event"], schema="dw")
    op.create_index("idx_tracking_timestamp", "fact_shipment_tracking", ["event_timestamp"], schema="dw")


def downgrade() -> None:
    op.drop_table("fact_shipment_tracking", schema="dw")
    op.drop_table("fact_import_transactions", schema="dw")
    op.drop_table("fact_export_transactions", schema="dw")
    op.drop_table("dim_port", schema="dw")
    op.drop_table("dim_importer", schema="dw")
    op.drop_table("dim_exporter", schema="dw")
    op.drop_table("dim_transport_mode", schema="dw")
