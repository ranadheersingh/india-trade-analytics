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

@router.get("/transactions/exports")
def get_export_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    country_iso: Optional[str] = Query(None, description="ISO alpha-3 code, e.g. USA"),
    hs_code: Optional[str] = Query(None, description="HS code prefix, e.g. 27"),
    status: Optional[str] = Query(None),
    exporter_key: Optional[int] = Query(None),
    iec_code: Optional[str] = Query(None, description="IEC code, e.g. AXGPK0287Q"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get export transactions with filters and pagination."""
    q = db.query(
        FactExportTransaction.id,
        FactExportTransaction.transaction_id,
        FactExportTransaction.export_date_key,
        FactExportTransaction.value_usd,
        FactExportTransaction.quantity,
        FactExportTransaction.quantity_unit,
        FactExportTransaction.shipment_status,
        DimExporter.company_name.label("exporter_name"),
        DimExporter.iec_code,
        DimCountry.country_name.label("destination_country"),
        DimCountry.iso_alpha_3,
        DimHsCode.hs_code,
        DimHsCode.description.label("hs_description"),
        DimTransportMode.transport_mode_name,
    ).join(DimExporter, FactExportTransaction.exporter_key == DimExporter.exporter_key
    ).join(DimCountry, FactExportTransaction.destination_country_key == DimCountry.country_key
    ).join(DimHsCode, FactExportTransaction.hs_code_key == DimHsCode.hs_code_key
    ).join(DimTransportMode, FactExportTransaction.transport_mode_key == DimTransportMode.transport_mode_key)

    if exporter_key:
        q = q.filter(FactExportTransaction.exporter_key == exporter_key)
    if iec_code:
        q = q.filter(DimExporter.iec_code == iec_code.upper())
    if date_from:
        q = q.filter(FactExportTransaction.export_date_key >= int(date_from.replace("-", "")))
    if date_to:
        q = q.filter(FactExportTransaction.export_date_key <= int(date_to.replace("-", "")))
    if country_iso:
        q = q.filter(DimCountry.iso_alpha_3 == country_iso.upper())
    if hs_code:
        q = q.filter(DimHsCode.hs_code.startswith(hs_code))
    if status:
        q = q.filter(FactExportTransaction.shipment_status == status)

    total = q.count()
    items = q.order_by(desc(FactExportTransaction.export_date_key)).offset((page - 1) * limit).limit(limit).all()
    return {"items": [row._asdict() for row in items], "total": total, "page": page, "limit": limit}


@router.get("/transactions/imports")
def get_import_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    country_iso: Optional[str] = Query(None, description="ISO alpha-3 code"),
    hs_code: Optional[str] = Query(None, description="HS code prefix"),
    status: Optional[str] = Query(None),
    importer_key: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get import transactions with filters and pagination."""
    q = db.query(
        FactImportTransaction.id,
        FactImportTransaction.transaction_id,
        FactImportTransaction.import_date_key,
        FactImportTransaction.value_usd,
        FactImportTransaction.quantity,
        FactImportTransaction.quantity_unit,
        FactImportTransaction.shipment_status,
        DimImporter.importer_name,
        DimCountry.country_name.label("origin_country"),
        DimCountry.iso_alpha_3,
        DimHsCode.hs_code,
        DimHsCode.description.label("hs_description"),
        DimTransportMode.transport_mode_name,
    ).join(DimImporter, FactImportTransaction.importer_key == DimImporter.importer_key
    ).join(DimCountry, FactImportTransaction.origin_country_key == DimCountry.country_key
    ).join(DimHsCode, FactImportTransaction.hs_code_key == DimHsCode.hs_code_key
    ).join(DimTransportMode, FactImportTransaction.transport_mode_key == DimTransportMode.transport_mode_key)

    if importer_key:
        q = q.filter(FactImportTransaction.importer_key == importer_key)
    if date_from:
        q = q.filter(FactImportTransaction.import_date_key >= int(date_from.replace("-", "")))
    if date_to:
        q = q.filter(FactImportTransaction.import_date_key <= int(date_to.replace("-", "")))
    if country_iso:
        q = q.filter(DimCountry.iso_alpha_3 == country_iso.upper())
    if hs_code:
        q = q.filter(DimHsCode.hs_code.startswith(hs_code))
    if status:
        q = q.filter(FactImportTransaction.shipment_status == status)

    total = q.count()
    items = q.order_by(desc(FactImportTransaction.import_date_key)).offset((page - 1) * limit).limit(limit).all()
    return {"items": [row._asdict() for row in items], "total": total, "page": page, "limit": limit}


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


@router.get("/exporters/by-iec/{iec_code}")
def get_exporter_by_iec(
    iec_code: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get exporter profile + stats by IEC code."""
    from sqlalchemy import literal
    sub = db.query(
        FactExportTransaction.exporter_key,
        func.count(FactExportTransaction.id).label("transaction_count"),
        func.sum(FactExportTransaction.value_usd).label("total_value_usd"),
        func.min(FactExportTransaction.export_date_key).label("first_date_key"),
        func.max(FactExportTransaction.export_date_key).label("last_date_key"),
    ).group_by(FactExportTransaction.exporter_key).subquery()

    row = db.query(
        DimExporter,
        sub.c.transaction_count,
        sub.c.total_value_usd,
        sub.c.first_date_key,
        sub.c.last_date_key,
    ).outerjoin(sub, DimExporter.exporter_key == sub.c.exporter_key
    ).filter(DimExporter.iec_code == iec_code.upper()).first()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Exporter {iec_code} not found")

    exp, tx_count, total_val, first_key, last_key = row
    return {
        "exporter_key": exp.exporter_key,
        "iec_code": exp.iec_code,
        "company_name": exp.company_name,
        "city": exp.city,
        "state_code": exp.state_code,
        "address": exp.address,
        "phone": exp.phone,
        "email": exp.email,
        "is_active": exp.is_active,
        "transaction_count": tx_count or 0,
        "total_value_usd": float(total_val or 0),
        "first_export_date": str(first_key) if first_key else None,
        "last_export_date": str(last_key) if last_key else None,
    }


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