"""
TRADESTAT Pipeline - REGIONAL VERSION (FIXED)
Loads CSV files from app/data/tradestat with region context.

Fixes included:
1. Ensures dw.fact_trade_monthly.region column exists.
2. Recreates uq_trade_monthly unique constraint including region.
3. Deletes old TRADESTAT rows before reload.
4. Deduplicates rows before insert.
5. Uses PostgreSQL ON CONFLICT DO UPDATE so duplicate regional rows will not fail the run.
6. Returns loaded count to the base pipeline so admin status will not show misleading 0 rows.
"""
import csv
import logging
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline
from app.models import DimState, DimHsCode, FactTradeMonthly

logger = logging.getLogger(__name__)

DATA_DIR = Path("app/data/tradestat")

ALL_INDIAN_STATES = [
    "Delhi", "Haryana", "Punjab", "Himachal Pradesh", "Jammu and Kashmir",
    "Ladakh", "Uttarakhand", "Uttar Pradesh", "Rajasthan", "Gujarat",
    "Daman and Diu", "Dadra and Nagar Haveli", "Maharashtra", "Goa",
    "Karnataka", "Andhra Pradesh", "Telangana", "Tamil Nadu", "Kerala",
    "Puducherry", "Andaman and Nicobar", "Lakshadweep", "Odisha",
    "Jharkhand", "West Bengal", "Sikkim", "Arunachal Pradesh", "Assam",
    "Meghalaya", "Manipur", "Mizoram", "Nagaland", "Tripura",
    "Bihar", "Madhya Pradesh", "Chhattisgarh"
]

USD_MULTIPLIER = 1_000_000


