# NIRYAT Phase 2 Pipeline Integration Guide

## Step 1: Copy Pipeline File

Copy `niryat_phase2.py` to your backend:

```bash
cp /mnt/user-data/outputs/niryat_phase2.py backend/app/ingestion/niryat_phase2.py
```

Or create it directly on your server:

```bash
# On production server
cat > ~/india-trade-analytics/backend/app/ingestion/niryat_phase2.py << 'PYEOF'
[Copy the entire niryat_phase2.py content here]
PYEOF
```

---

## Step 2: Update ingestion/__init__.py

Add the NIRYAT pipeline to the pipeline registry:

```python
# File: backend/app/ingestion/__init__.py

from app.ingestion.niryat_phase2 import NiryatPhase2Pipeline

PIPELINES = {
    "dgcis": DgcisPipeline,
    "comtrade": ComtradePipeline,
    "tradestat": TradestatPipeline,
    "oec": OecPipeline,
    "niryat": NiryatPipeline,
    "niryat_phase2": NiryatPhase2Pipeline,  # ← ADD THIS LINE
    "fx_rates": FxRatesPipeline,
    "world_bank": WorldBankPipeline,
}

def get_pipeline(name: str) -> Pipeline:
    """Get pipeline by name"""
    if name not in PIPELINES:
        raise ValueError(f"Unknown pipeline: {name}")
    return PIPELINES[name]()
```

---

## Step 3: Update scheduler.py (Optional)

Add scheduled job for NIRYAT:

```python
# File: backend/app/scheduler.py

# In the scheduler setup:
scheduler.add_job(
    _make_runner("niryat_phase2"),
    "cron",
    hour=3,
    minute=30,  # Run at 3:30 AM daily
    id="niryat_phase2",
    name="NIRYAT Phase 2 - Transaction-level exports"
)
```

---

## Step 4: Run the Pipeline

### Option A: Manual Run (Testing)

```bash
# SSH to production server
ssh root@your-server

cd ~/india-trade-analytics

# Run with sample data (demo mode)
docker compose exec trade_backend python3 << 'EOF'
import asyncio
from app.ingestion import get_pipeline

async def main():
    pipeline = get_pipeline('niryat_phase2')
    result = await pipeline.run()
    print(f"Status: {result.status}")
    print(f"Rows loaded: {result.rows_loaded}")

asyncio.run(main())
EOF
```

### Option B: Backfill Mode (5 years of history)

```bash
docker compose exec -e NIRYAT_MODE=backfill trade_backend python3 << 'EOF'
import asyncio
from app.ingestion import get_pipeline

async def main():
    pipeline = get_pipeline('niryat_phase2')
    result = await pipeline.run()
    print(f"Status: {result.status}")
    print(f"Transactions loaded: {result.rows_loaded}")

asyncio.run(main())
EOF
```

### Option C: Incremental Mode (Last 30 days)

```bash
docker compose exec trade_backend python3 << 'EOF'
import asyncio
from app.ingestion import get_pipeline

async def main():
    pipeline = get_pipeline('niryat_phase2')
    result = await pipeline.run()
    print(f"Status: {result.status}")
    print(f"Rows loaded: {result.rows_loaded}")

asyncio.run(main())
EOF
```

---

## Step 5: Verify Data Loaded

```bash
docker compose exec postgres psql -U biuser -d india_trade -c "
SELECT 
    COUNT(*) as total_transactions,
    COUNT(DISTINCT exporter_key) as unique_exporters,
    SUM(total_value_usd) as total_value,
    MIN(export_date) as earliest_export,
    MAX(export_date) as latest_export
FROM fact_export_transactions;
"
```

Expected output (for sample data):
```
 total_transactions | unique_exporters | total_value | earliest_export | latest_export
────────────────────┼──────────────────┼─────────────┼─────────────────┼──────────────
        300         |        5         | 150000000   | 2021-05-09      | 2026-05-09
```

---

## Step 6: Query the Data

### Get all transactions:

```bash
docker compose exec postgres psql -U biuser -d india_trade -c "
SELECT 
    t.transaction_id,
    e.exporter_name,
    c.country_name,
    t.product_hs_code,
    t.quantity,
    t.unit_of_measure,
    t.total_value_usd
FROM fact_export_transactions t
JOIN dim_exporter e ON t.exporter_key = e.exporter_key
JOIN dim_country c ON t.destination_country_key = c.country_key
LIMIT 10;
"
```

### Get transactions by exporter:

