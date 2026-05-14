# 🚀 Phase 2-4 Manual Deployment Guide

## Step 1: Copy API Module

```bash
cd ~/india-trade-analytics

# Create API directory
mkdir -p backend/app/api/v1

# Create the API file
cat > backend/app/api/v1/transactions_api.py << 'EOF'
[Copy the content from transaction_apis.py here]
EOF
```

## Step 2: Update FastAPI Main App

Edit `backend/app/main.py` and add at the end (before the last closing braces):

```python
# Phase 2-4 REST APIs
from app.api.v1.transactions_api import register_transaction_routes

# Register all transaction-related routes
register_transaction_routes(app)
```

## Step 3: Deploy Frontend Components

```bash
# Create directories
mkdir -p frontend/src/components/phase2
mkdir -p frontend/src/pages/dashboards

# Copy the component file
cp frontend_components.jsx frontend/src/components/phase2/

# Create transaction dashboard page
cat > frontend/src/pages/dashboards/transactions.tsx << 'EOF'
import { TransactionDashboard } from '@/components/phase2/frontend_components';
export default function TransactionsPage() {
  return <TransactionDashboard />;
}
EOF

# Create exporters dashboard page
cat > frontend/src/pages/dashboards/exporters.tsx << 'EOF'
import { ExporterDirectory } from '@/components/phase2/frontend_components';
export default function ExportersPage() {
  return <ExporterDirectory />;
}
EOF

# Create analytics dashboard page
cat > frontend/src/pages/dashboards/analytics.tsx << 'EOF'
import { AnalyticsDashboard } from '@/components/phase2/frontend_components';
export default function AnalyticsPage() {
  return <AnalyticsDashboard />;
}
EOF

# Create tracking dashboard page
cat > frontend/src/pages/dashboards/tracking.tsx << 'EOF'
import { TrackingDashboard } from '@/components/phase2/frontend_components';
export default function TrackingPage() {
  return <TrackingDashboard />;
}
EOF
```

## Step 4: Deploy Real NIRYAT Data Loader

```bash
# Copy the real data loader
cp niryat_real_data_and_tracking.py backend/app/ingestion/

# Update the ingestion __init__.py
# Add this to backend/app/ingestion/__init__.py
cat >> backend/app/ingestion/__init__.py << 'EOF'

# Real NIRYAT Data Loader
def get_pipeline_niryat_real(name: str):
    if name == "niryat_real":
        from app.ingestion.niryat_real_data import RealNiryatDataLoader
        import os
        return RealNiryatDataLoader(
            api_key=os.getenv("NIRYAT_API_KEY", ""),
            api_base=os.getenv("NIRYAT_API_BASE", "https://niryat.commerce.gov.in/api/v1")
        )
EOF
```

## Step 5: Update .env for APIs

```bash
# Edit or create .env
cat >> .env << 'EOF'

# Real NIRYAT Government API
NIRYAT_API_KEY=your-api-key-when-available
NIRYAT_API_BASE=https://niryat.commerce.gov.in/api/v1

# Vessel Tracking API (MarineTraffic or FleetMon)
VESSEL_API_KEY=your-vessel-api-key
VESSEL_API_PROVIDER=marinetraffic
EOF
```

## Step 6: Enable Tracking in Scheduler

Edit `backend/app/scheduler.py` and add:

```python
# Real-time vessel tracking (Phase 4)
try:
    from app.ingestion.niryat_real_data import TrackingScheduler
    import os
    
    tracking_scheduler = TrackingScheduler(
        vessel_api_key=os.getenv("VESSEL_API_KEY", "")
    )
    
    scheduler.add_job(
        tracking_scheduler.update_all_shipments,
        "interval",
        minutes=15,
        id="vessel_tracking_update"
    )
    
    logger.info("[scheduler] registered vessel_tracking_update with interval '15 min'")
except Exception as e:
    logger.warning(f"Could not initialize tracking scheduler: {e}")
```

## Step 7: Rebuild and Restart

```bash
cd ~/india-trade-analytics

# Stop and remove old containers
docker compose down

# Rebuild with new code
docker compose up -d --build

# Wait for services
sleep 45

# Check status
docker compose ps
```

## Step 8: Verify Deployment

### Test APIs
```bash
# Test transactions endpoint
curl http://localhost:8001/api/v1/transactions/exports

# Test exporters
curl http://localhost:8001/api/v1/exporters

# Test analytics
curl http://localhost:8001/api/v1/analytics/summary

# Test tracking
curl http://localhost:8001/api/v1/tracking/shipment/CONT-002001
```

### Test Dashboards

Open in browser:
- **Transactions**: http://localhost:3000/dashboards/transactions
- **Exporters**: http://localhost:3000/dashboards/exporters
- **Analytics**: http://localhost:3000/dashboards/analytics
- **Tracking**: http://localhost:3000/dashboards/tracking

## Troubleshooting

### API not responding?
```bash
docker logs trade_backend --tail=50 | grep -i "api\|error"
```

### Frontend not loading?
```bash
docker logs trade_frontend --tail=50 | grep -i "error"
```

### Models not found?
Make sure you have FactShipmentTracking model in backend/app/models.py

```bash
# Check if it exists
grep -n "class FactShipmentTracking" backend/app/models.py
```

If missing, add it to models.py:
```python
class FactShipmentTracking(Base):
    __tablename__ = "fact_shipment_tracking"
    
    shipment_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("fact_export_transactions.transaction_id"))
    container_number = Column(String(50))
    vessel_name = Column(String(100))
    vessel_imo_number = Column(String(20))
    shipment_status = Column(String(50))
    current_location = Column(String(100))
    current_port_code = Column(String(10))
    departure_date = Column(Date)
    expected_arrival_date = Column(Date)
    actual_arrival_date = Column(Date)
    is_delayed = Column(Boolean, default=False)
    delay_days = Column(Integer)
    bl_number = Column(String(50))
    invoice_number = Column(String(50))
    customs_entry_number = Column(String(50))
    last_update_timestamp = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

### Still getting 404 on endpoints?
Check that the routers are properly registered. The register_transaction_routes function should be called with the app object.

## What You Have Now

✅ **REST APIs** - 5 endpoints covering:
- Transactions (search, filter, detail)
- Exporters (directory, stats)
- Destinations (analytics)
- Analytics (summary, by mode, by HS code)
- Tracking (real-time shipment tracking)

✅ **Frontend Dashboards** - 4 interactive dashboards:
- Transaction Detail View
- Exporter Directory
- Analytics Dashboard
- Real-Time Tracking

✅ **Real NIRYAT Integration** - Ready for government API when credentials available

✅ **Real-Time Tracking** - Integration with MarineTraffic/FleetMon for live vessel positions

✅ **Sample Data** - 29 transactions already in database

## Next Steps

1. ✅ Deployment complete
2. Test all endpoints
3. Get API credentials when available
4. Enable real data loading
5. Configure vessel tracking

---

**Questions?** Check the COMPLETE_INTEGRATION_GUIDE.md for detailed information about each component.
