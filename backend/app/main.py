"""
India Trade Analytics - FastAPI Main Application
Phase 1: States & Sectors Dashboard
Phase 2-4: Transaction Details, Exporters, Tracking
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.db import engine, Base
from app.seeds.run import run_all_seeds
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for the application
    """
    # Startup
    logger.info("Starting India Trade Analytics backend…")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Run seeds
    run_all_seeds()
    
    # Start scheduler
    scheduler = start_scheduler()
    if scheduler:
        scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down India Trade Analytics backend…")
    stop_scheduler()

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="India Trade Analytics API",
    description="Complete India export/import analytics platform",
    version="2.4.0",
    lifespan=lifespan
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

# Phase 2-4 REST APIs
try:
    from app.api.v1.transactions_api import register_transaction_routes
    register_transaction_routes(app)
    logger.info("✅ Phase 2-4 REST APIs registered")
except ImportError as e:
    logger.warning(f"Phase 2-4 APIs not available: {e}")
except Exception as e:
    logger.warning(f"Error registering Phase 2-4 APIs: {e}")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "India Trade Analytics API",
        "version": "2.4.0"
    }

@app.get("/api/v1/health")
async def api_health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": str(__import__('datetime').datetime.now())
    }

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "message": "India Trade Analytics Platform",
        "version": "2.4.0",
        "docs": "http://localhost:8001/docs",
        "api_v1": "http://localhost:8001/api/v1",
        "dashboards": {
            "states": "http://localhost:3000/dashboards/states",
            "transactions": "http://localhost:3000/dashboards/transactions",
            "exporters": "http://localhost:3000/dashboards/exporters",
            "analytics": "http://localhost:3000/dashboards/analytics",
            "tracking": "http://localhost:3000/dashboards/tracking"
        }
    }

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
