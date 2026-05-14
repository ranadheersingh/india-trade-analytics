"""UN Comtrade API → fact_trade_monthly.

Strategy: per-partner monthly pulls for India's top trade partners.
Each call: 1 partner × all HS-2 × 12 months = ~1,160 cells, well under
Comtrade's 5,000-row cap. Total calls: ~30 partners × 6 years × 2 flows.

Free-tier rate limit: ~1 req/sec. We sleep ~1.2s between calls and back
off exponentially on HTTP 429.
"""
from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import date

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline
from app.core.config import get_settings
from app.models import DimCountry, DimHsCode, FactTradeMonthly

logger = logging.getLogger(__name__)
settings = get_settings()

INDIA_M49 = 699
PUBLIC_BASE = "https://comtradeapi.un.org/public/v1/preview"
KEYED_BASE = "https://comtradeapi.un.org/data/v1/get"

THROTTLE_SECONDS = 1.2
MAX_ATTEMPTS = 4

# India's top trading partners (covers ~95%+ of bilateral trade by value).
# Pull data for these specifically so each call stays under the 5,000-row cap.
# (M49 numeric codes — Comtrade's preferred partner identifier.)
TOP_PARTNERS_M49 = [
    156,  # China
    840,  # United States
    784,  # United Arab Emirates
    682,  # Saudi Arabia
    643,  # Russian Federation
    826,  # United Kingdom
    276,  # Germany
    528,  # Netherlands
    702,  # Singapore
    344,  # Hong Kong
    50,   # Bangladesh
    76,   # Brazil
    36,   # Australia
    410,  # Republic of Korea
    392,  # Japan
    764,  # Thailand
    458,  # Malaysia
    360,  # Indonesia
    704,  # Viet Nam
    380,  # Italy
    250,  # France
    56,   # Belgium
    724,  # Spain
    792,  # Türkiye
    710,  # South Africa
    608,  # Philippines
    124,  # Canada
    484,  # Mexico
    634,  # Qatar
    414,  # Kuwait
    512,  # Oman
    368,  # Iraq
    616,  # Poland
    144,  # Sri Lanka
    524,  # Nepal
]


def _month_end_date_key(period_yyyymm: str) -> int | None:
    if len(period_yyyymm) != 6:
        return None
    try:
        y, m = int(period_yyyymm[:4]), int(period_yyyymm[4:6])
        last = calendar.monthrange(y, m)[1]
        return int(f"{y:04d}{m:02d}{last:02d}")
    except (ValueError, calendar.IllegalMonthError):
        return None


