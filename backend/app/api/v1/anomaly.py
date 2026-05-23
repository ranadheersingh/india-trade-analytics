"""
Trade Anomaly Detection API
============================
Detects anomalous monthly trade values using IQR + rolling Z-score methods.

For each month in the selected window, we compute:
  - rolling mean and std over a 12-month lookback window
  - Z-score = (value - rolling_mean) / rolling_std
  - IQR flag = value outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]

A point is flagged as anomalous if:
  - |z_score| >= z_threshold (default 2.5), OR
  - IQR outlier flag is set AND |z_score| >= 1.5

Returns the full time series with anomaly flags so the frontend can highlight them.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models import DimDate, DimCountry, DimHsCode, FactTradeMonthly, User

router = APIRouter(prefix="/analytics", tags=["anomaly"])
logger = logging.getLogger(__name__)

LOOKBACK = 12       # months for rolling stats
MIN_POINTS = 13     # need at least LOOKBACK+1 to compute rolling stats
Z_THRESHOLD = 2.5


def _date_key_to_period(key: int) -> str:
    s = str(key)
    return f"{s[:4]}-{s[4:6]}"


def _compute_anomalies(values: list[float]) -> list[dict]:
    arr = np.array(values, dtype=float)
    n = len(arr)
    results = []

    # Global IQR
    q1, q3 = np.percentile(arr, 25), np.percentile(arr, 75)
    iqr = q3 - q1
    iqr_lo = q1 - 1.5 * iqr
    iqr_hi = q3 + 1.5 * iqr

    for i, v in enumerate(arr):
        if i < LOOKBACK:
            results.append({"z_score": None, "is_anomaly": False, "anomaly_type": None})
            continue

        window = arr[i - LOOKBACK: i]
        mean = float(np.mean(window))
        std = float(np.std(window))

        if std < 1e-6:
            results.append({"z_score": 0.0, "is_anomaly": False, "anomaly_type": None})
            continue

        z = (v - mean) / std
        iqr_flag = v < iqr_lo or v > iqr_hi

        is_anomaly = abs(z) >= Z_THRESHOLD or (iqr_flag and abs(z) >= 1.5)
        anomaly_type = None
        if is_anomaly:
            anomaly_type = "spike" if z > 0 else "dip"

        results.append({
            "z_score": round(float(z), 3),
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
        })

    return results


@router.get("/anomalies")
def detect_anomalies(
    direction: str = Query("EXPORT", pattern="^(EXPORT|IMPORT|TOTAL)$"),
    country_iso: Optional[str] = Query(None),
    hs_code: Optional[str] = Query(None),
    history_years: int = Query(5, ge=2, le=10),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Detect anomalous months in the trade time series.
    Returns every month in the requested window with anomaly flags.
    """
    stmt = (
        select(
            DimDate.date_key,
            FactTradeMonthly.value_usd,
        )
        .join(DimDate, FactTradeMonthly.date_key == DimDate.date_key)
        .where(FactTradeMonthly.direction == direction)
        .where(FactTradeMonthly.value_usd > 0)
    )

    if country_iso:
        stmt = stmt.join(DimCountry, FactTradeMonthly.country_key == DimCountry.country_key)
        stmt = stmt.where(DimCountry.iso_alpha_3 == country_iso.upper())

    if hs_code:
        stmt = stmt.join(DimHsCode, FactTradeMonthly.hs_key == DimHsCode.hs_key)
        stmt = stmt.where(DimHsCode.hs_code.startswith(hs_code))

    rows = db.execute(stmt.order_by(DimDate.date_key)).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found for the given filters.")

    # Aggregate by period (sum across sources)
    from collections import defaultdict
    agg: dict[str, float] = defaultdict(float)
    for date_key, value in rows:
        period = _date_key_to_period(date_key)
        agg[period] += float(value)

    periods = sorted(agg.keys())
    values = [agg[p] for p in periods]

    # Restrict to last history_years * 12 months
    max_months = history_years * 12
    if len(periods) > max_months:
        periods = periods[-max_months:]
        values = values[-max_months:]

    if len(values) < MIN_POINTS:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough data: need at least {MIN_POINTS} months, got {len(values)}.",
        )

    anomaly_meta = _compute_anomalies(values)

    points = []
    anomaly_count = 0
    for period, value, meta in zip(periods, values, anomaly_meta):
        point = {
            "period": period,
            "value": round(value, 2),
            "z_score": meta["z_score"],
            "is_anomaly": meta["is_anomaly"],
            "anomaly_type": meta["anomaly_type"],
        }
        points.append(point)
        if meta["is_anomaly"]:
            anomaly_count += 1

    anomalies_only = [p for p in points if p["is_anomaly"]]

    return {
        "direction": direction,
        "country_iso": country_iso,
        "hs_code": hs_code,
        "total_months": len(points),
        "anomaly_count": anomaly_count,
        "anomaly_rate_pct": round(anomaly_count / len(points) * 100, 1) if points else 0,
        "z_threshold": Z_THRESHOLD,
        "points": points,
        "anomalies": anomalies_only,
    }
