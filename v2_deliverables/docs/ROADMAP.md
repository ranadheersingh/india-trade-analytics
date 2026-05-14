# India Trade Analytics — v2 Roadmap

## What's in *this* delivery

1. **Cleanup script** that deletes ~15 dead files (old tradestat iterations, scratch files, empty placeholders)
2. **Diagnostic SQL** to find why your dashboards show empty results (it's almost certainly a fiscal-year filter mismatch, not a code problem)
3. **State Performance v2** — a complete redesign of the page:
   - 4 KPI cards (state exports, imports, balance, count)
   - **India choropleth map** with click-to-drill
   - Top 10 states bar chart (also clickable)
   - 5-year YoY trend (export vs import)
   - Region split (NORTH/SOUTH/EAST/WEST/CENTRAL)
   - Rankings table with row-level click-to-drill
4. **NEW state detail page** at `/dashboards/states/[stateCode]`:
   - 4 state-specific KPIs
   - Monthly trend
   - 5-year history
   - Top export/import products (HS-2)
   - Top destination/source countries

What ships:

| Path | What |
|---|---|
| `backend/app/schemas/dashboards.py` | Full file replacement — adds `StateDetail`, enhances `StateOverview` |
| `backend/app/services/dashboards.py` | Replaces `get_state_overview`, adds `get_state_detail` |
| `backend/app/api/v1/dashboards.py` | Full file replacement — adds `/states/{state_code}` endpoint |
| `frontend/src/components/charts/IndiaMap.tsx` | NEW — choropleth component |
| `frontend/src/app/dashboards/states/page.tsx` | Full file replacement |
| `frontend/src/app/dashboards/states/[stateCode]/page.tsx` | NEW — drill-in page |
| `frontend/public/india-states.geojson` | Downloaded by install script |

## What's deliberately NOT in this delivery (and why)

You asked for "complete v2" with "more detailed reports for all screens." Doing that thoroughly would mean rewriting:

- Executive Overview (currently 7 charts) → ~15 charts with drill-downs
- Country Analysis page → similar treatment to State Performance with world map
- Sector Deep-dive → similar with HS hierarchy navigator
- Plus all corresponding backend endpoints

That's roughly another 8–10 files of substantial work (maybe 1,500 lines). If I had crammed it into a single response, I'd have cut corners somewhere — most likely on data accuracy, error handling, or testing — and you'd have spent days hunting bugs.

The **State Performance v2 here is meant to be a template**. Once you've got it working, the same pattern applies to the other dashboards:

- Backend: add detail endpoint with KPIs + trend + top-N tables
- Frontend: add map/chart + drill-in page + KPI cards
- Pattern is reusable

## Your immediate next steps (in order)

### 1. Run the diagnostic — find out why dashboards are empty

```bash
cd ~/RANA/AATREE/exports/india-trade-analytics
bash v2_deliverables/scripts/01_diagnose_and_cleanup.sh
```

The diagnostic prints which fiscal years actually have data. The default frontend filter is FY2026, but your data may end at FY2025 or earlier. If so:

- **Quick fix**: change the default in `frontend/src/app/dashboards/states/page.tsx` from `useState(2026)` to whatever year has data
- **Real fix**: load more recent data via NIRYAT/DGCIS/TRADESTAT pipelines

### 2. Install the v2 State Performance page

```bash
bash v2_deliverables/scripts/02_install_state_v2.sh
cd frontend && npm run dev
```

Visit `http://localhost:3000/dashboards/states`.

### 3. If TRADESTAT data still shows 0 rows

The fact_trade_monthly UNIQUE constraint now includes `region`, but you also need to verify:

```sql
SELECT region, direction, COUNT(*) 
FROM dw.fact_trade_monthly 
WHERE source_system='TRADESTAT' 
GROUP BY 1,2;
```

If that returns 0 rows even though 214 CSVs are on disk, run the pipeline again with logging enabled and check `docker compose logs backend | grep tradestat` for the actual error.

## Phase 2 — Country Analysis with world map

Same pattern as State Performance:

- Backend: enhance `get_country_detail` with more sections, add `get_country_overview` for global view
- Frontend: world map (`echarts.registerMap('world', ...)` — comes built-in to ECharts) + country drill-in already exists
- Add KPIs, trend, regional split (you already have this via `region_split_export` in executive)

Estimated: 1–2 days of focused work.

## Phase 3 — Sector Deep-dive enhancements

Currently you have HS-2 detail. Add:

- HS hierarchy navigator (HS-2 → HS-4 → HS-6 → HS-8)
- Treemap of HS-2 categories sized by export value
- Concentration metrics (HHI, top-5 share)
- Trend by HS-2 over 5 years

Estimated: 1–2 days.

## Phase 4 — Executive Overview polish

- Add commodity-level KPIs (top growing/declining)
- Add trade balance trend over 5 years
- Add country–region heatmap
- Date-range picker beyond fiscal year

Estimated: 1 day.

## Phase 5 — Cross-cutting improvements

- **Caching**: dashboards re-query DB on every request. Add Redis or simple in-memory TTL cache (10-min) for aggregations.
- **Export to PDF/Excel**: every dashboard should have an "Export report" button.
- **User permissions**: currently any logged-in user sees everything. Add role-based access (admin / analyst / viewer).
- **Alerts**: email digest when KPIs cross thresholds.
- **Mobile responsive**: most pages are desktop-only currently.

## Pending issues you mentioned earlier

- TRADESTAT region data loading (need to verify the model `region` field works after rebuild)
- Some pipelines showing "0 rows" in admin — diagnose with `01_diagnose_and_cleanup.sh`
- Auto-scheduling: already configured (cron in scheduler.py), the admin "Run now" button works

## Files removed by the cleanup script

These will be deleted (review before running):

```
tradestat_autoscraper.py        # Old selenium scraper, superseded
tradestat_final.py              # Older pipeline draft
test_eximp.py                   # Manual test script
setup_tradestat.sh              # One-time setup, no longer needed
fix_model_v2.sh                 # Already applied
Dockerfile.clean                # Use main Dockerfile instead

httpx                           # Empty file (typo'd output redirect)
naming                          # Empty file
resolving                       # Empty file

auto_run/tradestat.py
auto_run/tradestat_v4_auto.py
auto_run/tradestat_v5_auto.py
auto_run/tradestat_v6_full.py
auto_run/tradestat_v7_full.py
auto_run/tradestat_final_v8.py
auto_run/tradestat_full_auto.py
auto_run/tradestat_visible_auto.py
auto_run/tradestat_automation.py
auto_run/tradestat_pipeline.py
auto_run/auto_download_all.sh
auto_run/run_full_automation.sh
auto_run/convert_and_load.sh
auto_run/download_and_convert.py
```

Kept:
- `auto_run/tradestat_downloader.py` — current working downloader
- `auto_run/run_complete_automation.sh` — current orchestrator
- `auto_run/sample_analytics_queries.sql` — useful reference
- `auto_run/README.md`
