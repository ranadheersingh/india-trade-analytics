"""All ORM models for the India Trade warehouse.

Layout:
- ops schema: users, ingestion_log
- dw schema: dimensions and facts
"""
from datetime import datetime, date
from sqlalchemy import (
    BigInteger, Integer, SmallInteger, String, Text, Boolean, Date, DateTime,
    ForeignKey, Numeric, UniqueConstraint, Index, JSON, func, Identity,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.core.db import Base


# ============================================================
# OPS SCHEMA
# ============================================================

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IngestionLog(Base):
    __tablename__ = "ingestion_log"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_fetched: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


# ============================================================
# DW DIMENSIONS
# ============================================================

class DimDate(Base):
    __tablename__ = "dim_date"
    __table_args__ = {"schema": "dw"}

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_name: Mapped[str] = mapped_column(String(10), nullable=False)
    week_of_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month_num: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month_name: Mapped[str] = mapped_column(String(10), nullable=False)
    quarter_num: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    calendar_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    fiscal_year_in: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    fiscal_quarter_in: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fiscal_month_in: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_month_end: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_quarter_end: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_fiscal_year_end_in: Mapped[bool] = mapped_column(Boolean, nullable=False)


class DimCountry(Base):
    __tablename__ = "dim_country"
    __table_args__ = {"schema": "dw"}

    country_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    iso_alpha_2: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    iso_alpha_3: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    iso_numeric: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    sub_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    continent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    income_group: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_landlocked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    primary_currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DimState(Base):
    __tablename__ = "dim_state"
    __table_args__ = {"schema": "dw"}

    state_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    state_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False, index=True)
    state_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_union_territory: Mapped[bool] = mapped_column(Boolean, default=False)
    region: Mapped[str | None] = mapped_column(String(20), nullable=True)
    capital: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_coastal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    population_latest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DimHsCode(Base):
    __tablename__ = "dim_hs_code"
    __table_args__ = (
        UniqueConstraint("hs_code", "hs_version", name="uq_hs_code_version"),
        Index("idx_hs_h2", "hs_2"),
        Index("idx_hs_h4", "hs_4"),
        {"schema": "dw"},
    )

    hs_code_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    hs_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    hs_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hs_2: Mapped[str] = mapped_column(String(2), nullable=False)
    hs_4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    hs_6: Mapped[str | None] = mapped_column(String(6), nullable=True)
    hs_version: Mapped[str] = mapped_column(String(10), nullable=False, default="HS22")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    section_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    section_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class DimCurrency(Base):
    __tablename__ = "dim_currency"
    __table_args__ = {"schema": "dw"}

    currency_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    currency_name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(5), nullable=True)
    decimal_places: Mapped[int] = mapped_column(SmallInteger, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DimMacroIndicator(Base):
    __tablename__ = "dim_macro_indicator"
    __table_args__ = {"schema": "dw"}

    indicator_key: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    indicator_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)


# ============================================================
# DW FACTS
# ============================================================

class FactTradeMonthly(Base):
    __tablename__ = "fact_trade_monthly"
    __table_args__ = (
        UniqueConstraint(
            "date_key", "direction", "hs_code_key", "country_key", "source_system", "region",
            name="uq_trade_monthly",
        ),
        Index("idx_tradem_date", "date_key"),
        Index("idx_tradem_country", "country_key"),
        Index("idx_tradem_hs", "hs_code_key"),
        Index("idx_tradem_direction", "direction"),
        {"schema": "dw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dw.dim_date.date_key"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    hs_code_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_hs_code.hs_code_key"), nullable=False)
    country_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_country.country_key"), nullable=False)
    state_key: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dw.dim_state.state_key"), nullable=True)
    value_usd: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False, server_default="WORLD")
    quantity: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    quantity_kg: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_shipments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False)
    extract_date_key: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactCurrencyRate(Base):
    __tablename__ = "fact_currency_rate"
    __table_args__ = (
        UniqueConstraint(
            "date_key", "base_currency_key", "quote_currency_key", "source_system",
            name="uq_fx_rate",
        ),
        {"schema": "dw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dw.dim_date.date_key"), nullable=False, index=True)
    base_currency_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_currency.currency_key"), nullable=False)
    quote_currency_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_currency.currency_key"), nullable=False)
    mid_rate: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactMacroIndicator(Base):
    __tablename__ = "fact_macro_indicator"
    __table_args__ = (
        UniqueConstraint(
            "date_key", "country_key", "indicator_key", "source_system",
            name="uq_macro_ind",
        ),
        {"schema": "dw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dw.dim_date.date_key"), nullable=False, index=True)
    country_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_country.country_key"), nullable=False, index=True)
    indicator_key: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.dim_macro_indicator.indicator_key"), nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    period_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# PHASE 2-4 TRANSACTION MODELS
# ============================================================

from .transactions import (
    DimExporter, DimImporter, DimPort, DimTransportMode,
    FactExportTransaction, FactImportTransaction, FactShipmentTracking,
)
