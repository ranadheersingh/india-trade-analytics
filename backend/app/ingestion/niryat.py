"""NIRYAT (niryat.gov.in) → fact_trade_monthly via official JSON API.

Fully automated: hits NIRYAT's public JSON endpoints to fetch state-wise
monthly trade values. No CSV downloads, no captcha, no scraping.

Endpoints used:
    /financial_years_list_india              → list of available FYs
    /states_group_data?start_date=&end_date= → state × month × value (the data)
    /state_list_no_fltrs?...                 → state code → state name lookup

Granularity returned: state × calendar-month × direction (export OR import).
NIRYAT does NOT split state totals by partner country or HS code, so we use
catch-all placeholders (country=IND, hs_code=99) to fit the schema.

Direction is selected via the `default_table` query parameter:
    export_achieved-sort-desc → exports
    import_achieved-sort-desc → imports
"""
from __future__ import annotations

import asyncio
import calendar
import logging
import warnings
from datetime import date

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline
from app.models import DimCountry, DimHsCode, DimState, FactTradeMonthly

# Suppress the "Unverified HTTPS request" warning since we use verify=False
# for niryat.gov.in (their TLS cert isn't trusted by the container's CA bundle)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

logger = logging.getLogger(__name__)

BASE_URL = "https://niryat.gov.in"
THROTTLE_SECONDS = 0.5     # be polite — half-second between calls
TIMEOUT_SECONDS = 60.0
MAX_ATTEMPTS = 3

# Catch-all placeholders (NIRYAT state-totals don't split by partner or HS)
CATCH_ALL_HS = "99"

# NIRYAT names → canonical names in dim_state.
# NIRYAT lowercases everything. We compare uppercased strings.
STATE_ALIASES = {
    "MAHARASHTRA": "Maharashtra",
    "GUJARAT": "Gujarat",
    "TAMIL NADU": "Tamil Nadu",
    "KARNATAKA": "Karnataka",
    "UTTAR PRADESH": "Uttar Pradesh",
    "ANDHRA PRADESH": "Andhra Pradesh",
    "ODISHA": "Odisha",
    "ORISSA": "Odisha",
    "HARYANA": "Haryana",
    "DELHI": "Delhi",
    "WEST BENGAL": "West Bengal",
    "KERALA": "Kerala",
    "TELANGANA": "Telangana",
    "RAJASTHAN": "Rajasthan",
    "MADHYA PRADESH": "Madhya Pradesh",
    "PUNJAB": "Punjab",
    "GOA": "Goa",
    "JHARKHAND": "Jharkhand",
    "CHHATTISGARH": "Chhattisgarh",
    "CHATTISGARH": "Chhattisgarh",
    "BIHAR": "Bihar",
    "ASSAM": "Assam",
    "HIMACHAL PRADESH": "Himachal Pradesh",
    "UTTARAKHAND": "Uttarakhand",
    "UTTARANCHAL": "Uttarakhand",
    "JAMMU & KASHMIR": "Jammu and Kashmir",
    "JAMMU AND KASHMIR": "Jammu and Kashmir",
    "PUDUCHERRY": "Puducherry",
    "PONDICHERRY": "Puducherry",
    "MANIPUR": "Manipur",
    "TRIPURA": "Tripura",
    "MEGHALAYA": "Meghalaya",
    "NAGALAND": "Nagaland",
    "MIZORAM": "Mizoram",
    "ARUNACHAL PRADESH": "Arunachal Pradesh",
    "SIKKIM": "Sikkim",
    "CHANDIGARH": "Chandigarh",
    "ANDAMAN & NICOBAR": "Andaman and Nicobar Islands",
    "ANDAMAN AND NICOBAR ISLANDS": "Andaman and Nicobar Islands",
    "DAMAN & DIU": "Dadra and Nagar Haveli and Daman and Diu",
    "DADRA & NAGAR HAVELI": "Dadra and Nagar Haveli and Daman and Diu",
    "DAMAN & DIU AND DADRA & NAGAR HAVELI": "Dadra and Nagar Haveli and Daman and Diu",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "Dadra and Nagar Haveli and Daman and Diu",
    "LAKSHADWEEP": "Lakshadweep",
    "LADAKH": "Ladakh",
    # Aggregate rows we want to skip if they sneak in
    "TOTAL": None,
    "ALL INDIA": None,
    "UNSPECIFIED": None,
    "STATES UNSPECIFIED": None,
    "OTHERS": None,
}


