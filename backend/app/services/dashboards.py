"""Dashboard service: SQL aggregations producing the data the UI charts need.

Fixes included:
- Rolling 5-year monthly window from current month back to 5 years.
- No future / empty zero months in monthly trend charts.
- State source handling for TOTAL-only FYs such as DGCIS FY26.
- TRADESTAT state partner/source display uses fact_trade_monthly.region, not dim_country.
"""
from typing import Optional
from app.services.date_utils import DateWindow

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import FactTradeMonthly, DimDate, DimCountry, DimState, DimHsCode
from app.schemas.dashboards import (
    ExecutiveOverview,
    CountryDetail,
    StateOverview,
    StateDetail,
    SectorDetail,
    KpiCard,
    TimeSeriesPoint,
    CategoryValue,
)


# ---------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------

def _current_fy() -> int:
    return DateWindow.current_fy()


def _rolling_5_year_month_window() -> tuple[int, int]:
    return DateWindow.rolling_window()


def _kpi_pair(value_curr: float, value_prev: float, label: str) -> KpiCard:
    value_curr = float(value_curr or 0)
    value_prev = float(value_prev or 0)
    yoy = value_curr - value_prev
    pct = (yoy / value_prev) if value_prev else None
    return KpiCard(
        label=label,
        value=value_curr,
        yoy_change=float(yoy or 0),
        yoy_pct=float(pct) if pct is not None else None,
    )


def _latest_fy_with_data(db: Session, requested_fy: Optional[int] = None) -> int:
    """Return requested FY if global trade data exists; otherwise latest FY with data."""
    if requested_fy:
        count_rows = db.execute(
            select(func.count())
            .select_from(FactTradeMonthly)
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .where(
                FactTradeMonthly.direction.in_(["EXPORT", "IMPORT"]),
                FactTradeMonthly.value_usd > 0,
                DimDate.fiscal_year_in == requested_fy,
            )
        ).scalar_one()
        if count_rows and count_rows > 0:
            return int(requested_fy)

    latest_fy = db.execute(
        select(func.max(DimDate.fiscal_year_in))
        .select_from(FactTradeMonthly)
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.direction.in_(["EXPORT", "IMPORT"]),
            FactTradeMonthly.value_usd > 0,
        )
    ).scalar_one()

    return int(latest_fy or requested_fy or DateWindow.current_fy())


def _latest_fy_with_state_data(
    db: Session,
    requested_fy: Optional[int] = None,
    state_key: Optional[int] = None,
) -> int:
    """Return requested FY if state data exists; otherwise latest FY with state data."""
    filters = [FactTradeMonthly.state_key.is_not(None)]
    if state_key is not None:
        filters.append(FactTradeMonthly.state_key == state_key)

    if requested_fy:
        count_rows = db.execute(
            select(func.count())
            .select_from(FactTradeMonthly)
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .where(*filters, DimDate.fiscal_year_in == requested_fy)
        ).scalar_one()
        if count_rows and count_rows > 0:
            return int(requested_fy)

    latest_fy = db.execute(
        select(func.max(DimDate.fiscal_year_in))
        .select_from(FactTradeMonthly)
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(*filters)
    ).scalar_one()

    return int(latest_fy or requested_fy or DateWindow.current_fy())


def _state_directions_for_year(
    db: Session,
    fy: int,
    state_key: Optional[int] = None,
) -> list[str]:
    """Prefer EXPORT/IMPORT if present; otherwise use TOTAL for state datasets."""
    filters = [FactTradeMonthly.state_key.is_not(None), DimDate.fiscal_year_in == fy]
    if state_key is not None:
        filters.append(FactTradeMonthly.state_key == state_key)

    rows = db.execute(
        select(FactTradeMonthly.direction)
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(*filters)
        .group_by(FactTradeMonthly.direction)
    ).all()

    directions = [r.direction for r in rows if r.direction]
    export_import = [d for d in ["EXPORT", "IMPORT"] if d in directions]
    if export_import:
        return export_import
    if "TOTAL" in directions:
        return ["TOTAL"]
    return []


