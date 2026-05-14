"""
Phase 2-4 Transaction Models
============================
New tables for export/import transactions, exporters, tracking.
"""

from datetime import datetime
from sqlalchemy import (
    BigInteger, Integer, String, Text, Boolean, DateTime, Numeric,
    ForeignKey, UniqueConstraint, Index, func, Identity,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.core.db import Base


# ============================================================
# DIMENSIONS
# ============================================================

class DimExporter(Base):
    __tablename__ = "dim_exporter"
    __table_args__ = {"schema": "dw"}

    exporter_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    iec_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pan_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(15), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(5), ForeignKey("dw.dim_state.state_code"), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(6), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_export_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_export_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DimImporter(Base):
    __tablename__ = "dim_importer"
    __table_args__ = {"schema": "dw"}

    importer_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    importer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_country.country_key"), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DimPort(Base):
    __tablename__ = "dim_port"
    __table_args__ = {"schema": "dw"}

    port_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    port_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    port_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_country.country_key"), nullable=False)
    port_type: Mapped[str] = mapped_column(String(20), nullable=False)  # sea, air, rail, road
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DimTransportMode(Base):
    __tablename__ = "dim_transport_mode"
    __table_args__ = {"schema": "dw"}

    transport_mode_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    transport_mode_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    transport_mode_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ============================================================
# FACTS
# ============================================================

class FactExportTransaction(Base):
    __tablename__ = "fact_export_transactions"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id", "source_system",
            name="uq_export_transaction",
        ),
        Index("idx_export_date", "export_date_key"),
        Index("idx_export_exporter", "exporter_key"),
        Index("idx_export_country", "destination_country_key"),
        Index("idx_export_hs", "hs_code_key"),
        Index("idx_export_transport", "transport_mode_key"),
        {"schema": "dw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    export_date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dw.dim_date.date_key"), nullable=False)
    exporter_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_exporter.exporter_key"), nullable=False)
    destination_country_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_country.country_key"), nullable=False)
    hs_code_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_hs_code.hs_code_key"), nullable=False)
    port_key: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dw.dim_port.port_key"), nullable=True)
    transport_mode_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_transport_mode.transport_mode_key"), nullable=False)
    value_usd: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    value_inr: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    shipment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    bill_of_lading: Mapped[str | None] = mapped_column(String(50), nullable=True)
    container_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False)
    extract_date_key: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactImportTransaction(Base):
    __tablename__ = "fact_import_transactions"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id", "source_system",
            name="uq_import_transaction",
        ),
        Index("idx_import_date", "import_date_key"),
        Index("idx_import_importer", "importer_key"),
        Index("idx_import_country", "origin_country_key"),
        Index("idx_import_hs", "hs_code_key"),
        Index("idx_import_transport", "transport_mode_key"),
        {"schema": "dw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    import_date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dw.dim_date.date_key"), nullable=False)
    importer_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_importer.importer_key"), nullable=False)
    origin_country_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_country.country_key"), nullable=False)
    hs_code_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_hs_code.hs_code_key"), nullable=False)
    port_key: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dw.dim_port.port_key"), nullable=True)
    transport_mode_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_transport_mode.transport_mode_key"), nullable=False)
    value_usd: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    value_inr: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    shipment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    bill_of_lading: Mapped[str | None] = mapped_column(String(50), nullable=True)
    container_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False)
    extract_date_key: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactShipmentTracking(Base):
    __tablename__ = "fact_shipment_tracking"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id", "tracking_event", "event_timestamp",
            name="uq_shipment_tracking",
        ),
        Index("idx_tracking_transaction", "transaction_id"),
        Index("idx_tracking_event", "tracking_event"),
        Index("idx_tracking_timestamp", "event_timestamp"),
        {"schema": "dw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tracking_event: Mapped[str] = mapped_column(String(50), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    status_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    carrier_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vessel_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    voyage_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    container_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())