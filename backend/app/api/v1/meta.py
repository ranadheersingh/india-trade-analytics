from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models import (
    DimCountry, DimState, DimHsCode, IngestionLog, User,
)
from app.schemas.meta import CountryOut, StateOut, HsCodeOut, IngestionStatusOut

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/countries", response_model=list[CountryOut])
def list_countries(
    q: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(500, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(DimCountry).where(DimCountry.is_active == True)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(
            func.lower(DimCountry.country_name).like(like),
            func.lower(DimCountry.iso_alpha_3).like(like),
            func.lower(DimCountry.iso_alpha_2).like(like),
        ))
    if region:
        stmt = stmt.where(DimCountry.region == region)
    stmt = stmt.order_by(DimCountry.country_name).limit(limit)
    return list(db.execute(stmt).scalars())


@router.get("/states", response_model=list[StateOut])
def list_states(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = db.execute(
        select(DimState).where(DimState.is_active == True).order_by(DimState.state_name)
    ).scalars()
    return list(rows)


@router.get("/hs", response_model=list[HsCodeOut])
def list_hs_codes(
    q: Optional[str] = None,
    level: int = Query(2, ge=2, le=8),
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(DimHsCode).where(
        DimHsCode.is_current == True,
        DimHsCode.hs_level == level,
    )
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(
            func.lower(DimHsCode.description).like(like),
            DimHsCode.hs_code.like(f"{q}%"),
        ))
    stmt = stmt.order_by(DimHsCode.hs_code).limit(limit)
    return list(db.execute(stmt).scalars())


@router.get("/ingestion-status", response_model=list[IngestionStatusOut])
def ingestion_status(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Latest log per source
    sub = (
        select(
            IngestionLog.source,
            func.max(IngestionLog.started_at).label("max_started"),
        )
        .group_by(IngestionLog.source)
        .subquery()
    )
    rows = db.execute(
        select(IngestionLog).join(
            sub,
            (IngestionLog.source == sub.c.source) &
            (IngestionLog.started_at == sub.c.max_started),
        ).order_by(IngestionLog.source)
    ).scalars()

    return [
        IngestionStatusOut(
            source=r.source,
            status=r.status,
            last_run_at=r.started_at.isoformat() if r.started_at else None,
            rows_loaded=r.rows_loaded,
            error_message=r.error_message,
        )
        for r in rows
    ]
