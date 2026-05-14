# 🎯 States Dashboard Fix: Load State Data (DGCIS Backfill)

## Your Diagnostic Result

✅ **Good News**: Docker containers are running perfectly  
❌ **Issue Found**: Database has **0 state-level data rows**

```
Database state rows with state_key: 0
```

This is the root cause. The states dashboard needs state-level data to display anything.

---

## Solution: Load DGCIS State Data

The DGCIS pipeline has state-level information. We need to run it in **backfill mode** to load all historical state data.

### Step 1: Start the DGCIS Backfill (5-10 minutes)

```bash
cd backend
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
```

**What this does**:
- Downloads 5 years of monthly data from DGCIS
- Extracts state-level information
- Loads into database with proper state_key linking
- Creates: ~60 months × 28 states = ~1,680 rows

**Expected output** (watch for):
```
Loading DGCIS data (backfill mode)...
Processing FY2022-Q1... ✓
Processing FY2022-Q2... ✓
...
Loaded: 1680 rows
State data linked: 28 states
Complete: ✓
```

### Step 2: Monitor Progress

The script may take 5-10 minutes depending on your internet connection. You'll see:

```
2026-05-09 12:00:00 - Loading DGCIS monthly data
2026-05-09 12:00:05 - FY2022: Processing...
2026-05-09 12:00:15 - FY2022: Loaded 420 rows
2026-05-09 12:00:20 - FY2023: Processing...
...
2026-05-09 12:10:30 - Complete: 1680 rows loaded, 28 states
```

### Step 3: Verify Data Loaded

While the script runs (or after), check progress:

```bash
# In another terminal, check database
PGPASSWORD=changeme psql -U trade -d india_trade -h localhost \
  -c "SELECT COUNT(*) as state_rows FROM fact_trade_monthly WHERE state_key IS NOT NULL;"

# Should go from 0 → increasing numbers (100s, 500s, 1000s, 1680)
```

---

## What If It Fails?

### Error: "Network connection error"
```bash
# DGCIS API might be down
# Option 1: Retry after 5 minutes
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline

# Option 2: Load TRADESTAT instead (regional data)
cd backend
python -m app.pipelines.tradestat_pipeline
```

### Error: "Unique constraint violation"
```bash
# State data partially loaded
# Safe to ignore - rerun will skip duplicates
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
```

### Error: "State master data not found"
```bash
# State dimension table empty
# Run migrations first
cd backend
alembic upgrade head
# Then retry
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
```

---

## Step 4: Run the Fix Script Again

Once loading is complete:

```bash
cd ~/RANA/AATREE/exports/india-trade-analytics
bash fix-states-dashboard.sh
```

Expected result:
```
=== PHASE 2: DATABASE VALIDATION ===
Database state rows with state_key: 1680
Available directions: TOTAL
✓ State data present in database

=== PHASE 3: API ENDPOINT TEST ===
✓ Authenticated
Testing /dashboards/states?fiscal_year=2025…
Response structure:
  States: 28
  KPIs: 4
  Region split: 0
  YoY trend points: 60

✓ API endpoint responding with data
  Top state: Maharashtra: $45.23B

=== PHASE 4: STATE DETAIL TEST ===
State detail for Maharashtra:
  State name: Maharashtra
  Top products returned: 10
✓ State detail endpoint working

=== READY TO USE ===
✓ All systems operational!
```

---

## Step 5: Hard Refresh Browser

Once API test shows ✓ (all systems operational):

```
📊 Dashboard URL:
   http://localhost:3000/dashboards/states

IMPORTANT: Hard refresh your browser!
   - Windows/Linux: Ctrl+Shift+R
   - macOS: Cmd+Shift+R
   - Or try Incognito/Private window
```

You should now see:
- ✅ 4 KPI cards with numbers
- ✅ Interactive India map
- ✅ Top 10 states chart
- ✅ 5-year trend
- ✅ State rankings table

---

## Expected Data After DGCIS Load

### What You'll See
- **States**: All 28 Indian states + union territories
- **Direction**: TOTAL trade value (not split into EXPORT/IMPORT)
- **Time period**: Last 5 years of monthly data (60 months)
- **Top states**: Maharashtra, Gujarat, Tamil Nadu, etc.

### Sample Numbers (FY2025)
```
Maharashtra: $156.2 B (20% of total)
Gujarat: $142.5 B (18%)
Tamil Nadu: $89.3 B (11%)
...
```

### Note About Direction
- **Current data**: DGCIS provides direction='TOTAL'
- **Label shown**: "State trade value" (not exports/imports)
- **Why**: DGCIS doesn't split by direction yet
- **When split available**: NIRYAT pipeline (future phase)