class ComtradePipeline(Pipeline):
    name = "comtrade"
    schedule_cron = "0 3 * * *"

    YEARS = 5

    async def fetch(self, db: Session) -> list[dict]:
        current_year = date.today().year
        years = list(range(current_year - self.YEARS, current_year + 1))

        api_key = settings.comtrade_api_key
        base = KEYED_BASE if api_key else PUBLIC_BASE
        headers = {"Ocp-Apim-Subscription-Key": api_key} if api_key else {}

        all_rows: list[dict] = []
        total_calls = len(TOP_PARTNERS_M49) * len(years) * 2
        logger.info("[comtrade] starting per-partner pull: %d calls planned", total_calls)
        call_idx = 0

        async with httpx.AsyncClient(timeout=120.0) as client:
            for partner_m49 in TOP_PARTNERS_M49:
                for y in years:
                    periods = ",".join(f"{y}{m:02d}" for m in range(1, 13))
                    for flow in ("M", "X"):
                        call_idx += 1
                        rows = await self._request(
                            client, base, headers,
                            partner_m49=partner_m49,
                            periods=periods,
                            flow=flow,
                        )
                        all_rows.extend(rows)
                        if call_idx % 20 == 0:
                            logger.info(
                                "[comtrade] progress %d/%d calls, %d rows accumulated",
                                call_idx, total_calls, len(all_rows),
                            )
                        await asyncio.sleep(THROTTLE_SECONDS)

        logger.info("[comtrade] fetched %d total rows", len(all_rows))
        return all_rows

    async def _request(
        self,
        client: httpx.AsyncClient,
        base: str,
        headers: dict,
        *,
        partner_m49: int,
        periods: str,
        flow: str,
    ) -> list[dict]:
        params = {
            "reporterCode": INDIA_M49,
            "period": periods,
            "partnerCode": partner_m49,
            "cmdCode": "AG2",
            "flowCode": flow,
            "partner2Code": 0,
            "customsCode": "C00",
            "motCode": 0,
            "maxRecords": 5000,
            "includeDesc": "true",
            "freqCode": "M",
            "typeCode": "C",
            "clCode": "HS",
        }
        url = f"{base}/C/M/HS"

        for attempt in range(MAX_ATTEMPTS):
            try:
                r = await client.get(url, params=params, headers=headers)

                if r.status_code == 429:
                    wait = 2 ** attempt + 1
                    logger.warning(
                        "[comtrade] 429 rate limit (partner=%s flow=%s y=%s); "
                        "backing off %ds (attempt %d/%d)",
                        partner_m49, flow, periods[:6], wait, attempt + 1, MAX_ATTEMPTS,
                    )
                    await asyncio.sleep(wait)
                    continue

                r.raise_for_status()
                payload = r.json()
                items = payload.get("data") or []
                out: list[dict] = []
                for it in items:
                    out.append({
                        "period": str(it.get("period") or ""),
                        "partner_code_iso": it.get("partnerISO"),
                        "partner_desc": it.get("partnerDesc"),
                        "hs_2": str(it.get("cmdCode") or "").zfill(2),
                        "flow": "EXPORT" if flow == "X" else "IMPORT",
                        "value_usd": it.get("primaryValue") or it.get("fobvalue") or 0,
                        "qty": it.get("qty"),
                        "qty_unit": it.get("qtyUnitAbbr"),
                    })
                return out

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[comtrade] HTTP %s partner=%s flow=%s periods=%s: %s",
                    e.response.status_code if e.response else "?",
                    partner_m49, flow, periods[:6], e,
                )
                return []
            except Exception as e:
                if attempt == MAX_ATTEMPTS - 1:
                    logger.warning(
                        "[comtrade] partner=%s flow=%s periods=%s failed after %d tries: %s",
                        partner_m49, flow, periods[:6], MAX_ATTEMPTS, e,
                    )
                    return []
                wait = 2 ** attempt
                logger.info("[comtrade] transient error, retrying in %ds: %s", wait, e)
                await asyncio.sleep(wait)

        return []

    async def transform(self, db: Session, raw: list[dict]) -> list[dict]:
        countries = {
            c.iso_alpha_3: c.country_key
            for c in db.execute(select(DimCountry)).scalars()
        }
        hs_codes = {
            h.hs_2: h.hs_code_key
            for h in db.execute(
                select(DimHsCode).where(
                    DimHsCode.hs_level == 2, DimHsCode.is_current == True
                )
            ).scalars()
        }

        out: list[dict] = []
        today_key = int(date.today().strftime("%Y%m%d"))
        skipped_country = 0
        for r in raw:
            period = r["period"]
            if len(period) == 4:
                d_key = int(f"{period}1231")
            elif len(period) == 6:
                d_key = _month_end_date_key(period)
                if not d_key:
                    continue
            else:
                continue

            iso3 = (r["partner_code_iso"] or "").upper()
            if iso3 in ("WLD", "W00", ""):
                continue
            country_key = countries.get(iso3)
            if not country_key:
                skipped_country += 1
                continue
            hs_key = hs_codes.get(r["hs_2"])
            if not hs_key:
                continue
            value = float(r["value_usd"] or 0)
            if value <= 0:
                continue

            out.append({
                "date_key": d_key,
                "direction": r["flow"],
                "hs_code_key": hs_key,
                "country_key": country_key,
                "state_key": None,
                "value_usd": value,
                "quantity": r.get("qty"),
                "quantity_kg": None,
                "n_shipments": None,
                "source_system": "COMTRADE",
                "is_provisional": False,
                "extract_date_key": today_key,
            })

        if skipped_country:
            logger.info(
                "[comtrade] skipped %d rows (partner ISO not in dim_country — "
                "consider seeding more countries)",
                skipped_country,
            )
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
                    "quantity": stmt.excluded.quantity,
                    "is_provisional": stmt.excluded.is_provisional,
                    "extract_date_key": stmt.excluded.extract_date_key,
                },
            )
            db.execute(stmt)
            loaded += len(chunk)
        db.commit()
        return loaded
