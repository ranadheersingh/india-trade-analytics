"""
REST APIs for India Trade Analytics Phase 2-4
- Transaction Detail API
- Exporter Directory API  
- Analytics API
- Real-time Tracking API
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import (
    FactExportTransaction, FactImportTransaction,
    DimExporter, DimImporter, DimCountry, DimPort,
    FactShipmentTracking
)

# ============================================================================
# TRANSACTIONS API
# ============================================================================

router_transactions = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

class TransactionResponse:
    def __init__(self, t):
        self.transaction_id = t.transaction_id
        self.export_date = t.export_date
        self.exporter_name = None
        self.destination_country = None
        self.product_hs_code = t.product_hs_code
        self.quantity = t.quantity
        self.unit_of_measure = t.unit_of_measure
        self.unit_price_usd = t.unit_price_usd
        self.total_value_usd = t.total_value_usd
        self.mode_of_transport = t.mode_of_transport
        self.shipping_line = t.shipping_line
        self.bill_of_lading = t.bill_of_lading_number
        self.container_number = t.container_number

@router_transactions.get("/exports")
async def list_exports(
    db: Session = Depends(get_db),
    exporter_id: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    hs_code: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0)
):
    """Get export transactions with optional filters"""
    query = db.query(FactExportTransaction).outerjoin(
        DimExporter, FactExportTransaction.exporter_key == DimExporter.exporter_key
    ).outerjoin(
        DimCountry, FactExportTransaction.destination_country_key == DimCountry.country_key
    )
    
    if exporter_id:
        query = query.filter(DimExporter.exporter_id == exporter_id)
    if destination:
        query = query.filter(DimCountry.country_name.ilike(f"%{destination}%"))
    if hs_code:
        query = query.filter(FactExportTransaction.product_hs_code == hs_code)
    if start_date:
        query = query.filter(FactExportTransaction.export_date >= start_date)
    if end_date:
        query = query.filter(FactExportTransaction.export_date <= end_date)
    
    transactions = query.order_by(
        desc(FactExportTransaction.export_date)
    ).limit(limit).offset(skip).all()
    
    results = []
    for t in transactions:
        result = {
            "transaction_id": t[0].transaction_id,
            "export_date": str(t[0].export_date),
            "exporter_name": t[1].exporter_name if t[1] else "Unknown",
            "destination_country": t[2].country_name if t[2] else "Unknown",
            "product_hs_code": t[0].product_hs_code,
            "quantity": t[0].quantity,
            "unit_of_measure": t[0].unit_of_measure,
            "unit_price_usd": float(t[0].unit_price_usd) if t[0].unit_price_usd else 0,
            "total_value_usd": float(t[0].total_value_usd),
            "mode_of_transport": t[0].mode_of_transport,
            "shipping_line": t[0].shipping_line,
            "bill_of_lading": t[0].bill_of_lading_number,
            "container_number": t[0].container_number,
        }
        results.append(result)
    
    return {
        "count": len(results),
        "data": results
    }

@router_transactions.get("/exports/{transaction_id}")
async def get_export_detail(transaction_id: int, db: Session = Depends(get_db)):
    """Get detailed export transaction"""
    transaction = db.query(FactExportTransaction).filter(
        FactExportTransaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    exporter = db.query(DimExporter).filter(
        DimExporter.exporter_key == transaction.exporter_key
    ).first()
    
    country = db.query(DimCountry).filter(
        DimCountry.country_key == transaction.destination_country_key
    ).first()
    
    return {
        "transaction_id": transaction.transaction_id,
        "export_date": str(transaction.export_date),
        "fiscal_year": transaction.fiscal_year_in,
        "exporter": {
            "key": exporter.exporter_key if exporter else None,
            "id": exporter.exporter_id if exporter else None,
            "name": exporter.exporter_name if exporter else None,
            "email": exporter.email if exporter else None,
            "phone": exporter.phone if exporter else None,
            "website": exporter.website if exporter else None,
        },
        "destination": {
            "country": country.country_name if country else None,
            "code": country.country_code if country else None,
        },
        "product": {
            "hs_code": transaction.product_hs_code,
            "quantity": transaction.quantity,
            "unit": transaction.unit_of_measure,
            "unit_price": float(transaction.unit_price_usd) if transaction.unit_price_usd else 0,
        },
        "value": {
            "total_usd": float(transaction.total_value_usd),
            "currency": "USD",
        },
        "logistics": {
            "mode": transaction.mode_of_transport,
            "shipping_line": transaction.shipping_line,
            "bill_of_lading": transaction.bill_of_lading_number,
            "container": transaction.container_number,
        },
        "timestamps": {
            "created": str(transaction.created_at),
            "updated": str(transaction.updated_at),
        }
    }

@router_transactions.get("/imports")
async def list_imports(
    db: Session = Depends(get_db),
    limit: int = Query(100, le=1000)
):
    """Get import transactions"""
    transactions = db.query(FactImportTransaction).limit(limit).all()
    
    return {
        "count": len(transactions),
        "data": [
            {
                "transaction_id": t.transaction_id,
                "import_date": str(t.import_date),
                "total_value_usd": float(t.total_value_usd),
            }
            for t in transactions
        ]
    }

# ============================================================================
# EXPORTERS API
# ============================================================================

router_exporters = APIRouter(prefix="/api/v1/exporters", tags=["exporters"])

@router_exporters.get("")
async def list_exporters(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    """Get list of exporters"""
    query = db.query(DimExporter)
    
    if search:
        query = query.filter(DimExporter.exporter_name.ilike(f"%{search}%"))
    
    exporters = query.limit(limit).all()
    
    results = []
    for exporter in exporters:
        # Get exporter stats
        stats = db.query(
            func.count(FactExportTransaction.transaction_id).label("shipments"),
            func.sum(FactExportTransaction.total_value_usd).label("total_value")
        ).filter(
            FactExportTransaction.exporter_key == exporter.exporter_key
        ).first()
        
        results.append({
            "exporter_key": exporter.exporter_key,
            "exporter_id": exporter.exporter_id,
            "exporter_name": exporter.exporter_name,
            "email": exporter.email,
            "phone": exporter.phone,
            "website": exporter.website,
            "is_active": exporter.is_active,
            "stats": {
                "shipments": stats.shipments or 0,
                "total_value_usd": float(stats.total_value) if stats.total_value else 0,
            }
        })
    
    return {
        "count": len(results),
        "data": results
    }

@router_exporters.get("/{exporter_id}")
async def get_exporter_detail(exporter_id: str, db: Session = Depends(get_db)):
    """Get exporter details with export history"""
    exporter = db.query(DimExporter).filter(
        DimExporter.exporter_id == exporter_id
    ).first()
    
    if not exporter:
        raise HTTPException(status_code=404, detail="Exporter not found")
    
    # Get exports
    exports = db.query(FactExportTransaction).filter(
        FactExportTransaction.exporter_key == exporter.exporter_key
    ).all()
    
    return {
        "exporter": {
            "id": exporter.exporter_id,
            "name": exporter.exporter_name,
            "email": exporter.email,
            "phone": exporter.phone,
            "website": exporter.website,
            "active": exporter.is_active,
        },
        "statistics": {
            "total_shipments": len(exports),
            "total_value_usd": float(sum(e.total_value_usd for e in exports)),
            "avg_shipment_value": float(sum(e.total_value_usd for e in exports) / len(exports)) if exports else 0,
            "destinations": len(set(e.destination_country_key for e in exports)),
        },
        "recent_shipments": [
            {
                "transaction_id": e.transaction_id,
                "date": str(e.export_date),
                "destination": e.destination_country_key,
                "value": float(e.total_value_usd),
            }
            for e in sorted(exports, key=lambda x: x.export_date, reverse=True)[:10]
        ]
    }

# ============================================================================
# DESTINATIONS API
# ============================================================================

router_destinations = APIRouter(prefix="/api/v1/destinations", tags=["destinations"])

@router_destinations.get("")
async def list_destinations(
    db: Session = Depends(get_db),
    top: int = Query(10, le=100)
):
    """Get top destination countries by trade value"""
    results = db.query(
        DimCountry.country_name,
        DimCountry.country_code,
        func.count(FactExportTransaction.transaction_id).label("shipments"),
        func.sum(FactExportTransaction.total_value_usd).label("total_value"),
        func.avg(FactExportTransaction.total_value_usd).label("avg_value")
    ).join(
        FactExportTransaction,
        FactExportTransaction.destination_country_key == DimCountry.country_key
    ).group_by(
        DimCountry.country_key, DimCountry.country_name, DimCountry.country_code
    ).order_by(
        desc("total_value")
    ).limit(top).all()
    
    return {
        "count": len(results),
        "data": [
            {
                "country": r[0],
                "code": r[1],
                "shipments": r[2],
                "total_value_usd": float(r[3]),
                "avg_shipment_value": float(r[4]),
            }
            for r in results
        ]
    }

# ============================================================================
# ANALYTICS API
# ============================================================================

router_analytics = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router_analytics.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    """Get trade summary statistics"""
    export_stats = db.query(
        func.count(FactExportTransaction.transaction_id).label("count"),
        func.sum(FactExportTransaction.total_value_usd).label("value")
    ).first()
    
    exporter_count = db.query(func.count(DimExporter.exporter_key)).scalar()
    destination_count = db.query(
        func.count(func.distinct(FactExportTransaction.destination_country_key))
    ).scalar()
    
    return {
        "exports": {
            "total_shipments": export_stats.count or 0,
            "total_value_usd": float(export_stats.value) if export_stats.value else 0,
        },
        "exporters": exporter_count or 0,
        "destinations": destination_count or 0,
        "as_of": datetime.now().isoformat()
    }

@router_analytics.get("/by-transport-mode")
async def get_transport_mode_analytics(db: Session = Depends(get_db)):
    """Analytics by mode of transport"""
    results = db.query(
        FactExportTransaction.mode_of_transport,
        func.count(FactExportTransaction.transaction_id).label("shipments"),
        func.sum(FactExportTransaction.total_value_usd).label("total_value")
    ).group_by(
        FactExportTransaction.mode_of_transport
    ).order_by(
        desc("total_value")
    ).all()
    
    total_value = sum(r[2] for r in results)
    
    return {
        "data": [
            {
                "mode": r[0],
                "shipments": r[1],
                "total_value_usd": float(r[2]),
                "percentage": float((r[2] / total_value) * 100) if total_value > 0 else 0,
            }
            for r in results
        ]
    }

@router_analytics.get("/by-hs-code")
async def get_hs_code_analytics(
    db: Session = Depends(get_db),
    top: int = Query(10, le=50)
):
    """Top HS codes by trade value"""
    results = db.query(
        FactExportTransaction.product_hs_code,
        func.count(FactExportTransaction.transaction_id).label("shipments"),
        func.sum(FactExportTransaction.total_value_usd).label("total_value")
    ).group_by(
        FactExportTransaction.product_hs_code
    ).order_by(
        desc("total_value")
    ).limit(top).all()
    
    return {
        "count": len(results),
        "data": [
            {
                "hs_code": r[0],
                "shipments": r[1],
                "total_value_usd": float(r[2]),
            }
            for r in results
        ]
    }

@router_analytics.get("/timeline")
async def get_timeline(
    db: Session = Depends(get_db),
    days: int = Query(90, le=365)
):
    """Daily trade timeline"""
    start_date = datetime.now() - timedelta(days=days)
    
    results = db.query(
        func.date(FactExportTransaction.export_date).label("date"),
        func.count(FactExportTransaction.transaction_id).label("shipments"),
        func.sum(FactExportTransaction.total_value_usd).label("value")
    ).filter(
        FactExportTransaction.export_date >= start_date
    ).group_by(
        func.date(FactExportTransaction.export_date)
    ).order_by(
        "date"
    ).all()
    
    return {
        "data": [
            {
                "date": str(r[0]),
                "shipments": r[1],
                "value_usd": float(r[2]),
            }
            for r in results
        ]
    }

# ============================================================================
# TRACKING API (Phase 4)
# ============================================================================

router_tracking = APIRouter(prefix="/api/v1/tracking", tags=["tracking"])

@router_tracking.get("/shipment/{container_number}")
async def track_shipment(container_number: str, db: Session = Depends(get_db)):
    """Real-time shipment tracking"""
    tracking = db.query(FactShipmentTracking).filter(
        FactShipmentTracking.container_number == container_number
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    return {
        "container": tracking.container_number,
        "vessel": tracking.vessel_name,
        "status": tracking.shipment_status,
        "current_location": tracking.current_location,
        "current_port": tracking.current_port_code,
        "timeline": {
            "departure": str(tracking.departure_date) if tracking.departure_date else None,
            "expected_arrival": str(tracking.expected_arrival_date) if tracking.expected_arrival_date else None,
            "actual_arrival": str(tracking.actual_arrival_date) if tracking.actual_arrival_date else None,
        },
        "delay": {
            "is_delayed": tracking.is_delayed,
            "days": tracking.delay_days,
        },
        "documents": {
            "bill_of_lading": tracking.bl_number,
            "invoice": tracking.invoice_number,
            "customs_entry": tracking.customs_entry_number,
        },
        "last_updated": str(tracking.last_update_timestamp)
    }

@router_tracking.get("/exporter/{exporter_id}/active")
async def get_exporter_active_shipments(
    exporter_id: str,
    db: Session = Depends(get_db)
):
    """Get all active shipments for an exporter"""
    exporter = db.query(DimExporter).filter(
        DimExporter.exporter_id == exporter_id
    ).first()
    
    if not exporter:
        raise HTTPException(status_code=404, detail="Exporter not found")
    
    shipments = db.query(
        FactExportTransaction,
        FactShipmentTracking
    ).join(
        FactShipmentTracking,
        FactShipmentTracking.transaction_id == FactExportTransaction.transaction_id,
        isouter=True
    ).filter(
        FactExportTransaction.exporter_key == exporter.exporter_key
    ).all()
    
    return {
        "exporter_id": exporter_id,
        "shipments": [
            {
                "transaction_id": t[0].transaction_id,
                "export_date": str(t[0].export_date),
                "container": t[1].container_number if t[1] else None,
                "status": t[1].shipment_status if t[1] else "No tracking",
                "location": t[1].current_location if t[1] else None,
                "eta": str(t[1].expected_arrival_date) if t[1] and t[1].expected_arrival_date else None,
            }
            for t in shipments
        ]
    }

# ============================================================================
# Register all routers
# ============================================================================

def register_transaction_routes(app):
    app.include_router(router_transactions)
    app.include_router(router_exporters)
    app.include_router(router_destinations)
    app.include_router(router_analytics)
    app.include_router(router_tracking)
