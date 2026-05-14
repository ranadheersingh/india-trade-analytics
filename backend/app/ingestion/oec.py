"""OEC (Observatory of Economic Complexity) → fact_trade_monthly.

OEC has a public REST/GraphQL endpoint that provides annual trade data.
Free, no key required.

We use the simpler tesseract endpoint:
  https://oec.world/api/olap-proxy/data.jsonrecords?cube=trade_i_baci_a_92&...

This pipeline loads annual trade for India ↔ partners at HS-2 to back-fill
deeper history (OEC has data from 1995). Comtrade and OEC will overlap on
recent years; the unique constraint includes source_system so both coexist.
"""
from __future__ import annotations
import logging
from datetime import date
import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline
from app.models import DimCountry, DimHsCode, FactTradeMonthly

logger = logging.getLogger(__name__)
OEC_BASE = "https://oec.world/api/olap-proxy/data.jsonrecords"


class OecPipeline(Pipeline):
    name = "oec"
    schedule_cron = "0 4 * * 1"  # Mondays at 04:00

    YEARS = 10  # backfill last 10 years

    async def fetch(self, db: Session) -> list[dict]:
        current_year = date.today().year - 1  # OEC lags by ~1 year
        years = list(range(current_year - self.YEARS, current_year + 1))

        all_rows: list[dict] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for year in years:
                # Cube: trade_i_baci_a_92 — annual BACI HS92 (covers most years uniformly)
                params = {
                    "cube": "trade_i_baci_a_92",
                    "drilldowns": "Year,HS2,Exporter Country,Importer Country",
                    "measures": "Trade Value",
                    "Year": year,
                    "Exporter Country": "ASIN",  # India in OEC's coding
                    "limit": 50000,
                }
                try:
                    r = await client.get(OEC_BASE, params=params, timeout=60.0)
                    r.raise_for_status()
                    data = r.json().get("data", [])
                    for row in data:
                        all_rows.append({
                            "year": int(row.get("Year") or year),
                            "hs_2": str(row.get("HS2 ID") or "")[-2:],
                            "exporter_iso3": (row.get("Exporter Country ISO 3") or "").upper(),
                            "importer_iso3": (row.get("Importer Country ISO 3") or "").upper(),
                            "value_usd": float(row.get("Trade Value") or 0),
                            "direction": "EXPORT",
                        })
                except Exception as e:
                    logger.warning("[oec] export %d failed: %s", year, e)

                # Imports — India as importer
                params["Exporter Country"] = ""
                params["Importer Country"] = "ASIN"
                try:
                    r = await client.get(OEC_BASE, params=params, timeout=60.0)
                    r.raise_for_status()
                    data = r.json().get("data", [])
                    for row in data:
                        all_rows.append({
                            "year": int(row.get("Year") or year),
                            "hs_2": str(row.get("HS2 ID") or "")[-2:],
                            "exporter_iso3": (row.get("Exporter Country ISO 3") or "").upper(),
                            "importer_iso3": (row.get("Importer Country ISO 3") or "").upper(),
                            "value_usd": float(row.get("Trade Value") or 0),
                            "direction": "IMPORT",
                        })
                except Exception as e:
                    logger.warning("[oec] import %d failed: %s", year, e)

        logger.info("[oec] fetched %d rows", len(all_rows))
        return all_rows

    async def transform(self, db: Session, raw: list[dict]) -> list[dict]:
        countries = {c.iso_alpha_3: c.country_key for c in db.execute(select(DimCountry)).scalars()}
        hs_codes = {
            h.hs_2: h.hs_code_key
            for h in db.execute(
                select(DimHsCode).where(DimHsCode.hs_level == 2, DimHsCode.is_current == True)
            ).scalars()
        }

        out = []
        today_key = int(date.today().strftime("%Y%m%d"))
        for r in raw:
            d_key = int(f"{r['year']}1231")
            partner_iso = r["importer_iso3"] if r["direction"] == "EXPORT" else r["exporter_iso3"]
            country_key = countries.get(partner_iso)
            if not country_key:
                continue
            hs_key = hs_codes.get(r["hs_2"])
            if not hs_key:
                continue
            value = float(r["value_usd"] or 0)
            if value <= 0:
                continue
            out.append({
                "date_key": d_key,
                "direction": r["direction"],
                "hs_code_key": hs_key,
                "country_key": country_key,
                "state_key": None,
                "value_usd": value,
                "quantity": None,
                "quantity_kg": None,
                "n_shipments": None,
                "source_system": "OEC",
                "is_provisional": False,
                "extract_date_key": today_key,
            })
        return out

    async def load(self, db: Session, rows: list[dict]) -> int:
        if not rows:
            return 0
        existing_keys = {k for (k,) in db.execute(text("SELECT date_key FROM dw.dim_date"))}
        valid = [r for r in rows if r["date_key"] in existing_keys]
        loaded = 0
        BATCH = 500
        for i in range(0, len(valid), BATCH):
            chunk = valid[i:i + BATCH]
            stmt = pg_insert(FactTradeMonthly).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_trade_monthly",
                set_={
                    "value_usd": stmt.excluded.value_usd,
                    "extract_date_key": stmt.excluded.extract_date_key,
                },
            )
            db.execute(stmt)
            loaded += len(chunk)
        db.commit()
        return loaded
