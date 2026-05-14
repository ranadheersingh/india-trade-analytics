# 🔧 Phase 2-4 Deployment - QUICK FIX

## Issue: Backend restarting after deployment

The deployment script appended code to `main.py` and `__init__.py` which caused issues. Here's how to fix it:

---

## Quick Fix (5 minutes)

### Step 1: Replace main.py

```bash
# Use the CORRECT version we just created
cp main_py_CORRECT.py ~/india-trade-analytics/backend/app/main.py
```

### Step 2: Replace ingestion __init__.py

```bash
# Use the CORRECT version we just created
cp ingestion_init_CORRECT.py ~/india-trade-analytics/backend/app/ingestion/__init__.py
```

### Step 3: Rebuild and Restart

```bash
cd ~/india-trade-analytics

# Stop everything
docker compose down

# Rebuild with correct code
docker compose up -d --build

# Wait for health checks
sleep 45

# Verify
docker compose ps
```

### Step 4: Verify Backend is Running

```bash
# Should show "Up" and "healthy"
docker compose ps | grep trade_backend

# Check if API is responding (wait a few more seconds if needed)
sleep 10
curl http://localhost:8001/api/v1/analytics/summary
```

---

## If Still Not Working

### Check Backend Logs

```bash
docker logs trade_backend --tail=100
```

Look for:
- `ImportError` → Missing module
- `SyntaxError` → Code syntax issue
- `ModuleNotFoundError` → Import path issue

### Reset Everything

```bash
cd ~/india-trade-analytics

# Remove containers and volumes
docker compose down -v

# Verify no containers running
docker ps

# Rebuild fresh
docker compose up -d --build

# Wait longer this time
sleep 60

# Check status
docker compose ps
```

---

## Files You Need

Download and use these CORRECTED files from `/mnt/user-data/outputs/`:

1. **main_py_CORRECT.py** → Copy to `backend/app/main.py`
2. **ingestion_init_CORRECT.py** → Copy to `backend/app/ingestion/__init__.py`
3. **transaction_apis.py** → Already in `backend/app/api/v1/transactions_api.py` (should be OK)

---

## Verification Checklist

- [ ] Backend container shows "Up" status
- [ ] Frontend container shows "Up" status
- [ ] PostgreSQL container shows "Up (healthy)"
- [ ] `curl http://localhost:8001/api/v1/health` returns JSON
- [ ] Can access http://localhost:3000 in browser
- [ ] No errors in `docker logs trade_backend`

---

## If Everything Fails

Nuclear option (completely reset):

```bash
cd ~/india-trade-analytics

# Stop everything
docker compose down -v

# Remove images
docker rmi india-trade-analytics-backend india-trade-analytics-frontend

# Clean up
rm -f backend/app/main.py.bak backend/app/ingestion/__init__.py.bak

# Copy correct files
cp /mnt/user-data/outputs/main_py_CORRECT.py backend/app/main.py
cp /mnt/user-data/outputs/ingestion_init_CORRECT.py backend/app/ingestion/__init__.py

# Rebuild fresh
docker compose up -d --build

# Wait
sleep 60

# Check
docker compose ps
```

---

## Testing

Once backend is running:

```bash
# Test health
curl http://localhost:8001/api/v1/health

# Test analytics
curl http://localhost:8001/api/v1/analytics/summary

# Test transactions
curl "http://localhost:8001/api/v1/transactions/exports?limit=5"

# Test exporters
curl http://localhost:8001/api/v1/exporters
```

All should return JSON responses.

---

## What Went Wrong

The deployment script used `>>` (append) on files that should have been completely replaced. This caused:
- Duplicate imports
- Broken syntax
- Missing closing brackets

The CORRECT files are complete, properly formatted, and ready to use.

---

**Need help? Run step 1-3 above and let me know the status!** 🚀
