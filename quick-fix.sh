#!/bin/bash
################################################################################
# Quick Diagnostic & Fix Script for States Dashboard
# Run this from project root: bash ops/quick-fix.sh
################################################################################

set -e

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  India Trade Analytics — States Dashboard Quick Diagnostic    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────
# 1. Database State Check
# ─────────────────────────────────────────────────────────────────────
echo "[1/5] Checking database state…"
echo ""

PGPASSWORD=changeme psql -U trade -d india_trade -h localhost -q -c "
SELECT 
  direction,
  COUNT(*) as total_rows,
  COUNT(DISTINCT state_key) as states_with_data,
  ROUND(100.0 * SUM(CASE WHEN state_key IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_with_state
FROM fact_trade_monthly
GROUP BY direction
ORDER BY total_rows DESC;
" 2>/dev/null || {
  echo "  ⚠ Could not connect to DB at localhost:5432"
  echo "     Ensure Docker containers are running:"
  echo "     docker compose up -d"
  exit 1
}

echo ""
echo "FY-wise state data breakdown:"
PGPASSWORD=changeme psql -U trade -d india_trade -h localhost -q -c "
SELECT 
  dd.fiscal_year_in as fy,
  ftm.direction,
  COUNT(*) as rows,
  COUNT(DISTINCT ftm.state_key) as states
FROM fact_trade_monthly ftm
JOIN dim_date dd ON ftm.date_key = dd.date_key
WHERE ftm.state_key IS NOT NULL
GROUP BY dd.fiscal_year_in, ftm.direction
ORDER BY dd.fiscal_year_in DESC, ftm.direction;
" 2>/dev/null || echo "  (No state data found)"

echo ""

# ─────────────────────────────────────────────────────────────────────
# 2. Check TRADESTAT Load Status
# ─────────────────────────────────────────────────────────────────────
echo "[2/5] Checking TRADESTAT status…"
echo ""

TRADESTAT_COUNT=$(PGPASSWORD=changeme psql -U trade -d india_trade -h localhost -t -c "
SELECT COUNT(*) FROM fact_trade_monthly WHERE region IS NOT NULL;
" 2>/dev/null || echo "0")

echo "  TRADESTAT rows in DB: $TRADESTAT_COUNT"

CSV_COUNT=$(ls data/tradestat_regional/*.csv 2>/dev/null | wc -l)
echo "  TRADESTAT CSVs on disk: $CSV_COUNT"

if [ "$CSV_COUNT" -gt 0 ] && [ "$TRADESTAT_COUNT" -eq 0 ]; then
  echo "  ⚠ CSVs exist but not loaded! Will reload in Phase 3."
fi
echo ""

# ─────────────────────────────────────────────────────────────────────
# 3. Verify Code Logic
# ─────────────────────────────────────────────────────────────────────
echo "[3/5] Verifying code logic…"

cat > /tmp/test_state_logic.py << 'PYEOF'
import sys
sys.path.insert(0, '/home/claude/india-trade-project/backend')

try:
    from app.database import SessionLocal
    from app.services.dashboards import (
        _state_directions_for_year,
        _latest_fy_with_state_data,
        get_state_overview
    )
    
    db = SessionLocal()
    
    # Test detection for FY2025
    print("\n  Testing FY2025 state data…")
    dirs_2025 = _state_directions_for_year(db=db, fy=2025)
    print(f"    Directions available: {dirs_2025 or '[none]'}")
    
    # Test fallback
    print("\n  Testing FY2026 fallback…")
    fallback_fy = _latest_fy_with_state_data(db=db, requested_fy=2026)
    print(f"    FY2026 falls back to: FY{fallback_fy}")
    
    # Try full response
    print("\n  Testing get_state_overview()…")
    result = get_state_overview(db=db, fiscal_year=2025)
    print(f"    States returned: {len(result.states)}")
    print(f"    KPIs: {len(result.kpis)}")
    if result.states:
        print(f"    Top state: {result.states[0].label} = ${result.states[0].value/1e9:.2f}B")
    
    print("\n  ✓ Code logic working")
    sys.exit(0)
    
except Exception as e:
    print(f"\n  ✗ Error in code: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

python3 /tmp/test_state_logic.py || {
  echo ""
  echo "  ✗ Code verification failed. See above for details."
  exit 1
}

# ─────────────────────────────────────────────────────────────────────
# 4. Test API Endpoint
# ─────────────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Testing API endpoint…"
echo ""

# Get token
echo "  Getting auth token…"
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@india-trade.com","password":"admin123"}' | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null) || {
  echo "  ✗ Could not get auth token"
  echo "    Is backend running? docker logs trade_backend"
  exit 1
}

if [ -z "$TOKEN" ]; then
  echo "  ✗ Auth failed"
  exit 1
fi

echo "  ✓ Got token"

# Test endpoint
echo "  Testing /dashboards/states?fiscal_year=2025…"
RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states?fiscal_year=2025" \
    2>/dev/null)

STATES_COUNT=$(echo "$RESPONSE" | python3 -c "
import sys,json
d = json.load(sys.stdin)
print(len(d.get('states', [])))
" 2>/dev/null || echo "0")

KPIS_COUNT=$(echo "$RESPONSE" | python3 -c "
import sys,json
d = json.load(sys.stdin)
print(len(d.get('kpis', [])))
" 2>/dev/null || echo "0")

echo "    States: $STATES_COUNT"
echo "    KPIs: $KPIS_COUNT"

if [ "$STATES_COUNT" -gt 0 ]; then
  echo "  ✓ API returning data"
else
  echo "  ⚠ API returning empty states (check DB in Phase 1)"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────
# 5. Browser Refresh Reminder
# ─────────────────────────────────────────────────────────────────────
echo "[5/5] Final steps…"
echo ""

if [ "$STATES_COUNT" -gt 0 ]; then
  echo "  ✓ Data is available!"
  echo ""
  echo "  Browser: http://localhost:3000/dashboards/states"
  echo "  If page is blank:"
  echo "    1. Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)"
  echo "    2. Try incognito window"
  echo "    3. Check browser console: F12 → Console tab"
else
  echo "  ⚠ No state data available"
  echo ""
  echo "  Options:"
  echo "    1. Load DGCIS with state extraction:"
  echo "       cd backend && DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline"
  echo ""
  echo "    2. Load TRADESTAT regional data:"
  echo "       cd backend && python -m app.pipelines.tradestat_pipeline"
  echo ""
  echo "    3. Wait for NIRYAT pipeline (state-level export/import split)"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Diagnostic complete — refer to STATES_DASHBOARD_FIX_GUIDE.md  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
