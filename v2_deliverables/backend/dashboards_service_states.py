"""
ADD/REPLACE in: backend/app/services/dashboards.py
======================================================================
This file shows ONLY the state-related changes. Other functions stay as-is.

  - REPLACE the existing `get_state_overview()` with the version below
  - ADD the new `get_state_detail()` function
  - Keep all other functions (`get_executive_overview`, etc.) unchanged
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc
from fastapi import HTTPException, status

from app.models import (
    FactTradeMonthly, DimDate, DimCountry, DimState, DimHsCode,
)
from app.schemas.dashboards import (
    StateOverview, StateDetail,
    KpiCard, TimeSeriesPoint, CategoryValue,
)


def _current_fy() -> int:
    from datetime import date
    today = date.today()
    return today.year + 1 if today.month >= 4 else today.year


def _kpi_pair(value_curr: float, value_prev: float, label: str) -> KpiCard:
    yoy = value_curr - value_prev
    pct = (yoy / value_prev) if value_prev else None
    return KpiCard(
        label=label,
        value=float(value_curr or 0),
        yoy_change=float(yoy or 0),
        yoy_pct=float(pct) if pct is not None else None,
    )


# ─────────────────────────────────────────────────────────────────────
# REPLACEMENT for existing get_state_overview()
# ─────────────────────────────────────────────────────────────────────
def get_state_overview(db: Session, fiscal_year: Optional[int] = None) -> StateOverview:
    """State performance overview with KPIs, trend, and region split."""
    fy = fiscal_year or _current_fy()
    fy_prev = fy - 1

    # 1. State export ranking (existing logic)
    rows = db.execute(
        select(
            DimState.state_code,
            DimState.state_name,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .join(DimState, FactTradeMonthly.state_key == DimState.state_key)
        .where(
            DimDate.fiscal_year_in == fy,
            FactTradeMonthly.direction == "EXPORT",
        )
        .group_by(DimState.state_code, DimState.state_name)
        .order_by(desc("v"))
    ).all()
    total = sum(float(r.v or 0) for r in rows) or 1
    export_states = [
        CategoryValue(
            label=r.state_name,
            code=r.state_code,
            value=float(r.v or 0),
            pct_of_total=float(r.v or 0) / total,
        )
        for r in rows
    ]

    # 2. Same for imports (NEW)
    rows_imp = db.execute(
        select(
            DimState.state_code,
            DimState.state_name,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .join(DimState, FactTradeMonthly.state_key == DimState.state_key)
        .where(
            DimDate.fiscal_year_in == fy,
            FactTradeMonthly.direction == "IMPORT",
        )
        .group_by(DimState.state_code, DimState.state_name)
        .order_by(desc("v"))
        .limit(15)
    ).all()
    total_imp = sum(float(r.v or 0) for r in rows_imp) or 1
    import_states = [
        CategoryValue(
            label=r.state_name,
            code=r.state_code,
            value=float(r.v or 0),
            pct_of_total=float(r.v or 0) / total_imp,
        )
        for r in rows_imp
    ]

    # 3. KPI cards (NEW)
    def total_state_value(direction: str, year: int) -> float:
        return db.execute(
            select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .where(
                FactTradeMonthly.direction == direction,
                FactTradeMonthly.state_key.is_not(None),
                DimDate.fiscal_year_in == year,
            )
        ).scalar_one() or 0

    exp_curr = float(total_state_value("EXPORT", fy))
    exp_prev = float(total_state_value("EXPORT", fy_prev))
    imp_curr = float(total_state_value("IMPORT", fy))
    imp_prev = float(total_state_value("IMPORT", fy_prev))

    kpis = [
        _kpi_pair(exp_curr, exp_prev, "Total state exports"),
        _kpi_pair(imp_curr, imp_prev, "Total state imports"),
        _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade balance"),
        KpiCard(
            label="States with data",
            value=float(len(export_states)),
            unit="states",
        ),
    ]

    # 4. Region split (NORTH/SOUTH/EAST/WEST/CENTRAL) -- NEW
    region_rows = db.execute(
        select(
            DimState.region,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .join(DimState, FactTradeMonthly.state_key == DimState.state_key)
        .where(
            DimDate.fiscal_year_in == fy,
            FactTradeMonthly.direction == "EXPORT",
        )
        .group_by(DimState.region)
        .order_by(desc("v"))
    ).all()
    total_reg = sum(float(r.v or 0) for r in region_rows) or 1
    region_split = [
        CategoryValue(
            label=r.region or "Unknown",
            value=float(r.v or 0),
            pct_of_total=float(r.v or 0) / total_reg,
        )
        for r in region_rows
    ]

    # 5. YoY trend (last 5 FYs) -- NEW
    yoy_rows = db.execute(
        select(
            DimDate.fiscal_year_in,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.state_key.is_not(None),
            DimDate.fiscal_year_in.between(fy - 4, fy),
        )
        .group_by(DimDate.fiscal_year_in, FactTradeMonthly.direction)
        .order_by(DimDate.fiscal_year_in)
    ).all()
    yoy_trend = [
        TimeSeriesPoint(
            period=f"FY{str(r.fiscal_year_in)[-2:]}",
            value=float(r.v or 0),
            direction=r.direction,
        )
        for r in yoy_rows
    ]

    return StateOverview(
        fiscal_year=fy,
        states=export_states,           # backwards compatible
        kpis=kpis,
        yoy_trend=yoy_trend,
        top_export_states=export_states[:15],
        top_import_states=import_states,
        region_split=region_split,
    )


# ─────────────────────────────────────────────────────────────────────
# NEW: get_state_detail() -- powers the drill-in page when user clicks
#                            a state on the India map
# ─────────────────────────────────────────────────────────────────────
def get_state_detail(
    db: Session, state_code: str, fiscal_year: Optional[int] = None
) -> StateDetail:
    fy = fiscal_year or _current_fy()
    fy_prev = fy - 1

    state = db.execute(
        select(DimState).where(DimState.state_code == state_code.upper())
    ).scalar_one_or_none()
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State {state_code} not found",
        )

    # KPIs for this specific state
    def total_for_state(direction: str, year: int) -> float:
        return db.execute(
            select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .where(
                FactTradeMonthly.state_key == state.state_key,
                FactTradeMonthly.direction == direction,
                DimDate.fiscal_year_in == year,
            )
        ).scalar_one() or 0

    exp_curr = float(total_for_state("EXPORT", fy))
    exp_prev = float(total_for_state("EXPORT", fy_prev))
    imp_curr = float(total_for_state("IMPORT", fy))
    imp_prev = float(total_for_state("IMPORT", fy_prev))

    kpis = [
        _kpi_pair(exp_curr, exp_prev, "Exports"),
        _kpi_pair(imp_curr, imp_prev, "Imports"),
        _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade balance"),
        _kpi_pair(exp_curr + imp_curr, exp_prev + imp_prev, "Total trade"),
    ]

    # Monthly trend for this state
    monthly_rows = db.execute(
        select(
            DimDate.calendar_year,
            DimDate.month_num,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.state_key == state.state_key,
            DimDate.fiscal_year_in == fy,
        )
        .group_by(DimDate.calendar_year, DimDate.month_num, FactTradeMonthly.direction)
        .order_by(DimDate.calendar_year, DimDate.month_num)
    ).all()
    monthly_trend = [
        TimeSeriesPoint(
            period=f"{r.calendar_year}-{r.month_num:02d}",
            value=float(r.v or 0),
            direction=r.direction,
        )
        for r in monthly_rows
    ]

    # Top export products (HS-2)
    def top_products(direction: str, n: int = 10) -> list[CategoryValue]:
        rows = db.execute(
            select(
                DimHsCode.hs_2,
                DimHsCode.description,
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .join(DimHsCode, FactTradeMonthly.hs_code_key == DimHsCode.hs_code_key)
            .where(
                FactTradeMonthly.state_key == state.state_key,
                FactTradeMonthly.direction == direction,
                DimDate.fiscal_year_in == fy,
            )
            .group_by(DimHsCode.hs_2, DimHsCode.description)
            .order_by(desc("v"))
            .limit(n)
        ).all()
        total = sum(float(r.v or 0) for r in rows) or 1
        return [
            CategoryValue(
                label=f"{r.hs_2} — {(r.description or '')[:60]}",
                code=r.hs_2,
                value=float(r.v or 0),
                pct_of_total=float(r.v or 0) / total,
            )
            for r in rows
        ]

    # Top destination/source countries
    def top_partners(direction: str, n: int = 10) -> list[CategoryValue]:
        rows = db.execute(
            select(
                DimCountry.iso_alpha_3,
                DimCountry.country_name,
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .join(DimCountry, FactTradeMonthly.country_key == DimCountry.country_key)
            .where(
                FactTradeMonthly.state_key == state.state_key,
                FactTradeMonthly.direction == direction,
                DimDate.fiscal_year_in == fy,
            )
            .group_by(DimCountry.iso_alpha_3, DimCountry.country_name)
            .order_by(desc("v"))
            .limit(n)
        ).all()
        total = sum(float(r.v or 0) for r in rows) or 1
        return [
            CategoryValue(
                label=r.country_name,
                code=r.iso_alpha_3,
                value=float(r.v or 0),
                pct_of_total=float(r.v or 0) / total,
            )
            for r in rows
        ]

    # 5-year history
    hist_rows = db.execute(
        select(
            DimDate.fiscal_year_in,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.state_key == state.state_key,
            DimDate.fiscal_year_in.between(fy - 4, fy),
        )
        .group_by(DimDate.fiscal_year_in, FactTradeMonthly.direction)
        .order_by(DimDate.fiscal_year_in)
    ).all()
    yoy_history = [
        TimeSeriesPoint(
            period=f"FY{str(r.fiscal_year_in)[-2:]}",
            value=float(r.v or 0),
            direction=r.direction,
        )
        for r in hist_rows
    ]

    return StateDetail(
        state_code=state.state_code,
        state_name=state.state_name,
        region=state.region,
        is_coastal=state.is_coastal,
        fiscal_year=fy,
        kpis=kpis,
        monthly_trend=monthly_trend,
        top_export_products=top_products("EXPORT"),
        top_import_products=top_products("IMPORT"),
        top_export_destinations=top_partners("EXPORT"),
        top_import_sources=top_partners("IMPORT"),
        yoy_history=yoy_history,
    )
