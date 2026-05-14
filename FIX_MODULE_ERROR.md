# ✅ Fix: ModuleNotFoundError - Running DGCIS Pipeline

The error you got:
```
/usr/bin/python: Error while finding module specification for 'app.pipelines.dgcis_pipeline'
(ModuleNotFoundError: No module named 'app.pipelines')
```

**Reason**: The module path was wrong. It should be `app.ingestion`, not `app.pipelines`.

---

## ✅ Solution: Use the Provided Script

I've created a proper wrapper script. Run this instead:

```bash
# From the project root
cd ~/RANA/AATREE/exports/india-trade-analytics
bash run_dgcis_pipeline.sh --backfill
```

**This will**:
1. ✓ Check Docker is running
2. ✓ Verify database is ready
3. ✓ Run DGCIS pipeline in backfill mode (5-year history)
4. ✓ Verify data loaded
5. ✓ Tell you what to do next

**Expected output**:
```
╔════════════════════════════════════════════════════════════════╗
║  DGCIS Pipeline Runner                                         ║
║  Mode: backfill (loads state-level trade data)                 ║
╚════════════════════════════════════════════════════════════════╝

[1/3] Checking database connectivity...
✓ Database connected

[2/3] Running DGCIS pipeline (Mode: backfill)...
This may take 5-15 minutes depending on your connection...

Loading DGCIS pipeline (backfill mode)...
✓ DGCIS pipeline complete!

[3/3] Verifying data loaded...
State-level rows in database: 1680

╔════════════════════════════════════════════════════════════════╗
║  ✓ SUCCESS                                                     ║
║  DGCIS data loaded: 1680 state-level trade records             ║
╚════════════════════════════════════════════════════════════════╝

Next steps:
  1. Run: bash fix-states-dashboard.sh
  2. Hard refresh: http://localhost:3000/dashboards/states
```

---

## 🚀 Quick Commands

```bash
# Load state data (one command)
bash run_dgcis_pipeline.sh --backfill

# Then verify everything works
bash fix-states-dashboard.sh

# Then hard refresh browser
# http://localhost:3000/dashboards/states
# Press: Ctrl+Shift+R
```

---

## ⏱️ Timeline

| Step | Command | Time | Status |
|------|---------|------|--------|
| 1️⃣ Load data | `bash run_dgcis_pipeline.sh --backfill` | 5-15 min | ⏳ Running |
| 2️⃣ Verify | `bash fix-states-dashboard.sh` | 1 min | ⏸️ Waiting |
| 3️⃣ View | Hard refresh browser | instant | 🔜 Next |

---

## Alternative: If Docker Exec Fails

If the Docker version doesn't support the command above, use the Python script directly:

```bash
cd ~/RANA/AATREE/exports/india-trade-analytics/backend
DGCIS_MODE=backfill python3 run_dgcis_pipeline.py
```

(But the bash script is recommended as it handles Docker setup automatically)

---

**👉 Run this now**:
```bash
bash run_dgcis_pipeline.sh --backfill
```

It will download 5 years of state-level trade data. Takes 5-15 minutes.

Let me know when it completes! 🚀