def _split_state_directions(available_dirs: list[str]) -> tuple[list[str], list[str], bool]:
    has_total_only = available_dirs == ["TOTAL"]
    if has_total_only:
        return ["TOTAL"], [], True
    export_dirs = ["EXPORT"] if "EXPORT" in available_dirs else []
    import_dirs = ["IMPORT"] if "IMPORT" in available_dirs else []
    return export_dirs, import_dirs, False


def _monthly_points_from_rows(rows) -> list[TimeSeriesPoint]:
    return [
        TimeSeriesPoint(
            period=f"{r.calendar_year}-{int(r.month_num):02d}",
            value=float(r.v or 0),
            direction=r.direction,
        )
        for r in rows
        if float(r.v or 0) > 0
    ]


def _clean_region_name(region: str | None) -> str:
    region = region or "Unknown"
    return (
        region.replace("__", " / ")
        .replace("_", " ")
        .title()
        .replace("Gcc", "GCC")
        .replace("Asean", "ASEAN")
        .replace("Eu", "EU")
        .replace("Efta", "EFTA")
        .replace("Cis", "CIS")
        .replace("Ne Asia", "NE Asia")
    )


# ---------------------------------------------------------------------
# Executive Overview
# ---------------------------------------------------------------------

def get_executive_overview(db: Session, fiscal_year: Optional[int] = None) -> ExecutiveOverview:
    fy = _latest_fy_with_data(db, fiscal_year)
    fy_prev = fy - 1

    def total_value(direction: str, year: int) -> float:
        return float(
            db.execute(
                select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
                .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
                .where(
                    FactTradeMonthly.direction == direction,
                    DimDate.fiscal_year_in == year,
                    FactTradeMonthly.value_usd > 0,
                )
            ).scalar_one()
            or 0
        )

    exp_curr = total_value("EXPORT", fy)
    imp_curr = total_value("IMPORT", fy)
    exp_prev = total_value("EXPORT", fy_prev)
    imp_prev = total_value("IMPORT", fy_prev)

    kpis = [
        _kpi_pair(exp_curr, exp_prev, "Total Exports (FYTD)"),
        _kpi_pair(imp_curr, imp_prev, "Total Imports (FYTD)"),
        _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade Balance"),
        _kpi_pair(exp_curr + imp_curr, exp_prev + imp_prev, "Total Trade"),
    ]

    start_key, end_key = DateWindow.rolling_window()
    rows = db.execute(
        select(
            DimDate.calendar_year,
            DimDate.month_num,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.date_key.between(start_key, end_key),
            FactTradeMonthly.direction.in_(["EXPORT", "IMPORT"]),
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimDate.calendar_year, DimDate.month_num, FactTradeMonthly.direction)
        .having(func.sum(FactTradeMonthly.value_usd) > 0)
        .order_by(DimDate.calendar_year, DimDate.month_num)
    ).all()
    monthly = _monthly_points_from_rows(rows)

    def top_countries(direction: str, n: int = 10) -> list[CategoryValue]:
        rows = db.execute(
            select(
                DimCountry.iso_alpha_3,
                DimCountry.country_name,
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .join(DimCountry, FactTradeMonthly.country_key == DimCountry.country_key)
            .where(
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.direction == direction,
                FactTradeMonthly.value_usd > 0,
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

    def top_categories(direction: str, n: int = 10) -> list[CategoryValue]:
        rows = db.execute(
            select(
                DimHsCode.hs_2,
                DimHsCode.description,
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .join(DimHsCode, FactTradeMonthly.hs_code_key == DimHsCode.hs_code_key)
            .where(
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.direction == direction,
                FactTradeMonthly.value_usd > 0,
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

    region_rows = db.execute(
        select(DimCountry.region, func.sum(FactTradeMonthly.value_usd).label("v"))
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .join(DimCountry, FactTradeMonthly.country_key == DimCountry.country_key)
        .where(
            DimDate.fiscal_year_in == fy,
            FactTradeMonthly.direction == "EXPORT",
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimCountry.region)
        .order_by(desc("v"))
    ).all()
    total_exp = sum(float(r.v or 0) for r in region_rows) or 1
    region_split = [
        CategoryValue(
            label=r.region or "Unknown",
            value=float(r.v or 0),
            pct_of_total=float(r.v or 0) / total_exp,
        )
        for r in region_rows
    ]

    return ExecutiveOverview(
        fiscal_year=fy,
        kpis=kpis,
        monthly_trend=monthly,
        top_partners_export=top_countries("EXPORT"),
        top_partners_import=top_countries("IMPORT"),
        top_categories_export=top_categories("EXPORT"),
        top_categories_import=top_categories("IMPORT"),
        region_split_export=region_split,
    )


# ---------------------------------------------------------------------
# Country detail
# ---------------------------------------------------------------------

def get_country_detail(db: Session, iso3: str, fiscal_year: Optional[int] = None) -> CountryDetail:
    fy = _latest_fy_with_data(db, fiscal_year)
    fy_prev = fy - 1

    country = db.execute(
        select(DimCountry).where(DimCountry.iso_alpha_3 == iso3.upper())
    ).scalar_one_or_none()
    if not country:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")

    def total_with_country(direction: str, year: int) -> float:
        return float(
            db.execute(
                select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
                .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
                .where(
                    FactTradeMonthly.direction == direction,
                    FactTradeMonthly.country_key == country.country_key,
                    DimDate.fiscal_year_in == year,
                    FactTradeMonthly.value_usd > 0,
                )
            ).scalar_one()
            or 0
        )

    exp_curr = total_with_country("EXPORT", fy)
    imp_curr = total_with_country("IMPORT", fy)
    exp_prev = total_with_country("EXPORT", fy_prev)
    imp_prev = total_with_country("IMPORT", fy_prev)

    kpis = [
        _kpi_pair(exp_curr, exp_prev, f"Exports to {country.country_name}"),
        _kpi_pair(imp_curr, imp_prev, f"Imports from {country.country_name}"),
        _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade Balance"),
        _kpi_pair(exp_curr + imp_curr, exp_prev + imp_prev, "Total Trade"),
    ]

    start_key, end_key = DateWindow.rolling_window()
    rows = db.execute(
        select(
            DimDate.calendar_year,
            DimDate.month_num,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.country_key == country.country_key,
            FactTradeMonthly.date_key.between(start_key, end_key),
            FactTradeMonthly.direction.in_(["EXPORT", "IMPORT"]),
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimDate.calendar_year, DimDate.month_num, FactTradeMonthly.direction)
        .having(func.sum(FactTradeMonthly.value_usd) > 0)
        .order_by(DimDate.calendar_year, DimDate.month_num)
    ).all()
    monthly = _monthly_points_from_rows(rows)

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
                FactTradeMonthly.country_key == country.country_key,
                FactTradeMonthly.direction == direction,
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.value_usd > 0,
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

    return CountryDetail(
        country={
            "iso_alpha_3": country.iso_alpha_3,
            "iso_alpha_2": country.iso_alpha_2,
            "country_name": country.country_name,
            "region": country.region,
            "continent": country.continent,
        },
        fiscal_year=fy,
        kpis=kpis,
        monthly_trend=monthly,
        top_export_products=top_products("EXPORT"),
        top_import_products=top_products("IMPORT"),
    )


# ---------------------------------------------------------------------
# State overview
# ---------------------------------------------------------------------

def get_state_overview(db: Session, fiscal_year: Optional[int] = None) -> StateOverview:
    requested_fy = fiscal_year or DateWindow.current_fy()
    fy = _latest_fy_with_state_data(db=db, requested_fy=requested_fy)
    fy_prev = fy - 1

    available_dirs = _state_directions_for_year(db=db, fy=fy)
    export_dirs, import_dirs, has_total_only = _split_state_directions(available_dirs)
    ranking_dirs = export_dirs if export_dirs else available_dirs

    def total_state_value(directions: list[str], year: int) -> float:
        if not directions:
            return 0.0
        return float(
            db.execute(
                select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
                .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
                .where(
                    FactTradeMonthly.direction.in_(directions),
                    FactTradeMonthly.state_key.is_not(None),
                    DimDate.fiscal_year_in == year,
                    FactTradeMonthly.value_usd > 0,
                )
            ).scalar_one()
            or 0
        )

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
            FactTradeMonthly.direction.in_(ranking_dirs),
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimState.state_code, DimState.state_name)
        .order_by(desc("v"))
    ).all()

    total = sum(float(r.v or 0) for r in rows) or 1
    states = [
        CategoryValue(
            label=r.state_name,
            code=r.state_code,
            value=float(r.v or 0),
            pct_of_total=float(r.v or 0) / total,
        )
        for r in rows
    ]

    import_states: list[CategoryValue] = []
    if import_dirs:
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
                FactTradeMonthly.direction.in_(import_dirs),
                FactTradeMonthly.value_usd > 0,
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

    if has_total_only:
        total_curr = total_state_value(["TOTAL"], fy)
        total_prev = total_state_value(["TOTAL"], fy_prev)
        kpis = [
            _kpi_pair(total_curr, total_prev, "Total state trade"),
            KpiCard(label="States with data", value=float(len(states)), unit="states"),
            KpiCard(label="Available data type", value=1, unit="TOTAL"),
            KpiCard(label="Fiscal year shown", value=float(fy), unit="FY"),
        ]
    else:
        exp_curr = total_state_value(export_dirs, fy)
        exp_prev = total_state_value(export_dirs, fy_prev)
        imp_curr = total_state_value(import_dirs, fy)
        imp_prev = total_state_value(import_dirs, fy_prev)
        kpis = [
            _kpi_pair(exp_curr, exp_prev, "Total state exports"),
            _kpi_pair(imp_curr, imp_prev, "Total state imports"),
            _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade balance"),
            KpiCard(label="States with data", value=float(len(states)), unit="states"),
        ]

    region_rows = db.execute(
        select(DimState.region, func.sum(FactTradeMonthly.value_usd).label("v"))
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .join(DimState, FactTradeMonthly.state_key == DimState.state_key)
        .where(
            DimDate.fiscal_year_in == fy,
            FactTradeMonthly.direction.in_(ranking_dirs),
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimState.region)
        .order_by(desc("v"))
    ).all()
    total_reg = sum(float(r.v or 0) for r in region_rows) or 1
    region_split = [
        CategoryValue(label=r.region or "Unknown", value=float(r.v or 0), pct_of_total=float(r.v or 0) / total_reg)
        for r in region_rows
    ]

    trend_dirs = available_dirs or ranking_dirs
    yoy_rows = db.execute(
        select(
            DimDate.fiscal_year_in,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.state_key.is_not(None),
            FactTradeMonthly.direction.in_(trend_dirs),
            DimDate.fiscal_year_in.between(fy - 4, fy),
            FactTradeMonthly.value_usd > 0,
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
        states=states,
        kpis=kpis,
        yoy_trend=yoy_trend,
        top_export_states=states[:15],
        top_import_states=import_states,
        region_split=region_split,
    )


# ---------------------------------------------------------------------
# State detail
# ---------------------------------------------------------------------

def get_state_detail(db: Session, state_code: str, fiscal_year: Optional[int] = None) -> StateDetail:
    requested_fy = fiscal_year or DateWindow.current_fy()

    state = db.execute(
        select(DimState).where(DimState.state_code == state_code.upper())
    ).scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"State {state_code} not found")

    fy = _latest_fy_with_state_data(db=db, requested_fy=requested_fy, state_key=state.state_key)
    fy_prev = fy - 1

    available_dirs = _state_directions_for_year(db=db, fy=fy, state_key=state.state_key)
    export_dirs, import_dirs, has_total_only = _split_state_directions(available_dirs)

    def total_for_state(directions: list[str], year: int) -> float:
        if not directions:
            return 0.0
        return float(
            db.execute(
                select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
                .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
                .where(
                    FactTradeMonthly.state_key == state.state_key,
                    FactTradeMonthly.direction.in_(directions),
                    DimDate.fiscal_year_in == year,
                    FactTradeMonthly.value_usd > 0,
                )
            ).scalar_one()
            or 0
        )

    if has_total_only:
        total_curr = total_for_state(["TOTAL"], fy)
        total_prev = total_for_state(["TOTAL"], fy_prev)
        kpis = [
            _kpi_pair(total_curr, total_prev, "Total trade"),
            _kpi_pair(total_prev, total_for_state(["TOTAL"], fy_prev - 1), "Previous FY trade"),
            KpiCard(label="Available data type", value=1, unit="TOTAL"),
            KpiCard(label="Fiscal year shown", value=float(fy), unit="FY"),
        ]
        monthly_dirs = ["TOTAL"]
        product_export_dirs = ["TOTAL"]
        product_import_dirs: list[str] = []
        partner_export_dirs = ["TOTAL"]
        partner_import_dirs: list[str] = []
    else:
        exp_curr = total_for_state(export_dirs, fy)
        exp_prev = total_for_state(export_dirs, fy_prev)
        imp_curr = total_for_state(import_dirs, fy)
        imp_prev = total_for_state(import_dirs, fy_prev)
        kpis = [
            _kpi_pair(exp_curr, exp_prev, "Exports"),
            _kpi_pair(imp_curr, imp_prev, "Imports"),
            _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade balance"),
            _kpi_pair(exp_curr + imp_curr, exp_prev + imp_prev, "Total trade"),
        ]
        monthly_dirs = available_dirs
        product_export_dirs = export_dirs
        product_import_dirs = import_dirs
        partner_export_dirs = export_dirs
        partner_import_dirs = import_dirs

    start_key, end_key = DateWindow.rolling_window()
    monthly_trend: list[TimeSeriesPoint] = []
    if monthly_dirs:
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
                FactTradeMonthly.direction.in_(monthly_dirs),
                FactTradeMonthly.date_key.between(start_key, end_key),
                FactTradeMonthly.value_usd > 0,
            )
            .group_by(DimDate.calendar_year, DimDate.month_num, FactTradeMonthly.direction)
            .having(func.sum(FactTradeMonthly.value_usd) > 0)
            .order_by(DimDate.calendar_year, DimDate.month_num)
        ).all()
        monthly_trend = _monthly_points_from_rows(monthly_rows)

    def top_products(directions: list[str], n: int = 10) -> list[CategoryValue]:
        if not directions:
            return []
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
                FactTradeMonthly.direction.in_(directions),
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.value_usd > 0,
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

    def top_partners(directions: list[str], n: int = 10) -> list[CategoryValue]:
        if not directions:
            return []

        # TRADESTAT state-level files are region-wise. country_key is usually India.
        tradestat_rows = db.execute(
            select(
                FactTradeMonthly.region.label("region"),
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .where(
                FactTradeMonthly.state_key == state.state_key,
                FactTradeMonthly.direction.in_(directions),
                FactTradeMonthly.source_system == "TRADESTAT",
                FactTradeMonthly.region.is_not(None),
                FactTradeMonthly.region != "",
                FactTradeMonthly.region != "WORLD",
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.value_usd > 0,
            )
            .group_by(FactTradeMonthly.region)
            .order_by(desc("v"))
            .limit(n)
        ).all()
        if tradestat_rows:
            total = sum(float(r.v or 0) for r in tradestat_rows) or 1
            return [
                CategoryValue(
                    label=_clean_region_name(r.region),
                    code=r.region,
                    value=float(r.v or 0),
                    pct_of_total=float(r.v or 0) / total,
                )
                for r in tradestat_rows
            ]

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
                FactTradeMonthly.direction.in_(directions),
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.value_usd > 0,
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

    history_dirs = monthly_dirs or available_dirs
    yoy_history: list[TimeSeriesPoint] = []
    if history_dirs:
        hist_rows = db.execute(
            select(
                DimDate.fiscal_year_in,
                FactTradeMonthly.direction,
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .where(
                FactTradeMonthly.state_key == state.state_key,
                FactTradeMonthly.direction.in_(history_dirs),
                DimDate.fiscal_year_in.between(fy - 4, fy),
                FactTradeMonthly.value_usd > 0,
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
        top_export_products=top_products(product_export_dirs),
        top_import_products=top_products(product_import_dirs),
        top_export_destinations=top_partners(partner_export_dirs),
        top_import_sources=top_partners(partner_import_dirs),
        yoy_history=yoy_history,
    )


# ---------------------------------------------------------------------
# Sector detail
# ---------------------------------------------------------------------

def get_sector_detail(db: Session, hs_2: str, fiscal_year: Optional[int] = None) -> SectorDetail:
    fy = _latest_fy_with_data(db, fiscal_year)
    fy_prev = fy - 1

    hs_row = db.execute(
        select(DimHsCode).where(
            DimHsCode.hs_2 == hs_2,
            DimHsCode.hs_level == 2,
            DimHsCode.is_current == True,
        )
    ).scalar_one_or_none()
    if not hs_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HS-2 code not found")

    def total_for_hs(direction: str, year: int) -> float:
        return float(
            db.execute(
                select(func.coalesce(func.sum(FactTradeMonthly.value_usd), 0))
                .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
                .join(DimHsCode, FactTradeMonthly.hs_code_key == DimHsCode.hs_code_key)
                .where(
                    DimHsCode.hs_2 == hs_2,
                    FactTradeMonthly.direction == direction,
                    DimDate.fiscal_year_in == year,
                    FactTradeMonthly.value_usd > 0,
                )
            ).scalar_one()
            or 0
        )

    exp_curr = total_for_hs("EXPORT", fy)
    imp_curr = total_for_hs("IMPORT", fy)
    exp_prev = total_for_hs("EXPORT", fy_prev)
    imp_prev = total_for_hs("IMPORT", fy_prev)

    kpis = [
        _kpi_pair(exp_curr, exp_prev, "Exports"),
        _kpi_pair(imp_curr, imp_prev, "Imports"),
        _kpi_pair(exp_curr - imp_curr, exp_prev - imp_prev, "Trade Balance"),
    ]

    start_key, end_key = DateWindow.rolling_window()
    rows = db.execute(
        select(
            DimDate.calendar_year,
            DimDate.month_num,
            FactTradeMonthly.direction,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .join(DimHsCode, FactTradeMonthly.hs_code_key == DimHsCode.hs_code_key)
        .where(
            DimHsCode.hs_2 == hs_2,
            FactTradeMonthly.date_key.between(start_key, end_key),
            FactTradeMonthly.direction.in_(["EXPORT", "IMPORT"]),
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimDate.calendar_year, DimDate.month_num, FactTradeMonthly.direction)
        .having(func.sum(FactTradeMonthly.value_usd) > 0)
        .order_by(DimDate.calendar_year, DimDate.month_num)
    ).all()
    monthly = _monthly_points_from_rows(rows)

    def top_dest(direction: str, n: int = 10) -> list[CategoryValue]:
        rows = db.execute(
            select(
                DimCountry.iso_alpha_3,
                DimCountry.country_name,
                func.sum(FactTradeMonthly.value_usd).label("v"),
            )
            .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
            .join(DimHsCode, FactTradeMonthly.hs_code_key == DimHsCode.hs_code_key)
            .join(DimCountry, FactTradeMonthly.country_key == DimCountry.country_key)
            .where(
                DimHsCode.hs_2 == hs_2,
                FactTradeMonthly.direction == direction,
                DimDate.fiscal_year_in == fy,
                FactTradeMonthly.value_usd > 0,
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

    return SectorDetail(
        hs_2=hs_2,
        hs_2_name=hs_row.description,
        fiscal_year=fy,
        kpis=kpis,
        monthly_trend=monthly,
        top_export_destinations=top_dest("EXPORT"),
        top_import_sources=top_dest("IMPORT"),
        hs4_breakdown=[],
    )
