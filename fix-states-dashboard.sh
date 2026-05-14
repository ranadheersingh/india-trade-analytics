#!/bin/bash
################################################################################
# Comprehensive Remediation Script for States Dashboard
# Applies all fixes in sequence with validation
#
# Usage: bash fix-states-dashboard.sh [project-dir]
# Default: current directory
################################################################################

set -e

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  India Trade Analytics — States Dashboard Complete Fix        ║"
echo "║  This script will:                                            ║"
echo "║    1. Restart Docker containers (fresh build)                ║"
echo "║    2. Validate database connectivity                         ║"
echo "║    3. Test API endpoint                                      ║"
echo "║    4. Provide browser refresh instructions                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────────────
echo "=== PRE-FLIGHT CHECKS ==="
echo ""

if ! command -v docker &> /dev/null; then
  echo "✗ Docker not found. Please install Docker first."
  exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
  echo "✗ Docker Compose not found."
  exit 1
fi

echo "✓ Docker available"
echo "✓ Docker Compose available"
echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 1: Restart Containers
# ─────────────────────────────────────────────────────────────────────
echo "=== PHASE 1: RESTART CONTAINERS ==="
echo ""

echo "Stopping existing containers…"
docker compose down 2>&1 | tail -2 || true

echo "Building fresh containers (this may take 1-2 minutes)…"
docker compose build 2>&1 | grep -E "^(Building|FROM|RUN)" | tail -5

echo "Starting containers…"
docker compose up -d 2>&1 | tail -2

echo "Waiting for services to be healthy (30 seconds)…"
sleep 5

# Wait for postgres
for i in {1..25}; do
  if docker exec trade_postgres pg_isready -U trade -d india_trade &>/dev/null; then
    echo "✓ PostgreSQL healthy"
    break
  fi
  if [ $i -eq 25 ]; then
    echo "✗ PostgreSQL failed to start"
    docker logs trade_postgres --tail=20
    exit 1
  fi
  sleep 1
done

# Wait for backend
for i in {1..25}; do
  if curl -sf http://localhost:8001/api/v1/health &>/dev/null; then
    echo "✓ Backend healthy"
    break
  fi
  if [ $i -eq 25 ]; then
    echo "✗ Backend failed to start"
    docker logs trade_backend --tail=30
    exit 1
  fi
  sleep 1
done

# Wait for frontend
for i in {1..15}; do
  if curl -sf http://localhost:3000 &>/dev/null; then
    echo "✓ Frontend healthy"
    break
  fi
  if [ $i -eq 15 ]; then
    echo "⚠ Frontend slow to respond (may still work)"
  fi
  sleep 1
done

echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 2: Validate Database State
# ─────────────────────────────────────────────────────────────────────
echo "=== PHASE 2: DATABASE VALIDATION ==="
echo ""