```bash
docker compose exec postgres psql -U biuser -d india_trade -c "
SELECT 
    e.exporter_name,
    COUNT(*) as shipments,
    SUM(t.total_value_usd) as total_value,
    COUNT(DISTINCT t.destination_country_key) as countries
FROM fact_export_transactions t
JOIN dim_exporter e ON t.exporter_key = e.exporter_key
GROUP BY e.exporter_key, e.exporter_name
ORDER BY total_value DESC;
"
```

### Get transactions by destination:

```bash
docker compose exec postgres psql -U biuser -d india_trade -c "
SELECT 
    c.country_name,
    COUNT(*) as shipments,
    SUM(t.total_value_usd) as total_value,
    AVG(t.total_value_usd) as avg_shipment_value
FROM fact_export_transactions t
JOIN dim_country c ON t.destination_country_key = c.country_key
GROUP BY c.country_key, c.country_name
ORDER BY total_value DESC
LIMIT 10;
"
```

---

## Configuration

### Environment Variables

Add to `.env` or `docker-compose.yml`:

```bash
# NIRYAT API Configuration
NIRYAT_API_BASE=https://niryat.commerce.gov.in/api/v1
NIRYAT_API_KEY=your-api-key-here
NIRYAT_MODE=incremental  # or "backfill"

# Logging
LOG_LEVEL=INFO
```

### For Real NIRYAT API

When you get credentials from Government of India:

```bash
NIRYAT_API_BASE=https://niryat.commerce.gov.in/api/v1
NIRYAT_API_KEY=your-actual-api-key
```

### For Testing (Current Mode)

The pipeline uses sample data generation if the real API is unavailable.

---

## Pipeline Features

### ✅ What It Does

1. **Fetches Data**
   - From NIRYAT API (if available)
   - Falls back to sample data (for testing)
   - Supports backfill (5 years) and incremental (30 days) modes

2. **Transforms Data**
   - Validates all records
   - Converts data types
   - Calculates fiscal year
   - Handles missing fields gracefully

3. **Loads Data**
   - Creates/updates exporters
   - Links to countries
   - Inserts transactions
   - Handles duplicates (upsert)

4. **Verifies Load**
   - Counts total records
   - Checks data integrity
   - Logs results

### ✅ Error Handling

- Invalid records are skipped with warnings
- Missing countries are logged
- Duplicates are updated (not re-inserted)
- Database errors roll back transaction

### ✅ Performance

- Batch commits every 500 records
- Indexed queries for fast lookups
- Handles 1000s of records efficiently

---

## Expected Results (Sample Data)

Running the pipeline with sample data loads:

```
300 Export Transactions
├─ 5 different exporters
├─ 5 destination countries
├─ 5 HS product codes
├─ 4 modes of transport (Sea, Air, Rail, Road)
├─ 5-month date range (for demo)
└─ Total value: $150M+
```

---

## Troubleshooting

### Pipeline doesn't run

```bash
# Check logs
docker logs trade_backend --tail=100 | grep -i niryat

# Check if pipeline is registered
docker compose exec trade_backend python3 -c "
from app.ingestion import get_pipeline
try:
    p = get_pipeline('niryat_phase2')
    print('✓ Pipeline registered:', p.name)
except Exception as e:
    print('✗ Error:', e)
"
```

### No data inserted

```bash
# Check if countries exist (they must for foreign key)
docker compose exec postgres psql -U biuser -d india_trade -c "
SELECT COUNT(*) as countries FROM dim_country;
"

# Must return > 0
```

### API connection errors

```bash
# Check API connectivity
docker compose exec trade_backend python3 << 'EOF'
import httpx

async def test():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get("https://niryat.commerce.gov.in/api/v1/health")
            print(f"Status: {response.status_code}")
        except Exception as e:
            print(f"Error: {e}")

import asyncio
asyncio.run(test())
EOF
```

---

## Next Steps After Running Pipeline

1. **Build APIs** to query transaction data
2. **Create Dashboards** to visualize transactions
3. **Add Real NIRYAT Credentials** when available
4. **Implement Phase 3** (Port & Transport analytics)
5. **Implement Phase 4** (Real-time tracking)

---

## Quick Start Command

```bash
# One-command to copy, integrate, and run:
cd ~/india-trade-analytics/backend && \
cp /mnt/user-data/outputs/niryat_phase2.py app/ingestion/ && \
docker compose exec trade_backend python3 << 'EOF'
import asyncio
from app.ingestion import get_pipeline

async def main():
    pipeline = get_pipeline('niryat_phase2')
    result = await pipeline.run()
    if result.status == "success":
        print(f"\n✅ SUCCESS: Loaded {result.rows_loaded} transactions")
    else:
        print(f"\n❌ FAILED: {result.error_message}")

asyncio.run(main())
EOF
```
