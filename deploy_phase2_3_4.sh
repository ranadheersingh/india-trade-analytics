#!/bin/bash
# Complete deployment script for Phase 2-4
# Run this on your production server

set -e

PROJECT_DIR="$HOME/india-trade-analytics"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "🚀 Deploying Phase 2-4 Components..."

# ============================================================================
# 1. COPY AND DEPLOY API MODULE
# ============================================================================

echo "📦 [1/4] Deploying REST APIs..."

# Create API directory if not exists
mkdir -p "$BACKEND_DIR/app/api/v1"

# Copy API module
cp transaction_apis.py "$BACKEND_DIR/app/api/v1/transactions_api.py"

# Update main.py to include APIs
cat >> "$BACKEND_DIR/app/main.py" << 'EOF'

# Phase 2-4 REST APIs
from app.api.v1.transactions_api import register_transaction_routes

# Register all transaction-related routes
register_transaction_routes(app)
EOF

echo "✅ REST APIs deployed"

# ============================================================================
# 2. DEPLOY FRONTEND COMPONENTS
# ============================================================================

echo "📱 [2/4] Deploying Frontend Dashboards..."

# Create component directory
mkdir -p "$FRONTEND_DIR/src/components/phase2"
mkdir -p "$FRONTEND_DIR/src/pages/dashboards"

# Copy components
cp frontend_components.jsx "$FRONTEND_DIR/src/components/phase2/"

# Create dashboard pages
cat > "$FRONTEND_DIR/src/pages/dashboards/transactions.tsx" << 'EOF'
import { TransactionDashboard } from '@/components/phase2/frontend_components';

export default function TransactionsPage() {
  return <TransactionDashboard />;
}
EOF

cat > "$FRONTEND_DIR/src/pages/dashboards/exporters.tsx" << 'EOF'
import { ExporterDirectory } from '@/components/phase2/frontend_components';

export default function ExportersPage() {
  return <ExporterDirectory />;
}
EOF

cat > "$FRONTEND_DIR/src/pages/dashboards/analytics.tsx" << 'EOF'
import { AnalyticsDashboard } from '@/components/phase2/frontend_components';

export default function AnalyticsPage() {
  return <AnalyticsDashboard />;
}
EOF

cat > "$FRONTEND_DIR/src/pages/dashboards/tracking.tsx" << 'EOF'
import { TrackingDashboard } from '@/components/phase2/frontend_components';

export default function TrackingPage() {
  return <TrackingDashboard />;
}
EOF

echo "✅ Frontend dashboards deployed"

# ============================================================================
# 3. DEPLOY NIRYAT REAL DATA LOADER
# ============================================================================

echo "📊 [3/4] Deploying Real NIRYAT Data Loader..."

cp niryat_real_data_and_tracking.py "$BACKEND_DIR/app/ingestion/niryat_real_data.py"

# Update __init__.py to include real data loader
cat >> "$BACKEND_DIR/app/ingestion/__init__.py" << 'EOF'

def get_pipeline(name: str) -> Pipeline:
    if name == "niryat_real":
        from app.ingestion.niryat_real_data import RealNiryatDataLoader
        import os
        return RealNiryatDataLoader(
            api_key=os.getenv("NIRYAT_API_KEY", ""),
            api_base=os.getenv("NIRYAT_API_BASE", "https://niryat.commerce.gov.in/api/v1")
        )
    # ... existing pipelines
EOF

echo "✅ Real NIRYAT data loader deployed"

# ============================================================================
# 4. ENABLE REAL-TIME TRACKING
# ============================================================================

echo "🚚 [4/4] Enabling Real-Time Tracking..."

cat >> "$BACKEND_DIR/app/scheduler.py" << 'EOF'

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
EOF

echo "✅ Real-time tracking enabled"

# ============================================================================
# 5. REBUILD AND RESTART CONTAINERS
# ============================================================================

echo "🔄 Rebuilding and restarting containers..."

cd "$PROJECT_DIR"

docker compose down
docker compose up -d --build

echo "⏳ Waiting for services to be healthy..."
sleep 40

docker compose ps

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo ""
echo "✅ REST APIs:        http://localhost:8001/api/v1"
echo "✅ Transactions:     http://localhost:3000/dashboards/transactions"
echo "✅ Exporters:        http://localhost:3000/dashboards/exporters"
echo "✅ Analytics:        http://localhost:3000/dashboards/analytics"
echo "✅ Tracking:         http://localhost:3000/dashboards/tracking"
echo ""
echo "📝 Don't forget to:"
echo "   1. Set NIRYAT_API_KEY in .env (when available)"
echo "   2. Set VESSEL_API_KEY in .env (MarineTraffic or FleetMon)"
echo "   3. Check logs: docker logs trade_backend"
echo ""
