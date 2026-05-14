#!/bin/bash
###############################################################################
# TRADESTAT - COMPLETE AUTOMATION (ZERO MANUAL STEPS)
#
# This master script does EVERYTHING:
# 1. Migrates database (adds region column)
# 2. Updates pipeline code (regional support)
# 3. Rebuilds backend container
# 4. Auto-downloads ALL years × ALL regions × BOTH directions
# 5. Converts XLSX → CSV automatically
# 6. Loads everything into database
# 7. Shows comprehensive summary
#
# USAGE:
#   ./run_complete_automation.sh                    # Full run (~3 hours)
#   ./run_complete_automation.sh --resume           # Resume after interrupt
#   ./run_complete_automation.sh --no-regions       # World only (~10 min)
#   ./run_complete_automation.sh --max-regions 10   # Test with 10 regions
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Project root
PROJECT_DIR="${PROJECT_DIR:-$HOME/RANA/AATREE/exports/india-trade-analytics}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Parse arguments
RESUME_FLAG=""
REGIONS_FLAG=""
MAX_REGIONS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --resume) RESUME_FLAG="--resume"; shift ;;
        --no-regions) REGIONS_FLAG="--no-regions"; shift ;;
        --max-regions) MAX_REGIONS="--max-regions $2"; shift 2 ;;
        *) shift ;;
    esac
done

# Banner
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         TRADESTAT - COMPLETE AUTOMATION                          ║"
echo "║         All Years × All Regions × Both Directions                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}📁 Project: $PROJECT_DIR${NC}"
echo -e "${BLUE}📁 Scripts: $SCRIPT_DIR${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 1: Verify Prerequisites
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 1/7: Verifying prerequisites${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ! -d "backend/app/ingestion" ]; then
    echo -e "${RED}❌ Not in india-trade-analytics directory${NC}"
    exit 1
fi

# Check Docker
if ! docker compose ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker not running${NC}"
    exit 1
fi

