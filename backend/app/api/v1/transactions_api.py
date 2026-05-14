"""
Phase 2-4 Transaction APIs
==========================
REST endpoints for transactions, exporters, destinations, analytics, tracking.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models import (
    FactExportTransaction, FactImportTransaction, FactShipmentTracking,
    DimExporter, DimImporter, DimCountry, DimTransportMode, DimHsCode,
    User,
)


router = APIRouter(prefix="/api/v1", tags=["transactions"])


# ============================================================================
# TRANSACTION ENDPOINTS
# ============================================================================

@router.get("/transactions/exports", response_model=List[dict])
def get_export_transactions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    exporter_key: Optional[int] = None,
    country_key: Optional[int] = None,
    hs_code_key: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get export transactions with optional filters"""
    query = db.query(
        FactExportTransaction.id,
        FactExportTransaction.transaction_id,
        FactExportTransaction.value_usd,
        FactExportTransaction.quantity,
        FactExportTransaction.shipment_status,
        DimExporter.company_name.label("exporter_name"),
        DimCountry.country_name.label("destination_country"),
        DimHsCode.description.label("hs_description"),
        DimTransportMode.transport_mode_name.label("transport_mode"),
    ).join(
        DimExporter, FactExportTransaction.exporter_key == DimExporter.exporter_key
    ).join(
        DimCountry, FactExportTransaction.destination_country_key == DimCountry.country_key
    ).join(
        DimHsCode, FactExportTransaction.hs_code_key == DimHsCode.hs_code_key
    ).join(
        DimTransportMode, FactExportTransaction.transport_mode_key == DimTransportMode.transport_mode_key
    )

    if exporter_key:
        query = query.filter(FactExportTransaction.exporter_key == exporter_key)
    if country_key:
        query = query.filter(FactExportTransaction.destination_country_key == country_key)
    if hs_code_key:
        query = query.filter(FactExportTransaction.hs_code_key == hs_code_key)

    results = query.offset(offset).limit(limit).all()
    return [row._asdict() for row in results]


@router.get("/transactions/imports", response_model=List[dict])
def get_import_transactions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    importer_key: Optional[int] = None,
    country_key: Optional[int] = None,
    hs_code_key: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get import transactions with optional filters"""
    query = db.query(
        FactImportTransaction.id,
        FactImportTransaction.transaction_id,
        FactImportTransaction.value_usd,
        FactImportTransaction.quantity,
        FactImportTransaction.shipment_status,
        DimImporter.importer_name,
        DimCountry.country_name.label("origin_country"),
        DimHsCode.description.label("hs_description"),
        DimTransportMode.transport_mode_name.label("transport_mode"),
    ).join(
        DimImporter, FactImportTransaction.importer_key == DimImporter.importer_key
    ).join(
        DimCountry, FactImportTransaction.origin_country_key == DimCountry.country_key
    ).join(
        DimHsCode, FactImportTransaction.hs_code_key == DimHsCode.hs_code_key
    ).join(
        DimTransportMode, FactImportTransaction.transport_mode_key == DimTransportMode.transport_mode_key
    )

    if importer_key:
        query = query.filter(FactImportTransaction.importer_key == importer_key)
    if country_key:
        query = query.filter(FactImportTransaction.origin_country_key == country_key)
    if hs_code_key:
        query = query.filter(FactImportTransaction.hs_code_key == hs_code_key)

    results = query.offset(offset).limit(limit).all()
    return [row._asdict() for row in results]


# ============================================================================
# EXPORTER ENDPOINTS
# ============================================================================

@router.get("/exporters", response_model=List[dict])
def get_exporters(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get exporters with transaction counts and values"""
    subquery = db.query(
        FactExportTransaction.exporter_key,
        func.count(FactExportTransaction.id).label("transaction_count"),
        func.sum(FactExportTransaction.value_usd).label("total_value_usd"),
    ).group_by(FactExportTransaction.exporter_key).subquery()

    query = db.query(
        DimExporter.exporter_key,
        DimExporter.iec_code,
        DimExporter.company_name,
        DimExporter.city,
        DimExporter.state_code,
        subquery.c.transaction_count,
        subquery.c.total_value_usd,
    ).outerjoin(
        subquery, DimExporter.exporter_key == subquery.c.exporter_key
    ).filter(DimExporter.is_active == True)

    results = query.offset(offset).limit(limit).all()
    return [row._asdict() for row in results]