class TradestatPipeline(Pipeline):
    name = "tradestat"
    schedule_cron = "0 5 * * *"

    async def fetch(self, db: Session) -> list[dict]:
        logger.info("[tradestat] ========== STARTING (REGIONAL FIXED) ==========")

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_schema(db)

        export_files = sorted(DATA_DIR.glob("export_*.csv"))
        import_files = sorted(DATA_DIR.glob("import_*.csv"))

        logger.info("[tradestat] Files found: exports=%d, imports=%d", len(export_files), len(import_files))

        if not export_files and not import_files:
            logger.warning("[tradestat] NO CSV FILES FOUND in %s", DATA_DIR.resolve())
            return []

        states = self._load_states(db)
        hs_codes = self._load_hs_codes(db)

        logger.info("[tradestat] Loaded %d states, %d HS codes", len(states), len(hs_codes))

        # Clear all previous TRADESTAT rows before reload.
        db.execute(text("DELETE FROM dw.fact_trade_monthly WHERE source_system = 'TRADESTAT'"))
        db.commit()
        logger.info("[tradestat] Cleared existing TRADESTAT data")

        total_loaded = 0
        regions_loaded = set()
        files_failed = 0

        for fpath in export_files + import_files:
            direction = "EXPORT" if fpath.name.lower().startswith("export_") else "IMPORT"
            region = self._extract_region(fpath.name)
            regions_loaded.add(region)

            logger.info("[tradestat] === %s: %s (region=%s) ===", direction, fpath.name, region)

            try:
                rows = self._parse_csv(fpath, direction, region, states, hs_codes)
                rows = self._dedupe_rows(rows)
                if rows:
                    loaded = self._insert_rows(db, rows)
                    total_loaded += loaded
                    logger.info("[tradestat] ✅ loaded/upserted %d rows", loaded)
                else:
                    logger.info("[tradestat] No rows parsed from %s", fpath.name)
            except Exception as e:
                files_failed += 1
                logger.exception("[tradestat] ❌ Failed file %s: %s", fpath.name, e)

        logger.info("[tradestat] ========== COMPLETE ==========")
        logger.info("[tradestat] Total loaded/upserted: %d rows across %d regions; failed files=%d",
                    total_loaded, len(regions_loaded), files_failed)

        # Return dummy items so base pipeline/admin status can show loaded/fetched count instead of always 0.
        return [{"loaded": True}] * total_loaded

    def _ensure_schema(self, db: Session) -> None:
        """Ensure table has region column and unique constraint includes region."""
        logger.info("[tradestat] Ensuring schema supports region")

        db.execute(text("""
            ALTER TABLE dw.fact_trade_monthly
            ADD COLUMN IF NOT EXISTS region VARCHAR(150);
        """))
        db.commit()

        # Recreate unique constraint to include region.
        # Without this, regional imports/exports collide with same hs/country/state/date rows.
        db.execute(text("""
            ALTER TABLE dw.fact_trade_monthly
            DROP CONSTRAINT IF EXISTS uq_trade_monthly;
        """))
        db.commit()

        db.execute(text("""
            ALTER TABLE dw.fact_trade_monthly
            ADD CONSTRAINT uq_trade_monthly
            UNIQUE (
                date_key,
                direction,
                hs_code_key,
                country_key,
                state_key,
                source_system,
                region
            );
        """))
        db.commit()

    def _extract_region(self, filename: str) -> str:
        name = filename.replace(".csv", "")
        match = re.match(r"(?:export|import)_\d{4}-\d{2,4}(?:_(.+))?$", name)
        if not match or not match.group(1):
            return "WORLD"
        return match.group(1).upper().replace("-", "_").replace(" ", "_")[:150]

    def _parse_csv(
        self,
        fpath: Path,
        direction: str,
        region: str,
        states: Dict[str, int],
        hs_codes: Dict[str, int],
    ) -> List[Dict]:
        rows: List[Dict] = []
        today_key = int(date.today().strftime("%Y%m%d"))

        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                return []

            year_columns = [col for col in reader.fieldnames if self._is_year_column(col)]

            if not year_columns:
                logger.warning("[tradestat] No year columns found in %s. Headers=%s", fpath.name, reader.fieldnames)
                return []

            for record in reader:
                try:
                    hs_raw = str(record.get("HSCode", "") or record.get("HS CODE", "")).strip()
                    if not hs_raw or hs_raw.lower() == "nan":
                        continue

                    hs_code = hs_raw.zfill(2)[:2]
                    hs_code_key = hs_codes.get(hs_code)
                    if not hs_code_key:
                        continue

                    for year_col in year_columns:
                        value_str = str(record.get(year_col, "") or "").strip()
                        if not value_str or value_str.lower() == "nan":
                            continue

                        try:
                            value_million = float(value_str.replace(",", "").replace(" ", ""))
                        except ValueError:
                            continue

                        if value_million <= 0:
                            continue

                        year = self._extract_year_from_column(year_col)
                        if not year:
                            continue

                        d_key = int(f"{year:04d}0101")
                        value_usd = value_million * USD_MULTIPLIER
                        value_per_state = value_usd / len(ALL_INDIAN_STATES)

                        for state_name in ALL_INDIAN_STATES:
                            state_key = states.get(state_name.upper())
                            if not state_key:
                                continue

                            rows.append({
                                "date_key": d_key,
                                "direction": direction,
                                "hs_code_key": hs_code_key,
                                "country_key": 1,
                                "state_key": state_key,
                                "value_usd": round(value_per_state, 2),
                                "region": region,
                                "quantity": None,
                                "quantity_kg": None,
                                "n_shipments": None,
                                "source_system": "TRADESTAT",
                                "is_provisional": False,
                                "extract_date_key": today_key,
                            })
                except Exception as e:
                    logger.debug("[tradestat] Row error in %s: %s", fpath.name, e)

        logger.info("[tradestat] Parsed %d rows from %s (region=%s)", len(rows), fpath.name, region)
        return rows

    def _dedupe_rows(self, rows: List[Dict]) -> List[Dict]:
        """Combine duplicate keys before hitting the database."""
        if not rows:
            return []

        merged: Dict[Tuple, Dict] = {}
        for r in rows:
            key = (
                r["date_key"],
                r["direction"],
                r["hs_code_key"],
                r["country_key"],
                r["state_key"],
                r["source_system"],
                r.get("region") or "WORLD",
            )
            if key not in merged:
                merged[key] = dict(r)
            else:
                merged[key]["value_usd"] = round(float(merged[key]["value_usd"] or 0) + float(r["value_usd"] or 0), 2)

        if len(merged) != len(rows):
            logger.info("[tradestat] Deduped rows: %d -> %d", len(rows), len(merged))

        return list(merged.values())

    def _is_year_column(self, col_name: str) -> bool:
        return bool(re.match(r"^\d{4}-\d{2,4}$", str(col_name).strip()))

    def _extract_year_from_column(self, col_name: str) -> Optional[int]:
        match = re.match(r"^(\d{4})-\d{2,4}$", str(col_name).strip())
        return int(match.group(1)) if match else None

    def _load_states(self, db: Session) -> Dict[str, int]:
        states = {}
        for s in db.execute(select(DimState)).scalars():
            states[s.state_name.upper()] = s.state_key
        return states

    def _load_hs_codes(self, db: Session) -> Dict[str, int]:
        hs_codes = {}
        for h in db.execute(select(DimHsCode)).scalars():
            if not h.hs_code:
                continue
            code_2digit = str(h.hs_code).zfill(2)[:2]
            if code_2digit not in hs_codes:
                hs_codes[code_2digit] = h.hs_code_key
        return hs_codes

    def _insert_rows(self, db: Session, rows: List[Dict]) -> int:
        if not rows:
            return 0

        conflict_cols = [
            "date_key",
            "direction",
            "hs_code_key",
            "country_key",
            "state_key",
            "source_system",
            "region",
        ]

        batch_size = 1000
        total = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            stmt = pg_insert(FactTradeMonthly).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_cols,
                set_={
                    "value_usd": stmt.excluded.value_usd,
                    "quantity": stmt.excluded.quantity,
                    "quantity_kg": stmt.excluded.quantity_kg,
                    "n_shipments": stmt.excluded.n_shipments,
                    "is_provisional": stmt.excluded.is_provisional,
                    "extract_date_key": stmt.excluded.extract_date_key,
                },
            )
            db.execute(stmt)
            db.commit()
            total += len(batch)
            logger.info("[tradestat] inserted/upserted batch: %d/%d", min(i + batch_size, len(rows)), len(rows))

        return total

    async def transform(self, db, raw):
        # Loading is done in fetch() because TRADESTAT reads many local files sequentially.
        return []

    async def load(self, db, rows):
        return 0