# Check backend
if ! curl -sf http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend not running, starting...${NC}"
    docker compose up -d
    sleep 30
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 2: Install Dependencies
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 2/7: Installing dependencies${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

pip install --quiet --upgrade selenium openpyxl requests webdriver-manager 2>&1 | tail -3

echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 3: Run Database Migration
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 3/7: Adding 'region' column to database${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if migration already done
HAS_REGION=$(docker compose exec -T postgres psql -U biuser -d india_trade -tAc \
    "SELECT 1 FROM information_schema.columns WHERE table_schema='dw' AND table_name='fact_trade_monthly' AND column_name='region';" 2>/dev/null)

if [ "$HAS_REGION" = "1" ]; then
    echo -e "${GREEN}✅ Region column already exists${NC}"
else
    echo -e "${YELLOW}   Running migration...${NC}"
    
    docker compose exec -T postgres psql -U biuser -d india_trade << 'EOSQL'
ALTER TABLE dw.fact_trade_monthly ADD COLUMN IF NOT EXISTS region VARCHAR(50);
UPDATE dw.fact_trade_monthly SET region = 'WORLD' WHERE region IS NULL;
ALTER TABLE dw.fact_trade_monthly ALTER COLUMN region SET NOT NULL;
ALTER TABLE dw.fact_trade_monthly ALTER COLUMN region SET DEFAULT 'WORLD';
CREATE INDEX IF NOT EXISTS ix_dw_fact_trade_monthly_region ON dw.fact_trade_monthly(region);
CREATE INDEX IF NOT EXISTS ix_dw_fact_trade_monthly_source_region ON dw.fact_trade_monthly(source_system, region, direction);
EOSQL
    
    echo -e "${GREEN}✅ Migration complete${NC}"
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 4: Update Pipeline Code
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 4/7: Updating pipeline with regional support${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Backup current
cp backend/app/ingestion/tradestat.py backend/app/ingestion/tradestat.py.bak.$(date +%s) 2>/dev/null || true

# Copy new pipeline
if [ -f "$SCRIPT_DIR/tradestat_pipeline.py" ]; then
    cp "$SCRIPT_DIR/tradestat_pipeline.py" backend/app/ingestion/tradestat.py
    echo -e "${GREEN}✅ Pipeline updated${NC}"
else
    echo -e "${RED}❌ tradestat_pipeline.py not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Verify region support
if grep -q "region" backend/app/ingestion/tradestat.py && \
   grep -q "USD_MULTIPLIER" backend/app/ingestion/tradestat.py; then
    echo -e "${GREEN}✅ Pipeline has regional + value fix${NC}"
else
    echo -e "${RED}❌ Pipeline verification failed${NC}"
    exit 1
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 5: Rebuild Backend
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 5/7: Rebuilding backend container${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

docker compose down 2>&1 | tail -2
docker rmi india-trade-analytics-backend:latest 2>/dev/null || true
docker compose build --no-cache backend 2>&1 | tail -5
docker compose up -d backend 2>&1 | tail -2

echo -e "${YELLOW}   Waiting 30s for backend...${NC}"
sleep 30

if curl -sf http://localhost:8001/api/v1/health > /dev/null; then
    echo -e "${GREEN}✅ Backend healthy${NC}"
else
    echo -e "${RED}❌ Backend not responding${NC}"
    docker compose logs backend | tail -20
    exit 1
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 6: Run Auto-Downloader
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 6/7: Auto-downloading data from TRADESTAT${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ! -f "$SCRIPT_DIR/tradestat_downloader.py" ]; then
    echo -e "${RED}❌ tradestat_downloader.py not found${NC}"
    exit 1
fi

# Run downloader
python3 "$SCRIPT_DIR/tradestat_downloader.py" $RESUME_FLAG $REGIONS_FLAG $MAX_REGIONS

echo ""

# ═══════════════════════════════════════════════════════════════════
# STEP 7: Final Summary
# ═══════════════════════════════════════════════════════════════════
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 7/7: Final verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "📊 TRADESTAT data by region (top 20):"
docker compose exec -T postgres psql -U biuser -d india_trade << 'EOSQL'
SELECT 
    region,
    direction,
    COUNT(*) as rows,
    COUNT(DISTINCT date_key) as years,
    ROUND(SUM(value_usd)::numeric/1e9, 2) as billion_usd
FROM dw.fact_trade_monthly 
WHERE source_system = 'TRADESTAT'
GROUP BY region, direction 
ORDER BY direction, billion_usd DESC NULLS LAST
LIMIT 20;
EOSQL

echo ""
echo "📊 All sources comparison:"
docker compose exec -T postgres psql -U biuser -d india_trade << 'EOSQL'
SELECT 
    source_system,
    direction,
    COUNT(DISTINCT region) as regions,
    COUNT(*) as rows,
    ROUND(SUM(value_usd)::numeric/1e9, 1) as bn_usd
FROM dw.fact_trade_monthly
GROUP BY 1, 2
ORDER BY 1, 2;
EOSQL

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo -e "║         ${GREEN}🎉 AUTOMATION COMPLETE!${NC}                                   ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${YELLOW}📌 Next time you want to refresh:${NC}"
echo -e "   ${YELLOW}bash $SCRIPT_DIR/run_complete_automation.sh --resume${NC}"
echo ""
echo -e "${YELLOW}📌 To run analytics queries:${NC}"
echo -e "   ${YELLOW}docker compose exec postgres psql -U biuser -d india_trade${NC}"
echo ""
echo -e "${YELLOW}📌 Sample query - India exports by region:${NC}"
cat << 'EOF'
   SELECT region, ROUND(SUM(value_usd)/1e9, 2) as bn_usd
   FROM dw.fact_trade_monthly 
   WHERE source_system='TRADESTAT' AND direction='EXPORT'
   GROUP BY region ORDER BY 2 DESC LIMIT 10;
EOF
echo ""