# ============================================================================
# DESTINATION ENDPOINTS
# ============================================================================

@router.get("/destinations", response_model=List[dict])
def get_destinations(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get top destination countries by export value"""
    query = db.query(
        DimCountry.country_name,
        DimCountry.iso_alpha_3,
        func.count(FactExportTransaction.id).label("transaction_count"),
        func.sum(FactExportTransaction.value_usd).label("total_value_usd"),
    ).join(
        FactExportTransaction, DimCountry.country_key == FactExportTransaction.destination_country_key
    ).group_by(
        DimCountry.country_key, DimCountry.country_name, DimCountry.iso_alpha_3
    ).order_by(desc(func.sum(FactExportTransaction.value_usd)))

    results = query.limit(limit).all()
    return [row._asdict() for row in results]


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/summary", response_model=dict)
def get_analytics_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get overall trade analytics summary"""
    export_stats = db.query(
        func.count(FactExportTransaction.id).label("export_transactions"),
        func.sum(FactExportTransaction.value_usd).label("export_value_usd"),
    ).first()

    import_stats = db.query(
        func.count(FactImportTransaction.id).label("import_transactions"),
        func.sum(FactImportTransaction.value_usd).label("import_value_usd"),
    ).first()

    exporter_count = db.query(func.count(DimExporter.exporter_key)).filter(DimExporter.is_active == True).scalar()
    importer_count = db.query(func.count(DimImporter.importer_key)).filter(DimImporter.is_active == True).scalar()

    return {
        "export_transactions": export_stats.export_transactions or 0,
        "export_value_usd": float(export_stats.export_value_usd or 0),
        "import_transactions": import_stats.import_transactions or 0,
        "import_value_usd": float(import_stats.import_value_usd or 0),
        "active_exporters": exporter_count,
        "active_importers": importer_count,
    }


@router.get("/analytics/by-transport-mode", response_model=List[dict])
def get_analytics_by_transport_mode(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get export analytics by transport mode"""
    query = db.query(
        DimTransportMode.transport_mode_name,
        func.count(FactExportTransaction.id).label("transaction_count"),
        func.sum(FactExportTransaction.value_usd).label("total_value_usd"),
    ).join(
        FactExportTransaction, DimTransportMode.transport_mode_key == FactExportTransaction.transport_mode_key
    ).group_by(
        DimTransportMode.transport_mode_key, DimTransportMode.transport_mode_name
    ).order_by(desc(func.sum(FactExportTransaction.value_usd)))

    results = query.all()
    return [row._asdict() for row in results]


@router.get("/analytics/by-hs-code", response_model=List[dict])
def get_analytics_by_hs_code(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get export analytics by HS code"""
    query = db.query(
        DimHsCode.hs_code,
        DimHsCode.description,
        func.count(FactExportTransaction.id).label("transaction_count"),
        func.sum(FactExportTransaction.value_usd).label("total_value_usd"),
    ).join(
        FactExportTransaction, DimHsCode.hs_code_key == FactExportTransaction.hs_code_key
    ).group_by(
        DimHsCode.hs_code_key, DimHsCode.hs_code, DimHsCode.description
    ).order_by(desc(func.sum(FactExportTransaction.value_usd)))

    results = query.limit(limit).all()
    return [row._asdict() for row in results]


# ============================================================================
# TRACKING ENDPOINTS
# ============================================================================

@router.get("/tracking/shipment/{transaction_id}", response_model=List[dict])
def get_shipment_tracking(
    transaction_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get shipment tracking events for a transaction"""
    query = db.query(
        FactShipmentTracking.tracking_event,
        FactShipmentTracking.event_timestamp,
        FactShipmentTracking.location,
        FactShipmentTracking.status_description,
        FactShipmentTracking.carrier_name,
        FactShipmentTracking.vessel_name,
        FactShipmentTracking.estimated_arrival,
        FactShipmentTracking.actual_arrival,
    ).filter(
        FactShipmentTracking.transaction_id == transaction_id
    ).order_by(FactShipmentTracking.event_timestamp)

    results = query.all()
    if not results:
        raise HTTPException(status_code=404, detail="Shipment tracking not found")

    return [row._asdict() for row in results]


# ============================================================================
# REGISTRATION FUNCTION
# ============================================================================

def register_transaction_routes(app):
    """Register all transaction routes with the FastAPI app"""
    app.include_router(router)