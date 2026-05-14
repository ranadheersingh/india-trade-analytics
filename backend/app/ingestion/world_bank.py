"""World Bank Open Data API → fact_macro_indicator.

Endpoint: https://api.worldbank.org/v2/country/{iso2}/indicator/{ind}?format=json
Free, no API key required.
"""
from __future__ import annotations
import logging
import httpx
from datetime import datetime, date
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline
from app.models import (
    DimCountry, DimMacroIndicator, FactMacroIndicator,
)

logger = logging.getLogger(__name__)
WB_BASE = "https://api.worldbank.org/v2"
PER_PAGE = 200


class WorldBankPipeline(Pipeline):
    name = "world_bank"
    schedule_cron = "0 2 * * *"

    INDICATORS = [
        "NY.GDP.MKTP.CD",
        "NY.GDP.MKTP.KD.ZG",
        "FP.CPI.TOTL.ZG",
        "NE.EXP.GNFS.CD",
        "NE.IMP.GNFS.CD",
        "BX.GSR.GNFS.CD",
    ]

    async def fetch(self, db: Session) -> list[dict]:
        countries = db.execute(
            select(DimCountry.iso_alpha_2, DimCountry.iso_alpha_3).where(DimCountry.is_active == True)
        ).all()

        all_rows: list[dict] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for ind in self.INDICATORS:
                # Pull all countries at once via 'all', then filter — fewer round trips.
                # But the API caps response size, so we paginate.
                page = 1
                while True:
                    url = f"{WB_BASE}/country/all/indicator/{ind}"
                    params = {
                        "format": "json", "page": page, "per_page": PER_PAGE,
                        "date": "2014:2025",
                    }
                    try:
                        r = await client.get(url, params=params)
                        r.raise_for_status()
                    except Exception as e:
                        logger.warning("[wb] %s page %d failed: %s", ind, page, e)
                        break
                    payload = r.json()
                    if not isinstance(payload, list) or len(payload) < 2:
                        break
                    meta, items = payload[0], payload[1] or []
                    for it in items:
                        # Skip aggregates (countryiso3code is empty for regions)
                        iso3 = (it.get("countryiso3code") or "").upper()
                        if not iso3 or len(iso3) != 3:
                            continue
                        if it.get("value") is None:
                            continue
                        all_rows.append({
                            "indicator_code": ind,
                            "iso3": iso3,
                            "year": int(it["date"]),
                            "value": float(it["value"]),
                        })
                    if page >= meta.get("pages", 1):
                        break
                    page += 1
        logger.info("[wb] fetched %d total rows", len(all_rows))
        return all_rows

    async def transform(self, db: Session, raw: list[dict]) -> list[dict]:
        # Map iso3 → country_key, indicator_code → indicator_key
        countries = {c.iso_alpha_3: c.country_key for c in db.execute(select(DimCountry)).scalars()}
        indicators = {
            i.indicator_code: i.indicator_key
            for i in db.execute(select(DimMacroIndicator)).scalars()
        }

        out = []
        for r in raw:
            country_key = countries.get(r["iso3"])
            if not country_key:
                continue  # Country not in our dim
            indicator_key = indicators.get(r["indicator_code"])
            if not indicator_key:
                continue
            # Use Dec 31 of that year as the date_key
            d_key = int(f"{r['year']}1231")
            out.append({
                "date_key": d_key,
                "country_key": country_key,
                "indicator_key": indicator_key,
                "value": r["value"],
                "period_type": "ANNUAL",
                "is_provisional": False,
                "source_system": "WORLD_BANK",
            })
        return out

    async def load(self, db: Session, rows: list[dict]) -> int:
        if not rows:
            return 0
        # Filter to date_keys that exist in dim_date
        existing_keys = {
            k for (k,) in db.execute(text("SELECT date_key FROM dw.dim_date"))
        }
        valid = [r for r in rows if r["date_key"] in existing_keys]
        loaded = 0
        # Batch upsert
        BATCH = 500
        for i in range(0, len(valid), BATCH):
            chunk = valid[i:i + BATCH]
            stmt = pg_insert(FactMacroIndicator).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_macro_ind",
                set_={"value": stmt.excluded.value, "is_provisional": stmt.excluded.is_provisional},
            )
            db.execute(stmt)
            loaded += len(chunk)
        db.commit()
        return loaded