def _normalize_state(raw: str) -> str | None:
    if not raw:
        return None
    key = raw.strip().upper().replace(".", "").replace("'", "")
    if key in STATE_ALIASES:
        return STATE_ALIASES[key]
    for alias, canonical in STATE_ALIASES.items():
        if canonical and (key == alias):
            return canonical
    return None


def _month_end_date_key(monthyr: int) -> int | None:
    """202304 -> 20230430"""
    s = str(monthyr)
    if len(s) != 6:
        return None
    try:
        y, m = int(s[:4]), int(s[4:6])
        last = calendar.monthrange(y, m)[1]
        return int(f"{y:04d}{m:02d}{last:02d}")
    except (ValueError, calendar.IllegalMonthError):
        return None


def _fy_to_range(fy_start: int) -> tuple[str, str]:
    """fy_start=2024 -> ('202404', '202503')  i.e. Apr 2024 - Mar 2025"""
    return f"{fy_start:04d}04", f"{fy_start + 1:04d}03"


class NiryatPipeline(Pipeline):
    name = "niryat"
    schedule_cron = "0 6 * * *"   # daily 06:00 UTC

    # How many trailing FYs to pull on each run.  NIRYAT keeps history back to
    # FY 2017-18, so set this generously on first run, smaller for daily refreshes.
    YEARS_BACK = 8

    async def fetch(self, db: Session) -> list[dict]:
        all_rows: list[dict] = []

        async with httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=TIMEOUT_SECONDS,
            verify=False,
            headers={
                "User-Agent": "IndiaTradeAnalytics/1.0",
                "Accept": "application/json",
            },
        ) as client:
            # 1) discover available financial years
            fys = await self._fetch_fys(client)
            if not fys:
                logger.warning("[niryat] couldn't discover FYs; aborting")
                return []

            # take the trailing N years (oldest first to make insert ordering tidy)
            fys_to_pull = sorted(fys)[-self.YEARS_BACK:]
            logger.info("[niryat] FYs to pull: %s", fys_to_pull)

            # 2) for each (fy, direction), call states_group_data
            for fy_start in fys_to_pull:
                start_date, end_date = _fy_to_range(fy_start)
                for direction, table_param in (
                    ("EXPORT", "export_achieved-sort-desc"),
                    ("IMPORT", "import_achieved-sort-desc"),
                ):
                    rows = await self._fetch_state_group(
                        client, start_date, end_date, table_param,
                    )
                    logger.info(
                        "[niryat]   FY %d-%02d %s -> %d raw rows",
                        fy_start, (fy_start + 1) % 100, direction, len(rows),
                    )
                    for r in rows:
                        r["direction"] = direction
                    all_rows.extend(rows)
                    await asyncio.sleep(THROTTLE_SECONDS)

        logger.info("[niryat] total raw rows: %d", len(all_rows))
        return all_rows

    async def _fetch_fys(self, client: httpx.AsyncClient) -> list[int]:
        """Returns list of FY-start years, e.g. [2017, 2018, ..., 2024]."""
        # endpoint expects start/end placeholders; values don't matter for FY list
        params = {
            "start_date": "202304", "end_date": "202403",
            "default_table": "default",
            "sort_table": "export_achieved-sort-desc",
        }
        try:
            data = await self._get_json(client, "/financial_years_list_india", params)
            return [int(d["financial_year_start"]) for d in data if "financial_year_start" in d]
        except Exception as e:
            logger.warning("[niryat] FY list failed: %s — falling back to 2017..current", e)
            current = date.today().year
            return list(range(2017, current))

    async def _fetch_state_group(
        self,
        client: httpx.AsyncClient,
        start_date: str,
        end_date: str,
        table_param: str,
    ) -> list[dict]:
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "default_table": "default",
            "sort_table": table_param,
        }
        try:
            data = await self._get_json(client, "/states_group_data", params)
        except Exception as e:
            logger.warning(
                "[niryat] states_group_data failed for %s..%s (%s): %s",
                start_date, end_date, table_param, e,
            )
            return []

        # Response shape: {"state_data": [ {...}, {...} ]}
        if isinstance(data, dict) and "state_data" in data:
            return data["state_data"]
        if isinstance(data, list):
            return data
        logger.warning(
            "[niryat] unexpected payload shape for %s..%s: %s",
            start_date, end_date, type(data).__name__,
        )
        return []

    async def _get_json(
        self, client: httpx.AsyncClient, path: str, params: dict,
    ) -> list | dict:
        for attempt in range(MAX_ATTEMPTS):
            try:
                r = await client.get(path, params=params)
                if r.status_code == 429:
                    wait = 2 ** attempt + 1
                    logger.warning(
                        "[niryat] 429 on %s; backoff %ds (attempt %d/%d)",
                        path, wait, attempt + 1, MAX_ATTEMPTS,
                    )
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[niryat] HTTP %s on %s: %s",
                    e.response.status_code if e.response else "?", path, e,
                )
                return []
            except Exception as e:
                if attempt == MAX_ATTEMPTS - 1:
                    raise
                wait = 2 ** attempt
                logger.info("[niryat] transient error on %s, retry in %ds: %s",
                            path, wait, e)
                await asyncio.sleep(wait)
        return []

    async def transform(self, db: Session, raw: list[dict]) -> list[dict]:
        states = {
            s.state_name: s.state_key
            for s in db.execute(
                select(DimState).where(DimState.is_active == True)
            ).scalars()
        }
        india = db.execute(
            select(DimCountry).where(DimCountry.iso_alpha_3 == "IND")
        ).scalar_one_or_none()
        if not india:
            logger.error("[niryat] India (IND) missing from dim_country")
            return []
        india_key = india.country_key

        catch_all = db.execute(
            select(DimHsCode).where(
                DimHsCode.hs_2 == CATCH_ALL_HS,
                DimHsCode.hs_level == 2,
                DimHsCode.is_current == True,
            )
        ).scalar_one_or_none()
        if not catch_all:
            logger.error(
                "[niryat] HS-99 catch-all missing from dim_hs_code; "
                "ensure seeds include HS chapter 99",
            )
            return []
        hs_key = catch_all.hs_code_key

        out: list[dict] = []
        today_key = int(date.today().strftime("%Y%m%d"))
        unmatched_states: set[str] = set()
        skipped_no_value = 0
        skipped_no_date = 0

        for r in raw:
            d_key = _month_end_date_key(r.get("monthyr") or 0)
            if not d_key:
                skipped_no_date += 1
                continue

            state_name = _normalize_state(r.get("state_name") or "")
            if not state_name:
                continue

            state_key = states.get(state_name)
            if not state_key:
                unmatched_states.add(state_name)
                continue

            value = r.get("export_achieved") or r.get("import_achieved") or 0
            try:
                value_usd = float(value)
            except (ValueError, TypeError):
                value_usd = 0.0
            if value_usd <= 0:
                skipped_no_value += 1
                continue

            out.append({
                "date_key": d_key,
                "direction": r["direction"],
                "hs_code_key": hs_key,
                "country_key": india_key,
                "state_key": state_key,
                "value_usd": value_usd,
                "quantity": None,
                "quantity_kg": None,
                "n_shipments": None,
                "source_system": "NIRYAT",
                "is_provisional": False,
                "extract_date_key": today_key,
            })

        if unmatched_states:
            logger.warning(
                "[niryat] unmatched state names (add to STATE_ALIASES): %s",
                sorted(unmatched_states),
            )
        logger.info(
            "[niryat] transformed %d rows (skipped: %d no-value, %d no-date)",
            len(out), skipped_no_value, skipped_no_date,
        )
        return out

    async def load(self, db: Session, rows: list[dict]) -> int:
        if not rows:
            return 0
        existing_keys = {k for (k,) in db.execute(text("SELECT date_key FROM dw.dim_date"))}
        valid = [r for r in rows if r["date_key"] in existing_keys]

        # Wipe prior NIRYAT rows so a re-run replaces, not duplicates.
        # (Each NIRYAT cell is a state-level total, no partner/HS variation.)
        db.execute(text("DELETE FROM dw.fact_trade_monthly WHERE source_system='NIRYAT'"))

        loaded = 0
        BATCH = 500
        for i in range(0, len(valid), BATCH):
            chunk = valid[i:i + BATCH]
            stmt = pg_insert(FactTradeMonthly).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_trade_monthly",
                set_={
                    "value_usd": stmt.excluded.value_usd,
                    "is_provisional": stmt.excluded.is_provisional,
                    "extract_date_key": stmt.excluded.extract_date_key,
                },
            )
            db.execute(stmt)
            loaded += len(chunk)
        db.commit()
        return loaded
