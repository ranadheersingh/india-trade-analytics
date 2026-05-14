"""
Replace the contents of: backend/app/schemas/dashboards.py
======================================================================
Adds StateDetail schema and enhanced StateOverview with KPIs + trend.
Existing schemas kept as-is so other dashboards don't break.
"""
from pydantic import BaseModel
from typing import List, Optional


class KpiCard(BaseModel):
    label: str
    value: float
    unit: str = "USD"
    yoy_change: Optional[float] = None
    yoy_pct: Optional[float] = None


class TimeSeriesPoint(BaseModel):
    period: str  # 'YYYY-MM' or 'YYYY'
    value: float
    direction: Optional[str] = None


class CategoryValue(BaseModel):
    label: str
    code: Optional[str] = None
    value: float
    pct_of_total: Optional[float] = None


class ExecutiveOverview(BaseModel):
    fiscal_year: int
    kpis: List[KpiCard]
    monthly_trend: List[TimeSeriesPoint]
    top_partners_export: List[CategoryValue]
    top_partners_import: List[CategoryValue]
    top_categories_export: List[CategoryValue]
    top_categories_import: List[CategoryValue]
    region_split_export: List[CategoryValue]


class CountryDetail(BaseModel):
    country: dict
    fiscal_year: int
    kpis: List[KpiCard]
    monthly_trend: List[TimeSeriesPoint]
    top_export_products: List[CategoryValue]
    top_import_products: List[CategoryValue]


# ─────────────────────────────────────────────────────────────────────
# StateOverview - enhanced for v2 (new fields are Optional so existing
# clients still work)
# ─────────────────────────────────────────────────────────────────────
class StateOverview(BaseModel):
    fiscal_year: int
    states: List[CategoryValue]
    # NEW v2 additions
    kpis: Optional[List[KpiCard]] = None
    yoy_trend: Optional[List[TimeSeriesPoint]] = None
    top_export_states: Optional[List[CategoryValue]] = None
    top_import_states: Optional[List[CategoryValue]] = None
    region_split: Optional[List[CategoryValue]] = None  # NORTH/SOUTH/EAST/WEST/CENTRAL


# ─────────────────────────────────────────────────────────────────────
# NEW: StateDetail - drill-in view when user clicks a state on the map
# ─────────────────────────────────────────────────────────────────────
class StateDetail(BaseModel):
    state_code: str
    state_name: str
    region: Optional[str] = None
    is_coastal: Optional[bool] = None
    fiscal_year: int

    kpis: List[KpiCard]
    monthly_trend: List[TimeSeriesPoint]
    top_export_products: List[CategoryValue]
    top_import_products: List[CategoryValue]
    top_export_destinations: List[CategoryValue]
    top_import_sources: List[CategoryValue]
    yoy_history: List[TimeSeriesPoint]  # last 5 fiscal years


class SectorDetail(BaseModel):
    hs_2: str
    hs_2_name: str
    fiscal_year: int
    kpis: List[KpiCard]
    monthly_trend: List[TimeSeriesPoint]
    top_export_destinations: List[CategoryValue]
    top_import_sources: List[CategoryValue]
    hs4_breakdown: List[CategoryValue]
