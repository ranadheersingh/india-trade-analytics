"""
Trade Forecast API
==================
Uses Holt-Winters triple exponential smoothing (additive trend + seasonality)
to generate 12-month forward forecasts from fact_trade_monthly data.

No external service required — pure statsmodels, runs in-process.
"""
from __future__ import annotations

import calendar
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models import DimDate, DimCountry, DimHsCode, FactTradeMonthly, User

router = APIRouter(prefix="/analytics", tags=["forecast"])
logger = logging.getLogger(__name__)

MIN_HISTORY_MONTHS = 24   # need at least 2 years to fit seasonal model
FORECAST_HORIZON = 12     # always forecast 12 months ahead


def _date_key_to_period(key: int) -> str:
    s = str(key)
    return f"{s[:4]}-{s[4:6]}"


def _period_to_date_key_end(year: int, month: int) -> int:
    last = calendar.monthrange(year, month)[1]
    return int(f"{year:04d}{month:02d}{last:02d}")


def _run_hw(values: list[float]) -> list[float]:
    """Fit Holt-Winters and return FORECAST_HORIZON predictions."""
    arr = np.array(values, dtype=float)
    # Replace zeros/negatives with small positive to avoid log-scale issues
    arr = np.where(arr <= 0, arr.mean() * 0.01 if arr.mean() > 0 else 1.0, arr)

    try:
        model = ExponentialSmoothing(
            arr,
            trend="add",
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated",
        ).fit(optimized=True, remove_bias=True)
        forecast = model.forecast(FORECAST_HORIZON)
        # Clamp negative forecasts to 0
        return [max(0.0, float(v)) for v in forecast]
    except Exception as e:
        logger.warning("HW model failed (%s); using naive seasonal fallback", e)
        # Fallback: repeat last year's seasonality scaled by YoY trend
        if len(arr) >= 24:
            last_yr = arr[-12:]
            prev_yr = arr[-24:-12]
            trend = (last_yr.mean() / prev_yr.mean()) if prev_yr.mean() > 0 else 1.0
            return [max(0.0, float(v * trend)) for v in last_yr[:FORECAST_HORIZON]]
        return [float(arr[-1])] * FORECAST_HORIZON


@router.get("/forecast")
def get_forecast(
    direction: str = Query("EXPORT", description="EXPORT or IMPORT"),
    country_iso: Optional[str] = Query(None, description="ISO-3 code to filter by partner"),
    hs_code: Optional[str] = Query(None, description="HS-2 chapter prefix"),
    history_years: int = Query(5, ge=2, le=10),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Forecast the next 12 months of trade value using Holt-Winters.

    Returns:
      - historical: list of {period, value, type="actual"}
      - forecast:   list of {period, value, lower, upper, type="forecast"}
      - model_info: metadata about the fit
    """
    direction = direction.upper()
    if direction not in ("EXPORT", "IMPORT", "TOTAL"):
        raise HTTPException(400, "direction must be EXPORT, IMPORT, or TOTAL")

    # ── Build query ──────────────────────────────────────────────────────────
    q = (
        select(
            DimDate.calendar_year,
            DimDate.month_num,
            func.sum(FactTradeMonthly.value_usd).label("v"),
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(
            FactTradeMonthly.direction == direction,
            FactTradeMonthly.value_usd > 0,
        )
        .group_by(DimDate.calendar_year, DimDate.month_num)
        .order_by(DimDate.calendar_year, DimDate.month_num)
    )

    if country_iso:
        country = db.execute(
            select(DimCountry).where(DimCountry.iso_alpha_3 == country_iso.upper())
        ).scalar_one_or_none()
        if not country:
            raise HTTPException(404, f"Country {country_iso} not found")
        q = q.where(FactTradeMonthly.country_key == country.country_key)

    if hs_code:
        hs_rows = db.execute(
            select(DimHsCode.hs_code_key).where(DimHsCode.hs_code.startswith(hs_code))
        ).scalars().all()
        if not hs_rows:
            raise HTTPException(404, f"HS code {hs_code} not found")
        q = q.where(FactTradeMonthly.hs_code_key.in_(hs_rows))

    rows = db.execute(q).all()

    if not rows:
        raise HTTPException(404, "No data found for the given filters")

    # ── Build dense monthly series (fill gaps with 0) ─────────────────────
    # Only keep the last `history_years` years
    max_y = max(r.calendar_year for r in rows)
    min_y = max_y - history_years + 1
    data_map: dict[tuple, float] = {
        (r.calendar_year, int(r.month_num)): float(r.v or 0)
        for r in rows
        if r.calendar_year >= min_y
    }

    series_keys: list[tuple[int, int]] = []
    y, m = min_y, 1
    while (y, m) <= (max_y, 12):
        series_keys.append((y, m))
        m += 1
        if m > 13:
            m = 1
            y += 1

    # Truncate to actual last data point (don't include trailing zeros)
    values = [data_map.get(k, 0.0) for k in series_keys]
    last_nonzero = max((i for i, v in enumerate(values) if v > 0), default=-1)
    if last_nonzero < 0:
        raise HTTPException(404, "All values are zero")
    series_keys = series_keys[: last_nonzero + 1]
    values = values[: last_nonzero + 1]

    if len(values) < MIN_HISTORY_MONTHS:
        raise HTTPException(
            422,
            f"Need at least {MIN_HISTORY_MONTHS} months of data; got {len(values)}",
        )

    # ── Fit model ────────────────────────────────────────────────────────────
    forecasted = _run_hw(values)

    # ── Build forecast periods ────────────────────────────────────────────
    last_y, last_m = series_keys[-1]
    forecast_keys: list[tuple[int, int]] = []
    fy, fm = last_y, last_m + 1
    for _ in range(FORECAST_HORIZON):
        if fm > 12:
            fm = 1
            fy += 1
        forecast_keys.append((fy, fm))
        fm += 1

    # ── Confidence interval: ±20% scaled by recent volatility ────────────
    recent = np.array(values[-12:])
    cv = float(recent.std() / recent.mean()) if recent.mean() > 0 else 0.2
    ci_pct = min(0.40, max(0.10, cv))

    historical_out = [
        {"period": f"{y:04d}-{m:02d}", "value": round(v, 2), "type": "actual"}
        for (y, m), v in zip(series_keys, values)
    ]
    forecast_out = [
        {
            "period": f"{y:04d}-{m:02d}",
            "value": round(v, 2),
            "lower": round(v * (1 - ci_pct), 2),
            "upper": round(v * (1 + ci_pct), 2),
            "type": "forecast",
        }
        for (y, m), v in zip(forecast_keys, forecasted)
    ]

    return {
        "direction": direction,
        "country_iso": country_iso,
        "hs_code": hs_code,
        "history_months": len(values),
        "forecast_horizon": FORECAST_HORIZON,
        "ci_pct": round(ci_pct * 100, 1),
        "historical": historical_out,
        "forecast": forecast_out,
        "annual_forecast_usd": round(sum(forecasted), 2),
    }
