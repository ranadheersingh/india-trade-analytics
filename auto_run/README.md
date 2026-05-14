# TRADESTAT Complete Automation 🚀

## ONE COMMAND DOES EVERYTHING

```bash
bash run_complete_automation.sh
```

That's it. **No manual steps. No intervention. Fully automated.**

---

## What This Does (7 Automated Steps)

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Verify Docker, backend, project structure       │
│ STEP 2: Install Python dependencies (selenium, etc)     │
│ STEP 3: Add 'region' column to fact_trade_monthly       │
│ STEP 4: Update pipeline code (regional support)         │
│ STEP 5: Rebuild backend container                       │
│ STEP 6: Auto-download ALL years × ALL regions × 2 dirs  │
│         - Detects ~50 regions automatically             │
│         - Downloads ~800+ files                         │
│         - Auto-converts XLSX → CSV                      │
│         - Auto-loads to database                        │
│ STEP 7: Show summary statistics                         │
└─────────────────────────────────────────────────────────┘
```

**Total time:** ~3 hours (or 10 minutes with `--no-regions`)

---

## Files in This Package

| File | Purpose |
|------|---------|
| **`run_complete_automation.sh`** | ⭐ Master script — runs everything |
| `tradestat_pipeline.py` | Updated pipeline with regional support |
| `tradestat_downloader.py` | Selenium auto-downloader |
| `sample_analytics_queries.sql` | Ready-to-use queries for geopolitical analysis |
| `README.md` | This file |

---

## Setup (One-Time)

```bash
cd ~/RANA/AATREE/exports/india-trade-analytics

# Create automation folder
mkdir -p auto_run

# Copy all files
cp /mnt/user-data/outputs/final_automation/*.py auto_run/
cp /mnt/user-data/outputs/final_automation/*.sh auto_run/
cp /mnt/user-data/outputs/final_automation/*.sql auto_run/

chmod +x auto_run/run_complete_automation.sh
chmod +x auto_run/tradestat_downloader.py
```

---

## Usage Options

### Option 1: Full Download (~3 hours)
```bash
bash auto_run/run_complete_automation.sh
```
Downloads everything: 8 years × 51 regions × 2 directions = 816 files

### Option 2: Resume After Interruption
```bash
bash auto_run/run_complete_automation.sh --resume
```
Skips already-downloaded files, picks up where it left off.

### Option 3: World Totals Only (~10 minutes)
```bash
bash auto_run/run_complete_automation.sh --no-regions
```
Just 16 files (8 years × 2 directions). No regional split.

### Option 4: Test Run (~30 minutes)
```bash
bash auto_run/run_complete_automation.sh --max-regions 5
```
Tests with first 5 regions only.

---

## What You'll Get

### Data in Database

```sql
-- Each row tagged with region:
SELECT region, direction, COUNT(*) 
FROM dw.fact_trade_monthly 
WHERE source_system='TRADESTAT' 
GROUP BY 1, 2;
```

```
   region        | direction | rows
-----------------+-----------+--------
 WORLD           | EXPORT    | 24,816
 WORLD           | IMPORT    | 24,816
 EUROPE          | EXPORT    | 24,816
 EUROPE          | IMPORT    | 24,816
 EU_COUNTRIES    | EXPORT    | 24,816
 EU_COUNTRIES    | IMPORT    | 24,816
 NORTH_AMERICA   | EXPORT    | 24,816
 NORTH_AMERICA   | IMPORT    | 24,816
 ASEAN           | EXPORT    | 24,816
 ASEAN           | IMPORT    | 24,816
 ...
 ─────────────────────────────────────
 TOTAL: ~2.5 million rows across ~50 regions
```

### File Structure

```
backend/app/data/tradestat/
├── export_2024-25.xlsx              # World totals
├── export_2024-25.csv
├── export_2024-25_europe.xlsx       # Region: Europe
├── export_2024-25_europe.csv
├── export_2024-25_eu-countries.xlsx
├── export_2024-25_eu-countries.csv
├── export_2024-25_asean.xlsx
├── export_2024-25_asean.csv
├── ... (~800 files total)
└── import_2017-18_oceania.csv
```

---

## Sample Geopolitical Analytics

After loading, run these (in `sample_analytics_queries.sql`):

### India's Top Trading Regions
```sql
SELECT region, ROUND(SUM(value_usd)/1e9, 2) as bn_usd
FROM dw.fact_trade_monthly 
WHERE source_system='TRADESTAT' 
  AND direction='EXPORT'
  AND date_key = 20240101
GROUP BY region 
ORDER BY 2 DESC LIMIT 10;
```

### Trade Balance Analysis
```sql
SELECT 
    region,
    SUM(CASE WHEN direction='EXPORT' THEN value_usd ELSE 0 END)/1e9 as exports_bn,
    SUM(CASE WHEN direction='IMPORT' THEN value_usd ELSE 0 END)/1e9 as imports_bn
FROM dw.fact_trade_monthly
WHERE source_system='TRADESTAT' AND date_key = 20240101
GROUP BY region;
```

### Geopolitical Concentration
```sql
-- "What % of exports go to top 5 regions?"
WITH ranked AS (
  SELECT region, SUM(value_usd) total,
         ROW_NUMBER() OVER (ORDER BY SUM(value_usd) DESC) rank
  FROM dw.fact_trade_monthly
  WHERE source_system='TRADESTAT' AND direction='EXPORT'
    AND region != 'WORLD' AND date_key = 20240101
  GROUP BY region
)
SELECT ROUND(100.0 * SUM(CASE WHEN rank <= 5 THEN total END) / SUM(total), 2) 
       as top5_concentration_pct
FROM ranked;
```

---

## Daily Auto-Refresh

Pipeline auto-runs at **5 AM UTC daily** (already configured).

To manually refresh:
```bash
bash auto_run/run_complete_automation.sh --resume
```

---

## Troubleshooting

### "ChromeDriver version mismatch"
```bash
pip install --upgrade --force-reinstall webdriver-manager
```

### "Backend not healthy"
```bash
docker compose down
docker compose up -d
sleep 30
```

### "Region selection fails"
Check what regions are available:
```bash
python3 auto_run/tradestat_downloader.py --max-regions 1 --no-trigger
# This will show the dropdown structure
```

### "Out of disk space"
The 800+ XLSX files are ~5MB each = ~4GB total.
After loading to DB, you can delete them:
```bash
rm backend/app/data/tradestat/*.xlsx  # Keep CSVs only
```

---

## Final Verification

After completion, run:
```bash
docker compose exec postgres psql -U biuser -d india_trade -c "
SELECT 
    region, 
    direction, 
    COUNT(*) as rows,
    ROUND(SUM(value_usd)::numeric/1e9, 2) as bn_usd
FROM dw.fact_trade_monthly 
WHERE source_system = 'TRADESTAT'
GROUP BY region, direction 
ORDER BY direction, bn_usd DESC NULLS LAST 
LIMIT 20;"
```

**Expected:** 50+ regions, billions of dollars in each, 8 years of data.

---

## Done! 🎉

Run the master script and walk away:

```bash
bash auto_run/run_complete_automation.sh
```

Come back in ~3 hours to a fully populated database with:
- ✅ All 8 years of TRADESTAT data
- ✅ All ~50 regions
- ✅ Both EXPORT and IMPORT
- ✅ Ready for geopolitical analysis
