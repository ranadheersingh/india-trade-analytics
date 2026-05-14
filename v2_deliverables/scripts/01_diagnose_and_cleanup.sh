#!/bin/bash
###############################################################################
# Step 1: Diagnose why dashboards are empty + clean up unused files
###############################################################################
set -e

PROJECT_DIR="${PROJECT_DIR:-$HOME/RANA/AATREE/exports/india-trade-analytics}"
cd "$PROJECT_DIR"

echo "================================================================"
echo " DIAGNOSTIC: Why is State Performance empty?"
echo "================================================================"

docker compose exec -T postgres psql -U biuser -d india_trade <<'EOSQL'

-- 1. How much data per source/direction?
\echo '--- Data inventory by source ---'
SELECT source_system, direction,
       COUNT(*) AS rows,
       COUNT(DISTINCT date_key) AS distinct_dates,
       MIN(date_key) AS earliest_date_key,
       MAX(date_key) AS latest_date_key,
       ROUND(SUM(value_usd)::numeric/1e9, 2) AS bn_usd
FROM dw.fact_trade_monthly
GROUP BY source_system, direction
ORDER BY source_system, direction;

-- 2. What FYs does our data cover? (this is what matters for State Performance)
\echo '--- Fiscal years available (joined to dim_date) ---'
SELECT d.fiscal_year_in,
       COUNT(*) FILTER (WHERE f.direction = 'EXPORT') AS export_rows,
       COUNT(*) FILTER (WHERE f.direction = 'IMPORT') AS import_rows,
       COUNT(*) FILTER (WHERE f.state_key IS NOT NULL) AS rows_with_state
FROM dw.fact_trade_monthly f
JOIN dw.dim_date d ON d.date_key = f.date_key
GROUP BY d.fiscal_year_in
ORDER BY d.fiscal_year_in;

-- 3. State Performance specifically: how many rows match the dashboard filter?
--    The frontend asks for fiscal_year=2026 by default
\echo '--- Rows that State Performance dashboard would find for FY2026 ---'
SELECT COUNT(*) AS matching_rows,
       COUNT(DISTINCT f.state_key) AS distinct_states,
       ROUND(SUM(f.value_usd)::numeric/1e9, 2) AS bn_usd
FROM dw.fact_trade_monthly f
JOIN dw.dim_date d ON d.date_key = f.date_key
WHERE d.fiscal_year_in = 2026
  AND f.direction = 'EXPORT'
  AND f.state_key IS NOT NULL;

-- 4. Same query, but for whatever FY actually has data
\echo '--- Most recent FY with state-level export data ---'
SELECT d.fiscal_year_in, COUNT(*) AS rows
FROM dw.fact_trade_monthly f
JOIN dw.dim_date d ON d.date_key = f.date_key
WHERE f.direction = 'EXPORT' AND f.state_key IS NOT NULL
GROUP BY d.fiscal_year_in
ORDER BY d.fiscal_year_in DESC
LIMIT 5;

-- 5. State name verification (must match GeoJSON for map)
\echo '--- States in dim_state ---'
SELECT state_code, state_name, region FROM dw.dim_state ORDER BY state_name;

EOSQL

echo ""
echo "================================================================"
echo " CLEANUP: Remove development scratch files & old script versions"
echo "================================================================"
echo ""
echo "About to delete these files (review first, Ctrl-C to abort):"
echo ""

# Root-level scratch files
echo "Root-level scratch files:"
ls -1 tradestat_autoscraper.py tradestat_final.py test_eximp.py 2>/dev/null
ls -1 setup_tradestat.sh fix_model_v2.sh Dockerfile.clean 2>/dev/null
ls -1 httpx naming resolving 2>/dev/null

# Old auto_run iterations
echo ""
echo "Old auto_run/ iterations (we keep tradestat_downloader.py + run_complete_automation.sh):"
for f in auto_run/tradestat.py auto_run/tradestat_v4_auto.py auto_run/tradestat_v5_auto.py \
         auto_run/tradestat_v6_full.py auto_run/tradestat_v7_full.py auto_run/tradestat_final_v8.py \
         auto_run/tradestat_full_auto.py auto_run/tradestat_visible_auto.py \
         auto_run/tradestat_automation.py auto_run/tradestat_pipeline.py \
         auto_run/auto_download_all.sh auto_run/run_full_automation.sh \
         auto_run/convert_and_load.sh auto_run/download_and_convert.py; do
    [ -f "$f" ] && echo "  $f"
done

echo ""
read -p "Press Enter to delete, or Ctrl-C to abort... " _

# Actually delete
rm -f tradestat_autoscraper.py tradestat_final.py test_eximp.py
rm -f setup_tradestat.sh fix_model_v2.sh Dockerfile.clean
rm -f httpx naming resolving

rm -f auto_run/tradestat.py
rm -f auto_run/tradestat_v4_auto.py auto_run/tradestat_v5_auto.py
rm -f auto_run/tradestat_v6_full.py auto_run/tradestat_v7_full.py
rm -f auto_run/tradestat_final_v8.py auto_run/tradestat_full_auto.py
rm -f auto_run/tradestat_visible_auto.py auto_run/tradestat_automation.py
rm -f auto_run/tradestat_pipeline.py
rm -f auto_run/auto_download_all.sh auto_run/run_full_automation.sh
rm -f auto_run/convert_and_load.sh auto_run/download_and_convert.py

# Keep the model backup but remove old timestamps
find backend/app/models/ -name "__init__.py.bak.*" -delete

echo ""
echo "✅ Cleaned up."
echo ""
echo "What remains in auto_run/:"
ls -la auto_run/
