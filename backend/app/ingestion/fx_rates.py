"""FX Rates ingestion.

Loads currency exchange rates into:
    dw.fact_currency_rate

This project already has:
    dw.dim_currency
    dw.fact_currency_rate
    uq_fx_rate

So we do NOT use dw.fact_fx_rates.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline
from app.models import DimCurrency, FactCurrencyRate

logger = logging.getLogger(__name__)


class FxRatesPipeline(Pipeline):
    name = "fx_rates"
    schedule_cron = "0 5 * * *"

    async def fetch(self, db: Session) -> list[dict]:
        """
        Fetch latest FX rates.

        We use Frankfurter API because it does not require an API key.
        Base = USD.
        Quote currencies are taken from dw.dim_currency.
        """
        codes = [
            c.currency_code
            for c in db.execute(
                select(DimCurrency).where(DimCurrency.is_active == True)
            ).scalars()
        ]

        # USD->USD is always 1.0
        target_codes = [c for c in codes if c != "USD"]

        if not target_codes:
            logger.warning("[fx_rates] No active currencies found in dim_currency")
            return [{"base": "USD", "quote": "USD", "rate": 1.0}]

        symbols = ",".join(target_codes)

        url = "https://api.frankfurter.dev/v1/latest"
        params = {
            "from": "USD",
            "to": symbols,
        }

        rows: list[dict] = [{"base": "USD", "quote": "USD", "rate": 1.0}]

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

                rates = payload.get("rates") or {}

                for quote, rate in rates.items():
                    if rate is None:
                        continue
                    rows.append(
                        {
                            "base": "USD",
                            "quote": quote,
                            "rate": rate,
                        }
                    )

                logger.info("[fx_rates] fetched %d FX rates", len(rows))
                return rows

            except Exception as e:
                logger.exception("[fx_rates] provider failed: %s", e)
                return rows

    async def transform(self, db: Session, raw: list[dict]) -> list[dict]:
        currency_map = {
            c.currency_code: c.currency_key
            for c in db.execute(select(DimCurrency)).scalars()
        }

        today_key = int(date.today().strftime("%Y%m%d"))

        # Make sure today's date exists in dim_date
        date_exists = db.execute(
            text("SELECT 1 FROM dw.dim_date WHERE date_key = :date_key"),
            {"date_key": today_key},
        ).first()

        if not date_exists:
            logger.warning("[fx_rates] date_key %s missing in dim_date", today_key)
            return []

        rows: list[dict] = []

        for r in raw:
            base = r.get("base")
            quote = r.get("quote")
            rate = r.get("rate")

            base_key = currency_map.get(base)
            quote_key = currency_map.get(quote)

            if not base_key or not quote_key:
                logger.debug(
                    "[fx_rates] skipping unmapped currency pair %s/%s",
                    base,
                    quote,
                )
                continue

            try:
                rate_value = Decimal(str(rate))
            except Exception:
                continue

            if rate_value <= 0:
                continue

            rows.append(
                {
                    "date_key": today_key,
                    "base_currency_key": base_key,
                    "quote_currency_key": quote_key,
                    "mid_rate": rate_value,
                    "source_system": "FRANKFURTER",
                }
            )

        logger.info("[fx_rates] transformed %d rows", len(rows))
        return rows

    async def load(self, db: Session, rows: list[dict]) -> int:
        if not rows:
            logger.warning("[fx_rates] no rows to load")
            return 0

        stmt = pg_insert(FactCurrencyRate).values(rows)

        stmt = stmt.on_conflict_do_update(
            constraint="uq_fx_rate",
            set_={
                "mid_rate": stmt.excluded.mid_rate,
            },
        )

        db.execute(stmt)
        db.commit()

        logger.info("[fx_rates] loaded %d rows", len(rows))
        return len(rows)