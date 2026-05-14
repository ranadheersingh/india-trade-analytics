#!/bin/bash
###############################################################################
# v2 Install: State Performance with India map + drill-in
#
# Run AFTER 01_diagnose_and_cleanup.sh
# Assumes you've copied this folder to your project as: v2_deliverables/
###############################################################################
set -e

PROJECT_DIR="${PROJECT_DIR:-$HOME/RANA/AATREE/exports/india-trade-analytics}"
DELIVER_DIR="${DELIVER_DIR:-$PROJECT_DIR/v2_deliverables}"

cd "$PROJECT_DIR"

echo "================================================================"
echo " v2 INSTALL — State Performance with India map"
echo "================================================================"
echo ""

# ─────────────────────────────────────────────────────────────────
# 1. Backend changes
# ─────────────────────────────────────────────────────────────────
echo "[1/5] Backend: schemas + services + router"

# Backup
cp backend/app/schemas/dashboards.py     backend/app/schemas/dashboards.py.bak
cp backend/app/services/dashboards.py    backend/app/services/dashboards.py.bak
cp backend/app/api/v1/dashboards.py      backend/app/api/v1/dashboards.py.bak

# Replace schemas (full file) and router (full file)
cp "$DELIVER_DIR/backend/dashboards_schemas.py"  backend/app/schemas/dashboards.py
cp "$DELIVER_DIR/backend/dashboards_router.py"   backend/app/api/v1/dashboards.py

# For services we need to surgically replace get_state_overview + add get_state_detail
# This Python helper does it safely:
python3 << 'PYEOF'
from pathlib import Path

src_path = Path("backend/app/services/dashboards.py")
new_block = Path("v2_deliverables/backend/dashboards_service_states.py").read_text()

# Extract everything from "def get_state_overview" onwards in NEW block
new_state_section_start = new_block.find("def get_state_overview")
new_state_section = new_block[new_state_section_start:]
# Stop before sector function (we don't want to replace that)
new_state_section = new_state_section.split("# ─")[0]  # noqa
# Re-extract more cleanly:
new_state_section = new_block[new_state_section_start:]

orig = src_path.read_text()

# Find the section in original from get_state_overview to get_sector_detail
start = orig.find("def get_state_overview")
end = orig.find("def get_sector_detail")
if start < 0 or end < 0:
    print("⚠️  Could not locate state functions in services/dashboards.py")
    print("    Manual merge required - see v2_deliverables/backend/dashboards_service_states.py")
else:
    # Build replacement: everything before get_state_overview + new state funcs + get_sector_detail onward
    replaced = orig[:start] + new_state_section.rstrip() + "\n\n\n" + orig[end:]
    src_path.write_text(replaced)
    print("✅ services/dashboards.py: replaced get_state_overview + added get_state_detail")

# Also need to add StateDetail to the imports at the top
content = src_path.read_text()
old_import = "from app.schemas.dashboards import (\n    ExecutiveOverview, CountryDetail, StateOverview, SectorDetail,"
new_import = "from app.schemas.dashboards import (\n    ExecutiveOverview, CountryDetail, StateOverview, StateDetail, SectorDetail,"
if old_import in content:
    src_path.write_text(content.replace(old_import, new_import))
    print("✅ Added StateDetail to imports")
PYEOF

echo "✅ Backend updated"
echo ""

# ─────────────────────────────────────────────────────────────────
# 2. Frontend: India map component
# ─────────────────────────────────────────────────────────────────
echo "[2/5] Frontend: IndiaMap component + state pages"

mkdir -p frontend/src/components/charts
mkdir -p "frontend/src/app/dashboards/states/[stateCode]"

cp "$DELIVER_DIR/frontend/states/IndiaMap.tsx" \
   frontend/src/components/charts/IndiaMap.tsx

# Backup existing state page
cp frontend/src/app/dashboards/states/page.tsx \
   frontend/src/app/dashboards/states/page.tsx.bak

cp "$DELIVER_DIR/frontend/states/page.tsx" \
   frontend/src/app/dashboards/states/page.tsx

cp "$DELIVER_DIR/frontend/states/[stateCode]_page.tsx" \
   "frontend/src/app/dashboards/states/[stateCode]/page.tsx"

echo "✅ Frontend pages installed"
echo ""

# ─────────────────────────────────────────────────────────────────
# 3. Download India GeoJSON
# ─────────────────────────────────────────────────────────────────
echo "[3/5] Downloading India states GeoJSON"

mkdir -p frontend/public

# This is a public India state boundaries geoJSON with ST_NM property
GEO_URL="https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"

if curl -sf -o frontend/public/india-states.geojson "$GEO_URL"; then
    SIZE=$(wc -c < frontend/public/india-states.geojson)
    if [ "$SIZE" -gt 10000 ]; then
        echo "✅ india-states.geojson downloaded ($SIZE bytes)"
    else
        echo "⚠️  GeoJSON file looks too small. Manually verify: frontend/public/india-states.geojson"
    fi
else
    echo "⚠️  Could not auto-download geoJSON. Please manually save to:"
    echo "    frontend/public/india-states.geojson"
    echo "    Source: $GEO_URL"
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# 4. Rebuild
# ─────────────────────────────────────────────────────────────────
echo "[4/5] Rebuilding backend"

docker compose build backend 2>&1 | tail -5
docker compose restart backend
sleep 20

if curl -sf http://localhost:8001/api/v1/health > /dev/null; then
    echo "✅ Backend healthy"
else
    echo "❌ Backend failed to start. Check: docker compose logs backend"
    exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# 5. Verify
# ─────────────────────────────────────────────────────────────────
echo "[5/5] Smoke test new endpoint"

TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@india-trade.com","password":"admin123"}' | \
    python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

echo "Testing: GET /api/v1/dashboards/states (overview with KPIs)"
curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states?fiscal_year=2025" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  fiscal_year: {d.get(\"fiscal_year\")}')
print(f'  states returned: {len(d.get(\"states\", []))}')
print(f'  has KPIs: {bool(d.get(\"kpis\"))}')
print(f'  has region_split: {bool(d.get(\"region_split\"))}')
"

echo ""
echo "Testing: GET /api/v1/dashboards/states/MH (Maharashtra drill-in)"
curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states/MH?fiscal_year=2025" | \
    python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'  state_name: {d.get(\"state_name\")}')
    print(f'  KPIs: {len(d.get(\"kpis\", []))}')
    print(f'  monthly_trend points: {len(d.get(\"monthly_trend\", []))}')
    print(f'  top_export_products: {len(d.get(\"top_export_products\", []))}')
except Exception as e:
    print(f'  Could not parse response: {e}')
"

echo ""
echo "================================================================"
echo " ✅ v2 install complete"
echo "================================================================"
echo ""
echo "Now restart the frontend dev server:"
echo "  cd frontend && npm run dev"
echo ""
echo "Then visit: http://localhost:3000/dashboards/states"
echo ""
echo "If the map area is blank but data loads, check:"
echo "  - frontend/public/india-states.geojson exists and is non-empty"
echo "  - Browser console for errors"
echo "  - State names in DB match the geoJSON ST_NM property"
echo ""
