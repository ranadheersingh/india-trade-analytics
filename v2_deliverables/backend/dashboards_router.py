"""
Replace the entire contents of: backend/app/api/v1/dashboards.py
======================================================================
Adds the /dashboards/states/{state_code} drill-in endpoint.
All other endpoints unchanged.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models import User
from app.services.dashboards import (
    get_executive_overview,
    get_country_detail,
    get_state_overview,
    get_state_detail,         # NEW
    get_sector_detail,
)
from app.schemas.dashboards import (
    ExecutiveOverview, CountryDetail, StateOverview, StateDetail, SectorDetail,
)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/executive", response_model=ExecutiveOverview)
def executive(
    fiscal_year: Optional[int] = Query(None, ge=2010, le=2100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_executive_overview(db, fiscal_year)


@router.get("/country/{iso3}", response_model=CountryDetail)
def country(
    iso3: str,
    fiscal_year: Optional[int] = Query(None, ge=2010, le=2100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_country_detail(db, iso3, fiscal_year)


@router.get("/states", response_model=StateOverview)
def states(
    fiscal_year: Optional[int] = Query(None, ge=2010, le=2100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_state_overview(db, fiscal_year)


# NEW: drill-in to a specific state (clicked on the India map)
@router.get("/states/{state_code}", response_model=StateDetail)
def state_detail(
    state_code: str,
    fiscal_year: Optional[int] = Query(None, ge=2010, le=2100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_state_detail(db, state_code, fiscal_year)


@router.get("/sector/{hs_2}", response_model=SectorDetail)
def sector(
    hs_2: str,
    fiscal_year: Optional[int] = Query(None, ge=2010, le=2100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_sector_detail(db, hs_2, fiscal_year)