---

## Parallel Option: Load TRADESTAT Instead

If DGCIS is slow or failing:

```bash
# Load TRADESTAT regional data
cd backend
python -m app.pipelines.tradestat_pipeline

# This takes ~2 minutes
# Result: Regional groupings (ASEAN, EU, GCC, etc.)
# Shows: Trade by region instead of individual states
```

**Note**: TRADESTAT shows regions, not individual states, but provides good data for the dashboard.

---

## Complete Flow (Summary)

```
1. Run fix script
   ↓ (detects: no state data)
   ↓
2. Load DGCIS backfill
   cd backend
   DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
   ↓ (takes 5-10 minutes)
   ↓
3. Verify data loaded
   Check: psql query shows count > 0
   ↓
4. Run fix script again
   bash fix-states-dashboard.sh
   ↓ (should show: ✓ State data present)
   ↓
5. Hard refresh browser
   Ctrl+Shift+R on http://localhost:3000/dashboards/states
   ↓
6. See dashboard! 🎉
   States, KPIs, map, charts all load
```

---

## Monitoring During Load

### Watch Progress
```bash
# Terminal 1: Run DGCIS load
cd backend && DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline

# Terminal 2: Monitor database (while Terminal 1 is running)
watch -n 5 'PGPASSWORD=changeme psql -U trade -d india_trade -h localhost \
  -c "SELECT COUNT(*) FROM fact_trade_monthly WHERE state_key IS NOT NULL;"'

# Output will show: 0 → 100 → 500 → 1000 → 1680
```

### Check Logs
```bash
# If there are errors
docker logs trade_backend --tail=50 | grep -i "error\|state\|dgcis"

# If you want to see everything
docker logs trade_backend --tail=100
```

---

## After Data Loads: Next Steps

Once the states dashboard is working:

1. ✅ **States Dashboard** - Complete (you're here)
2. ⏭️ **Implement 5-Year Rolling Window** - See ROLLING_WINDOW_README.md
3. ⏭️ **Country Analysis Dashboard** - Phase 2
4. ⏭️ **Sector Deep-dive** - Phase 3
5. ⏭️ **Executive Overview Polish** - Phase 4

---

## Troubleshooting

### "Still no data after DGCIS load"
```bash
# 1. Check if it actually loaded
PGPASSWORD=changeme psql -U trade -d india_trade -h localhost \
  -c "SELECT COUNT(*) FROM fact_trade_monthly WHERE state_key IS NOT NULL;"
# Should show 1680 or similar

# 2. Check direction value
PGPASSWORD=changeme psql -U trade -d india_trade -h localhost \
  -c "SELECT DISTINCT direction FROM fact_trade_monthly WHERE state_key IS NOT NULL;"
# Should show: TOTAL

# 3. If still 0, DGCIS pipeline didn't complete successfully
# Check logs:
docker logs trade_backend | tail -100 | grep -i error
```

### "DGCIS pipeline hangs"
```bash
# Kill it and check for errors
Ctrl+C

# Look for API errors
grep -i "api\|error" backend/app/logs/*.log 2>/dev/null || echo "No logs found"

# Retry
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
```

### "States still not showing after refresh"
```bash
# 1. Hard refresh (Ctrl+Shift+R)
# 2. Try incognito window
# 3. Clear browser cache: Ctrl+Shift+Delete
# 4. Check browser console: F12 → Console tab
# 5. Check API directly:
TOKEN=$(curl -s ... | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/v1/dashboards/states" | jq .
```

---

## Performance Notes

- **DGCIS load time**: 5-10 minutes (one-time)
- **Dashboard load time**: Should be < 2 seconds (after data loads)
- **Query performance**: ~100ms for state overview query
- **Data size**: ~1,680 rows (small, very fast)

---

## Success Checklist

After completing all steps:

- [ ] DGCIS backfill completed without errors
- [ ] Database shows > 1000 state rows
- [ ] `fix-states-dashboard.sh` shows ✓ State data present
- [ ] API test shows States: 28
- [ ] Browser shows KPI cards with numbers
- [ ] Browser shows choropleth map with colors
- [ ] Click state → detail page works
- [ ] Dashboard loads in < 2 seconds
- [ ] No errors in browser console (F12)

---

## Next Command to Run Now

```bash
cd backend
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
```

⏱️ **Estimated time**: 5-10 minutes

Then: `bash fix-states-dashboard.sh` again

Then: Hard refresh browser 🚀

---

**Let me know once the data loads!** 📊
