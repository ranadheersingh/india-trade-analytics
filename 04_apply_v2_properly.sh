#!/bin/bash
###############################################################################
# Apply v2 properly:
#   1. Patch backend query to fall back to TOTAL when no EXPORT-state data
#   2. Rebuild BOTH containers (frontend was running old code)
#   3. Smoke test
###############################################################################
set -e

PROJECT_DIR="${PROJECT_DIR:-$HOME/RANA/AATREE/exports/india-trade-analytics}"
cd "$PROJECT_DIR"

# ─────────────────────────────────────────────────────────────────
# 1. Patch the state query for TOTAL fallback
# ─────────────────────────────────────────────────────────────────
echo "[1/4] Patching state query to handle TOTAL direction (DGCIS data)"

python3 << 'PYEOF'
from pathlib import Path
src = Path("backend/app/services/dashboards.py")
content = src.read_text()

# Insert helper function + patch the get_state_overview function
helper = '''def _pick_state_directions(db: Session, fy: int) -> tuple[list[str], str]:
    """Return (directions, label). Falls back to TOTAL if no EXPORT-state data."""
    has_exp = db.execute(
        select(func.count())
        .select_from(FactTradeMonthly)
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            DimDate.fiscal_year_in == fy,
            FactTradeMonthly.direction == "EXPORT",
            FactTradeMonthly.state_key.is_not(None),
        )
    ).scalar_one()
    return (["EXPORT"], "exports") if has_exp > 0 else (["TOTAL"], "total trade")


'''

# Add helper before get_state_overview (only once)
if "_pick_state_directions" not in content:
    content = content.replace(
        "def get_state_overview(",
        helper + "def get_state_overview(",
        1,
    )
    print("  ✓ Added _pick_state_directions helper")

# Replace direction filters with directions.in_(...)
import re

# Pattern A: direction == "EXPORT" inside state_overview/state_detail queries
# Insert export_dirs/import_dirs at top of get_state_overview body
overview_pat = re.compile(
    r'(def get_state_overview\(db: Session, fiscal_year: Optional\[int\] = None\) -> StateOverview:\n'
    r'    """[^"]*"""\n'
    r'    fy = fiscal_year or _current_fy\(\)\n'
    r'    fy_prev = fy - 1)',
    re.DOTALL,
)
inject = (
    r'\1\n\n    export_dirs, _ = _pick_state_directions(db, fy)\n'
    r'    import_dirs = ["IMPORT"] if export_dirs == ["EXPORT"] else ["TOTAL"]'
)
new_content, n = overview_pat.subn(inject, content)
if n > 0 and 'export_dirs, _ = _pick_state_directions' in new_content:
    content = new_content
    print("  ✓ Injected export_dirs/import_dirs in get_state_overview")

# Now replace direction filters within get_state_overview body
# Find function bounds
state_start = content.find("def get_state_overview(")
state_end = content.find("def get_state_detail(", state_start)
if state_start < 0 or state_end < 0:
    state_end = content.find("def get_sector_detail(", state_start)
overview_body = content[state_start:state_end]

new_body = overview_body
new_body = new_body.replace(
    'FactTradeMonthly.direction == "EXPORT",',
    'FactTradeMonthly.direction.in_(export_dirs),'
)
new_body = new_body.replace(
    'FactTradeMonthly.direction == "IMPORT",',
    'FactTradeMonthly.direction.in_(import_dirs),'
)
# Patch the inner total_state_value helper
new_body = new_body.replace(
    'def total_state_value(direction: str, year: int) -> float:',
    'def total_state_value(directions: list, year: int) -> float:'
)
new_body = new_body.replace(
    'FactTradeMonthly.direction == direction,',
    'FactTradeMonthly.direction.in_(directions),'
)
new_body = new_body.replace(
    'total_state_value("EXPORT", fy)',
    'total_state_value(export_dirs, fy)'
)
new_body = new_body.replace(
    'total_state_value("EXPORT", fy_prev)',
    'total_state_value(export_dirs, fy_prev)'
)
new_body = new_body.replace(
    'total_state_value("IMPORT", fy)',
    'total_state_value(import_dirs, fy)'
)
new_body = new_body.replace(
    'total_state_value("IMPORT", fy_prev)',
    'total_state_value(import_dirs, fy_prev)'
)

if new_body != overview_body:
    content = content[:state_start] + new_body + content[state_end:]
    print("  ✓ Replaced direction filters in get_state_overview")

