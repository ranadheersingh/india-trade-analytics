# States Dashboard Not Loading — Quick Action Plan

## The Problem (In 30 Seconds)

Your States dashboard at `http://localhost:3000/dashboards/states` is blank or not loading.

**Root cause**: One of three issues:
1. Database has no state-level trade data
2. Docker containers running old code
3. Frontend cached old build

**Good news**: Your code architecture is correct. No patches needed.

---

## Quick Fix (5 Minutes)

### Step 1: Rebuild Docker Containers
```bash
cd /path/to/india-trade-analytics
docker compose down
docker compose up -d --build
sleep 30
```

### Step 2: Hard Refresh Browser
- Windows/Linux: **Ctrl+Shift+R** on `http://localhost:3000/dashboards/states`
- Mac: **Cmd+Shift+R**
- Or try an Incognito/Private window

### Step 3: Check Result
- ✅ **If you see KPI cards, map, and charts**: Problem solved!
- ❌ **If still blank**: Go to "Detailed Diagnostics" below

---

## Detailed Diagnostics (10-15 Minutes)

### Run the Diagnostic Script
```bash
bash /mnt/user-data/outputs/quick-fix.sh
```

This will:
1. Check database for state data
2. Verify API endpoint returns data
3. Test authentication
4. Give you specific recommendations

**Expected output**:
```
✓ PostgreSQL healthy
✓ Backend healthy
✓ Frontend healthy
Database state rows: 12500
Available directions: ['EXPORT', 'IMPORT']
States returned: 28
KPIs: 4
✓ Code logic working
✓ API endpoint responding
Top state: Maharashtra: $45.23B
```

### If Database Has No State Data

```bash
# Option A: Load DGCIS state-level data
cd backend
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline
# This takes 3-5 minutes and loads 5 years of monthly data

# Then check:
PGPASSWORD=changeme psql -U trade -d india_trade -h localhost \
  -c "SELECT COUNT(*) FROM fact_trade_monthly WHERE state_key IS NOT NULL;"
# Should now show > 0

# Then restart dashboard script again
bash /mnt/user-data/outputs/quick-fix.sh
```

### If API Returns Data But Frontend Blank

This is a Next.js caching issue:

**Option 1**: Hard refresh (Ctrl+Shift+R)

**Option 2**: Clear Next.js cache
```bash
rm -rf frontend/.next
docker compose restart frontend
sleep 10
# Then hard refresh browser
```

**Option 3**: Try incognito/private window
- No cache = easiest test

---

## Verification Queries

Run these in psql to understand your data:

```bash
# Connect to DB
psql -U trade -d india_trade -h localhost

# Then paste any of these:
```

### Check State Data Exists
```sql
SELECT COUNT(*) as state_rows FROM fact_trade_monthly 
WHERE state_key IS NOT NULL;
```
✅ Should be > 0

### Check Directions Available
```sql
SELECT DISTINCT direction FROM fact_trade_monthly 
WHERE state_key IS NOT NULL ORDER BY direction;
```
✅ Should show EXPORT, IMPORT, or TOTAL

### Check Current Year Data
```sql
SELECT COUNT(*) FROM fact_trade_monthly ftm
JOIN dim_date dd ON ftm.date_key = dd.date_key
WHERE dd.fiscal_year_in = 2025 AND ftm.state_key IS NOT NULL;
```
✅ Should be > 0 for FY2025

---

## Comprehensive Fix Script (Automated)

For everything at once:

```bash
bash /mnt/user-data/outputs/fix-states-dashboard.sh
```

This does:
1. ✓ Restart containers (clean build)
2. ✓ Validate database
3. ✓ Test all API endpoints
4. ✓ Verify state detail endpoint
5. ✓ Give clear next steps

---

## If Still Not Working

Collect this information:

1. **Output of quick-fix.sh**
   ```bash
   bash /mnt/user-data/outputs/quick-fix.sh > diagnostic.txt 2>&1
   ```

2. **Backend logs** (last 50 lines)
   ```bash
   docker logs trade_backend --tail=50 > backend-logs.txt
   ```

3. **Browser console errors** (F12 → Console tab)
   - Screenshot or copy/paste

4. **API response** (with token)
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"email":"admin@india-trade.com","password":"admin123"}' | \
     jq -r .access_token)
   
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8001/api/v1/dashboards/states?fiscal_year=2025" | \
     jq . > api-response.json
   ```

Share these files + this action plan, and I can provide specific fixes.

---

## What Should Be Working

Once fixed, the States Dashboard shows:

### Top Section
- 📊 4 KPI cards
  - State Exports (or "State trade value" if TOTAL only)
  - State Imports (or "N/A" if TOTAL only)
  - Trade Balance
  - YoY % change

### Middle Section
- 🗺️ Interactive India choropleth map (clickable states)
- 📊 Top 10 states horizontal bar chart (clickable)

### Bottom Section
- 📈 5-year trend chart (exports/imports/total by FY)
- 🥧 Region split pie chart (if TRADESTAT data loaded)
- 📋 State rankings table (sortable, clickable)

### Click to Drill
- Click state in map → detail page
- Click bar in chart → detail page
- Click row in table → detail page

---

## Files in This Bundle

| File | Purpose |
|------|---------|
| `STATES_DASHBOARD_FIX_GUIDE.md` | Complete technical guide (30 min read) |
| `STATES_DASHBOARD_ARCHITECTURE.md` | Deep dive on data architecture & design |
| `DATABASE_DIAGNOSTICS.sql` | SQL queries to check data state |
| `quick-fix.sh` | 5-minute diagnostic script |
| `fix-states-dashboard.sh` | Comprehensive automated fix (15 min) |
| `QUICK_ACTION_PLAN.md` | This file — start here! |

---

## Next Steps

1. **First**: Run `quick-fix.sh` and see what it says
2. **If OK**: Hard refresh browser → problem solved
3. **If not OK**: Run `fix-states-dashboard.sh` → full automated fix
4. **If still not OK**: Reference `STATES_DASHBOARD_FIX_GUIDE.md` for detailed troubleshooting

---

## TL;DR

```bash
# 1. Restart containers
docker compose down
docker compose up -d --build
sleep 30

# 2. Hard refresh browser
# Ctrl+Shift+R on http://localhost:3000/dashboards/states

# 3. If still blank, run diagnostic
bash /mnt/user-data/outputs/quick-fix.sh

# 4. If no state data, load it
cd backend
DGCIS_MODE=backfill python -m app.pipelines.dgcis_pipeline

# 5. Restart and refresh again
```

---

**Still stuck?** Open `STATES_DASHBOARD_FIX_GUIDE.md` and follow Section 3.