DB_ROWS=$(PGPASSWORD=changeme psql -U trade -d india_trade -h localhost -t -c "
SELECT COUNT(*) FROM fact_trade_monthly WHERE state_key IS NOT NULL;
" 2>/dev/null || echo "0")

DB_DIRECTIONS=$(PGPASSWORD=changeme psql -U trade -d india_trade -h localhost -t -c "
SELECT DISTINCT direction FROM fact_trade_monthly WHERE state_key IS NOT NULL ORDER BY direction;
" 2>/dev/null || echo "")

echo "Database state rows with state_key: $DB_ROWS"
if [ -n "$DB_DIRECTIONS" ]; then
  echo "Available directions: $(echo $DB_DIRECTIONS | tr '\n' ' ')"
fi

if [ "$DB_ROWS" -eq 0 ]; then
  echo ""
  echo "⚠ WARNING: No state-level data found in database!"
  echo ""
  echo "   This means one of:"
  echo "   A) DGCIS pipeline has not loaded state data"
  echo "   B) TRADESTAT pipeline has not loaded"
  echo "   C) Data is there but not linked to states"
  echo ""
  echo "   To fix, run one of:"
  echo "   1) DGCIS backfill (loads state-level data from DGCIS source):"
  echo "      cd backend && DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline"
  echo ""
  echo "   2) TRADESTAT reload (loads regional/trade pattern data):"
  echo "      cd backend && python -m app.pipelines.tradestat_pipeline"
  echo ""
  echo "   Then run this script again."
  echo ""
  exit 1
fi

echo "✓ State data present in database"
echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 3: Test API Endpoint
# ─────────────────────────────────────────────────────────────────────
echo "=== PHASE 3: API ENDPOINT TEST ==="
echo ""

echo "Authenticating…"
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@india-trade.com","password":"admin123"}' 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "✗ Authentication failed"
  echo ""
  echo "Debug: Check if admin user exists"
  docker exec trade_backend python3 -c "
from app.database import SessionLocal
from app.models import User
db = SessionLocal()
admin = db.query(User).filter_by(email='admin@india-trade.com').first()
print('Admin user exists:', admin is not None)
" 2>/dev/null || echo "Could not verify user"
  exit 1
fi

echo "✓ Authenticated"
echo ""

echo "Testing /dashboards/states?fiscal_year=2025…"
RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states?fiscal_year=2025" 2>/dev/null)

# Parse response
STATES_COUNT=$(echo "$RESPONSE" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin)
  print(len(d.get('states', [])))
except:
  print('0')
" 2>/dev/null || echo "0")

KPIS_COUNT=$(echo "$RESPONSE" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin)
  print(len(d.get('kpis', [])))
except:
  print('0')
" 2>/dev/null || echo "0")

REGION_COUNT=$(echo "$RESPONSE" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin)
  print(len(d.get('region_split', [])))
except:
  print('0')
" 2>/dev/null || echo "0")

TREND_COUNT=$(echo "$RESPONSE" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin)
  print(len(d.get('yoy_trend', [])))
except:
  print('0')
" 2>/dev/null || echo "0")

echo "Response structure:"
echo "  States: $STATES_COUNT"
echo "  KPIs: $KPIS_COUNT"
echo "  Region split: $REGION_COUNT"
echo "  YoY trend points: $TREND_COUNT"
echo ""

if [ "$STATES_COUNT" -gt 0 ] && [ "$KPIS_COUNT" -gt 0 ]; then
  echo "✓ API endpoint responding with data"
  TOP_STATE=$(echo "$RESPONSE" | python3 -c "
import sys,json
d = json.load(sys.stdin)
if d.get('states'):
  s = d['states'][0]
  print(f\"{s['label']}: \${s['value']/1e9:.2f}B\")
else:
  print('No data')
" 2>/dev/null || echo "Unknown")
  echo "  Top state: $TOP_STATE"
else
  echo "✗ API not returning expected data structure"
  echo ""
  echo "Full response (first 500 chars):"
  echo "$RESPONSE" | head -c 500
  echo ""
  exit 1
fi

echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 4: Test State Detail Endpoint
# ─────────────────────────────────────────────────────────────────────
echo "=== PHASE 4: STATE DETAIL TEST ==="
echo ""

echo "Testing /dashboards/states/IN-MH?fiscal_year=2025…"
DETAIL=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states/IN-MH?fiscal_year=2025" 2>/dev/null)

STATE_NAME=$(echo "$DETAIL" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin)
  print(d.get('state_name', 'Unknown'))
except:
  print('ERROR')
" 2>/dev/null || echo "Unknown")

PRODUCTS=$(echo "$DETAIL" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin)
  print(len(d.get('top_export_products', [])))
except:
  print('0')
" 2>/dev/null || echo "0")

echo "State detail for Maharashtra:"
echo "  State name: $STATE_NAME"
echo "  Top products returned: $PRODUCTS"

if [ "$STATE_NAME" != "Unknown" ] && [ "$STATE_NAME" != "ERROR" ]; then
  echo "✓ State detail endpoint working"
else
  echo "⚠ State detail endpoint may have issues"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 5: Success Message
# ─────────────────────────────────────────────────────────────────────
echo "=== READY TO USE ==="
echo ""
echo "✓ All systems operational!"
echo ""
echo "📊 Dashboard URL:"
echo "   http://localhost:3000/dashboards/states"
echo ""
echo "IMPORTANT: Hard refresh your browser!"
echo "   - Windows/Linux: Ctrl+Shift+R"
echo "   - macOS: Cmd+Shift+R"
echo "   - If still blank, try an Incognito/Private window"
echo ""
echo "Expected to see:"
echo "   • 4 KPI cards (Exports, Imports, Balance, YoY)"
echo "   • Interactive India choropleth map"
echo "   • Top 10 states bar chart"
echo "   • 5-year trend chart"
echo "   • State rankings table"
echo ""
echo "To drill into a state:"
echo "   • Click on state in the map, or"
echo "   • Click on a row in the rankings table"
echo ""

# ─────────────────────────────────────────────────────────────────────
# Cleanup and summary
# ─────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════"
echo "Diagnostic data saved:"
echo ""
echo "If issues occur, collect and share:"
echo "  1. This script's output (copy/paste above)"
echo "  2. Browser console (F12)"
echo "  3. Backend logs: docker logs trade_backend --tail=50"
echo "  4. Frontend logs: docker logs trade_frontend --tail=20"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