# Now patch get_state_detail similarly
state_start = content.find("def get_state_detail(")
if state_start > 0:
    state_end = content.find("def get_sector_detail(", state_start)
    if state_end < 0:
        state_end = len(content)
    detail_body = content[state_start:state_end]

    # Inject directions selection after state lookup
    inject_after = '''    state = db.execute(
        select(DimState).where(DimState.state_code == state_code.upper())
    ).scalar_one_or_none()
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State {state_code} not found",
        )
'''
    inject_block = '''
    export_dirs, _ = _pick_state_directions(db, fy)
    import_dirs = ["IMPORT"] if export_dirs == ["EXPORT"] else ["TOTAL"]
'''
    if inject_after in detail_body and "export_dirs, _ = _pick_state_directions" not in detail_body:
        detail_body = detail_body.replace(inject_after, inject_after + inject_block)
        print("  ✓ Injected directions in get_state_detail")

    # Replace direction filters in detail
    detail_body = detail_body.replace(
        'def total_for_state(direction: str, year: int) -> float:',
        'def total_for_state(directions: list, year: int) -> float:'
    )
    detail_body = detail_body.replace(
        'FactTradeMonthly.direction == direction,',
        'FactTradeMonthly.direction.in_(directions),'
    )
    detail_body = detail_body.replace(
        'total_for_state("EXPORT", fy)', 'total_for_state(export_dirs, fy)'
    ).replace(
        'total_for_state("EXPORT", fy_prev)', 'total_for_state(export_dirs, fy_prev)'
    ).replace(
        'total_for_state("IMPORT", fy)', 'total_for_state(import_dirs, fy)'
    ).replace(
        'total_for_state("IMPORT", fy_prev)', 'total_for_state(import_dirs, fy_prev)'
    )

    # Patch top_products / top_partners inner functions
    detail_body = detail_body.replace(
        'def top_products(direction: str, n: int = 10)',
        'def top_products(directions: list, n: int = 10)'
    ).replace(
        'def top_partners(direction: str, n: int = 10)',
        'def top_partners(directions: list, n: int = 10)'
    ).replace(
        'FactTradeMonthly.direction == direction,',
        'FactTradeMonthly.direction.in_(directions),'
    )
    detail_body = detail_body.replace(
        'top_products("EXPORT")', 'top_products(export_dirs)'
    ).replace(
        'top_products("IMPORT")', 'top_products(import_dirs)'
    ).replace(
        'top_partners("EXPORT")', 'top_partners(export_dirs)'
    ).replace(
        'top_partners("IMPORT")', 'top_partners(import_dirs)'
    )

    content = content[:state_start] + detail_body + content[state_end:]
    print("  ✓ Patched get_state_detail")

# Patch yoy queries to use export_dirs+import_dirs
content = content.replace(
    'FactTradeMonthly.state_key.is_not(None),\n            DimDate.fiscal_year_in.between(fy - 4, fy),\n        )\n        .group_by(DimDate.fiscal_year_in, FactTradeMonthly.direction)',
    'FactTradeMonthly.state_key.is_not(None),\n            FactTradeMonthly.direction.in_(export_dirs + import_dirs),\n            DimDate.fiscal_year_in.between(fy - 4, fy),\n        )\n        .group_by(DimDate.fiscal_year_in, FactTradeMonthly.direction)'
)

src.write_text(content)
print("  ✓ File saved")
PYEOF

# Quick syntax check
python3 -c "import ast; ast.parse(open('backend/app/services/dashboards.py').read())" && echo "  ✓ Python syntax OK" || { echo "  ✗ Syntax error - aborting"; exit 1; }

echo ""

# ─────────────────────────────────────────────────────────────────
# 2. Rebuild BOTH containers so frontend picks up new TSX files
# ─────────────────────────────────────────────────────────────────
echo "[2/4] Rebuilding containers (this picks up new frontend code)"

docker compose down 2>&1 | tail -3
docker compose build 2>&1 | tail -5
docker compose up -d 2>&1 | tail -3

echo "  Waiting 30s for services..."
sleep 30

if curl -sf http://localhost:8001/api/v1/health > /dev/null; then
    echo "  ✓ Backend healthy"
else
    echo "  ✗ Backend not healthy"
    docker compose logs backend --tail=30
    exit 1
fi

if curl -sf http://localhost:3000 > /dev/null; then
    echo "  ✓ Frontend healthy"
else
    echo "  ✗ Frontend not responding"
    docker compose logs frontend --tail=20
    exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# 3. Smoke test
# ─────────────────────────────────────────────────────────────────
echo "[3/4] Smoke test new endpoint"

TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@india-trade.com","password":"admin123"}' | \
    python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

echo "  GET /dashboards/states?fiscal_year=2025"
curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states?fiscal_year=2025" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'    states returned: {len(d.get(\"states\", []))}')
print(f'    KPIs: {len(d.get(\"kpis\") or [])}')
print(f'    region_split: {len(d.get(\"region_split\") or [])}')
print(f'    yoy_trend: {len(d.get(\"yoy_trend\") or [])}')
if d.get('states'):
    top = d['states'][0]
    print(f'    top state: {top[\"label\"]} = \${top[\"value\"]/1e9:.2f}B')
"

echo ""
echo "  GET /dashboards/states/IN-MH?fiscal_year=2025  (Maharashtra drill-in)"
curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8001/api/v1/dashboards/states/IN-MH?fiscal_year=2025" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'    state_name: {d.get(\"state_name\")}')
print(f'    KPIs: {len(d.get(\"kpis\") or [])}')
print(f'    monthly_trend points: {len(d.get(\"monthly_trend\") or [])}')
print(f'    top_export_products: {len(d.get(\"top_export_products\") or [])}')
print(f'    top_export_destinations: {len(d.get(\"top_export_destinations\") or [])}')
"

echo ""

# ─────────────────────────────────────────────────────────────────
# 4. Done
# ─────────────────────────────────────────────────────────────────
echo "[4/4] Done"
echo ""
echo "✓ Hard-refresh your browser (Ctrl+Shift+R) on http://localhost:3000/dashboards/states"
echo "✓ You should now see: KPI cards, India map, region pie, 5-yr trend bar"
echo ""
echo "If page still looks old, try incognito window — Next.js may have cached the old bundle."
