"""Seed loader. Idempotent — safe to run multiple times.

Loads:
  - dim_date: from 2010-01-01 to 2035-12-31
  - dim_country: from countries.json
  - dim_state: from states.json
  - dim_hs_code: HS-2 chapters from hs_codes.json
  - dim_currency: a few key currencies
  - dim_macro_indicator: a few World Bank indicators
  - ops.users: admin user (from env)
"""
from __future__ import annotations
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.config import get_settings
from app.core.security import hash_password
from app.ingestion.niryat_phase2 import load_sample_data
from app.models import (
    DimDate, DimCountry, DimState, DimHsCode, DimCurrency,
    DimMacroIndicator, User,
)

logger = logging.getLogger(__name__)
SEED_DIR = Path(__file__).parent
settings = get_settings()


def _date_key(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def _fiscal_year_in(d: date) -> int:
    """Indian FY: Apr–Mar. FY26 = 2025-04-01..2026-03-31."""
    return d.year + 1 if d.month >= 4 else d.year


def _fiscal_quarter_in(d: date) -> int:
    fy_month = ((d.month - 4) % 12) + 1
    return (fy_month - 1) // 3 + 1


def _fiscal_month_in(d: date) -> int:
    return ((d.month - 4) % 12) + 1


def seed_dim_date(db: Session, start: date = date(2010, 1, 1), end: date = date(2035, 12, 31)):
    existing = db.execute(select(DimDate.date_key).limit(1)).first()
    if existing:
        logger.info("dim_date already populated, skipping")
        return

    rows = []
    d = start
    while d <= end:
        is_month_end = (d + timedelta(days=1)).month != d.month
        next_day = d + timedelta(days=1)
        is_quarter_end = is_month_end and d.month in (3, 6, 9, 12)
        is_fy_end_in = is_month_end and d.month == 3
        rows.append(
            DimDate(
                date_key=_date_key(d),
                full_date=d,
                day_of_month=d.day,
                day_of_week=d.weekday() + 1,  # 1=Mon..7=Sun
                day_name=d.strftime("%A"),
                week_of_year=int(d.strftime("%V")),
                month_num=d.month,
                month_name=d.strftime("%B"),
                quarter_num=(d.month - 1) // 3 + 1,
                calendar_year=d.year,
                fiscal_year_in=_fiscal_year_in(d),
                fiscal_quarter_in=_fiscal_quarter_in(d),
                fiscal_month_in=_fiscal_month_in(d),
                is_weekend=d.weekday() >= 5,
                is_month_end=is_month_end,
                is_quarter_end=is_quarter_end,
                is_fiscal_year_end_in=is_fy_end_in,
            )
        )
        d = next_day
    db.add_all(rows)
    db.commit()
    logger.info("Inserted %d rows into dim_date", len(rows))


def seed_countries(db: Session):
    existing = db.execute(select(DimCountry.country_key).limit(1)).first()
    if existing:
        logger.info("dim_country already populated, skipping")
        return
    data = json.loads((SEED_DIR / "countries.json").read_text(encoding="utf-8"))
    for c in data:
        db.add(DimCountry(
            iso_alpha_2=c["a2"],
            iso_alpha_3=c["a3"],
            iso_numeric=c["n"],
            country_name=c["name"],
            region=c.get("region"),
            sub_region=c.get("sub_region"),
            continent=c.get("continent"),
            income_group=c.get("income"),
            is_landlocked=c.get("landlocked"),
            primary_currency_code=c.get("currency"),
        ))
    db.commit()
    logger.info("Inserted %d rows into dim_country", len(data))


def seed_states(db: Session):
    existing = db.execute(select(DimState.state_key).limit(1)).first()
    if existing:
        logger.info("dim_state already populated, skipping")
        return
    data = json.loads((SEED_DIR / "states.json").read_text(encoding="utf-8"))
    for s in data:
        db.add(DimState(
            state_code=s["code"],
            state_name=s["name"],
            is_union_territory=s["ut"],
            region=s.get("region"),
            capital=s.get("capital"),
            is_coastal=s.get("coastal"),
        ))
    db.commit()
    logger.info("Inserted %d rows into dim_state", len(data))


def seed_hs_codes(db: Session):
    existing = db.execute(select(DimHsCode.hs_code_key).limit(1)).first()
    if existing:
        logger.info("dim_hs_code already populated, skipping")
        return
    data = json.loads((SEED_DIR / "hs_codes.json").read_text(encoding="utf-8"))
    for h in data:
        db.add(DimHsCode(
            hs_code=h["hs"],
            hs_level=2,
            hs_2=h["hs"],
            hs_4=None,
            hs_6=None,
            hs_version="HS22",
            description=h["desc"],
            section_code=h.get("section"),
            section_name=h.get("section_name"),
        ))
    db.commit()
    logger.info("Inserted %d rows into dim_hs_code", len(data))


def seed_currencies(db: Session):
    existing = db.execute(select(DimCurrency.currency_key).limit(1)).first()
    if existing:
        return
    currencies = [
        ("USD", "US Dollar", "$"),       ("INR", "Indian Rupee", "Rs"),
        ("EUR", "Euro", "EUR"),         ("GBP", "Pound Sterling", "GBP"),
        ("JPY", "Japanese Yen", "JPY"), ("CNY", "Chinese Yuan", "CNY"),
        ("AED", "UAE Dirham", "AED"),   ("SGD", "Singapore Dollar", "SGD"),
        ("AUD", "Australian Dollar", "AUD"), ("CAD", "Canadian Dollar", "CAD"),
        ("CHF", "Swiss Franc", "CHF"),  ("HKD", "Hong Kong Dollar", "HKD"),
        ("KRW", "South Korean Won", "KRW"), ("BRL", "Brazilian Real", "BRL"),
        ("ZAR", "South African Rand", "ZAR"), ("RUB", "Russian Ruble", "RUB"),
        ("MXN", "Mexican Peso", "MXN"), ("SAR", "Saudi Riyal", "SAR"),
        ("THB", "Thai Baht", "THB"),    ("MYR", "Malaysian Ringgit", "MYR"),
        ("IDR", "Indonesian Rupiah", "IDR"), ("VND", "Vietnamese Dong", "VND"),
        ("BDT", "Bangladeshi Taka", "BDT"), ("PKR", "Pakistani Rupee", "PKR"),
        ("LKR", "Sri Lankan Rupee", "LKR"), ("NPR", "Nepalese Rupee", "NPR"),
        ("EGP", "Egyptian Pound", "EGP"), ("NGN", "Nigerian Naira", "NGN"),
        ("KES", "Kenyan Shilling", "KES"), ("TRY", "Turkish Lira", "TRY"),
        ("ILS", "Israeli Shekel", "ILS"), ("QAR", "Qatari Riyal", "QAR"),
        ("KWD", "Kuwaiti Dinar", "KWD"), ("OMR", "Omani Rial", "OMR"),
        ("BHD", "Bahraini Dinar", "BHD"), ("NZD", "New Zealand Dollar", "NZD"),
    ]
    for code, name, sym in currencies:
        db.add(DimCurrency(currency_code=code, currency_name=name, symbol=sym))
    db.commit()
    logger.info("Inserted %d rows into dim_currency", len(currencies))


def seed_macro_indicators(db: Session):
    existing = db.execute(select(DimMacroIndicator.indicator_key).limit(1)).first()
    if existing:
        return
    indicators = [
        ("NY.GDP.MKTP.CD",    "GDP (current US$)",                    "GDP", "WB", "USD",   "ANNUAL"),
        ("NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)",                "GDP", "WB", "PCT",   "ANNUAL"),
        ("FP.CPI.TOTL.ZG",    "Inflation, consumer prices (annual %)","CPI", "WB", "PCT",   "ANNUAL"),
        ("NE.EXP.GNFS.CD",    "Exports of goods and services (current US$)", "TRADE", "WB", "USD", "ANNUAL"),
        ("NE.IMP.GNFS.CD",    "Imports of goods and services (current US$)", "TRADE", "WB", "USD", "ANNUAL"),
        ("BX.GSR.GNFS.CD",    "Exports of goods, services, primary income", "TRADE", "WB", "USD", "ANNUAL"),
    ]
    for code, name, cat, src, unit, freq in indicators:
        db.add(DimMacroIndicator(
            indicator_code=code, indicator_name=name, category=cat,
            source=src, unit=unit, frequency=freq,
        ))
    db.commit()
    logger.info("Inserted %d rows into dim_macro_indicator", len(indicators))


def seed_admin_user(db: Session):
    existing = db.execute(select(User).where(User.email == settings.admin_email)).scalar_one_or_none()
    if existing:
        logger.info("Admin user already exists")
        return
    db.add(User(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
        full_name="Administrator",
        role="admin",
        is_active=True,
    ))
    db.commit()
    logger.info("Created admin user: %s", settings.admin_email)


def run_all_seeds():
    logger.info("Running seeds…")
    db = SessionLocal()
    try:
        seed_dim_date(db)
        seed_countries(db)
        seed_states(db)
        seed_hs_codes(db)
        seed_currencies(db)
        seed_macro_indicators(db)
        seed_admin_user(db)

        # Load Phase 2-4 sample data
        load_sample_data()

        logger.info("Seeds complete")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_all_seeds()
