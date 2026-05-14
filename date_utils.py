"""
Date windowing utilities for consistent data filtering across dashboards.

All queries should use these utilities to ensure consistent 5-year rolling window
application across the entire application.

Usage:
    from app.services.date_utils import DateWindow
    
    # Get 5-year rolling window
    start_key, end_key = DateWindow.rolling_window()
    
    # Get current fiscal year
    fy = DateWindow.current_fy()
    
    # Get FY range
    start_fy, end_fy = DateWindow.fy_range(years=5)

Example (Today = May 9, 2026):
    rolling_window() → (20210501, 20260501)
    current_fy() → 2026 (FY26 in Indian fiscal year Apr-Mar)
    fy_range(5) → (2021, 2026)
"""

from datetime import date, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DateWindow:
    """Centralized date windowing for consistent query filtering."""

    # Constants for window sizes
    ROLLING_5_YEAR = 5
    ROLLING_10_YEAR = 10
    ALL_TIME = None

    @staticmethod
    def rolling_window(years: int = 5) -> Tuple[int, int]:
        """
        Return date_key range for rolling window (current month back N years).

        This is the PRIMARY windowing function for all dashboards.
        Use this for any query that shows trend data or time-series data.

        Args:
            years: Number of years back to include (default 5)
                   Use 10 for longer history, or 999 for all-time

        Returns:
            Tuple of (start_date_key, end_date_key)
            Format: YYYYMMDD (integer)

        Example:
            If today is 2026-05-09 and years=5:
                Returns: (20210501, 20260501)

                This means:
                - Start: May 1, 2021 (5 years ago)
                - End: May 1, 2026 (current month)
                - Data window: 5 years = ~60 months
        """
        today = date.today()
        
        # Calculate start year
        start_year = today.year - years
        start_month = today.month
        
        # Create date keys as YYYYMMDD (01 = first of month)
        start_key = int(f"{start_year}{start_month:02d}01")
        end_key = int(f"{today.year}{today.month:02d}01")
        
        logger.debug(
            f"Rolling window ({years}yr): {start_key} to {end_key}",
            extra={"years": years, "start": start_key, "end": end_key}
        )
        
        return start_key, end_key

    @staticmethod
    def current_fy() -> int:
        """
        Return current fiscal year (India: Apr-Mar).

        Indian fiscal year runs from April to March.
        - If today is Apr-Dec: FY = current_year + 1
        - If today is Jan-Mar: FY = current_year

        Example:
            May 9, 2026 → FY26 (Apr 2025 - Mar 2026)
            March 31, 2026 → FY26
            April 1, 2026 → FY27

        Returns:
            Fiscal year as integer (e.g., 2026)
        """
        today = date.today()
        
        # India's fiscal year: Apr-Mar
        # So Jan-Mar is part of the *current* year's FY
        # Apr-Dec is part of the *next* year's FY
        
        if today.month >= 4:  # Apr-Dec: next fiscal year
            return today.year + 1
        else:  # Jan-Mar: current fiscal year
            return today.year

    @staticmethod
    def fy_range(years: int = 5) -> Tuple[int, int]:
        """
        Return fiscal year range for rolling window (current FY back N years).

        Use this for queries that aggregate by fiscal year rather than date_key.

        Args:
            years: Number of fiscal years back to include (default 5)

        Returns:
            Tuple of (start_fy, end_fy)

        Example:
            If today is 2026-05-09 (FY26) and years=5:
                Returns: (2021, 2026)

                This means FY21, FY22, FY23, FY24, FY25, FY26
        """
        end_fy = DateWindow.current_fy()
        start_fy = end_fy - years
        
        logger.debug(
            f"FY range ({years}yr): {start_fy} to {end_fy}",
            extra={"years": years, "start_fy": start_fy, "end_fy": end_fy}
        )
        
        return start_fy, end_fy

    @staticmethod
    def month_window(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, int]:
        """
        Return date_key range for custom month window.

        Useful for user-selected date ranges in future UI features.

        Args:
            start_date: Start date (defaults to 5 years ago)
            end_date: End date (defaults to today)

        Returns:
            Tuple of (start_date_key, end_date_key)

        Example:
            # Last 2 years
            start = date(2024, 5, 1)
            end = date(2026, 5, 1)
            start_key, end_key = DateWindow.month_window(start, end)
            # Returns: (20240501, 20260501)
        """
        if start_date is None:
            # Default: 5 years ago
            today = date.today()
            start_date = date(today.year - 5, today.month, 1)
        
        if end_date is None:
            # Default: today
            today = date.today()
            end_date = date(today.year, today.month, 1)
        
        # Ensure start is on 1st of month
        start_date = date(start_date.year, start_date.month, 1)
        end_date = date(end_date.year, end_date.month, 1)
        
        start_key = int(f"{start_date.year}{start_date.month:02d}01")
        end_key = int(f"{end_date.year}{end_date.month:02d}01")
        
        logger.debug(
            f"Custom month window: {start_key} to {end_key}",
            extra={"start_date": str(start_date), "end_date": str(end_date)}
        )
        
        return start_key, end_key

    @staticmethod
    def date_key_to_date(date_key: int) -> date:
        """
        Convert date_key (YYYYMMDD) to datetime.date object.

        Args:
            date_key: Integer in format YYYYMMDD (e.g., 20260509)

        Returns:
            date object

        Example:
            DateWindow.date_key_to_date(20260509) → date(2026, 5, 9)
        """
        date_str = str(date_key).zfill(8)
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        try:
            return date(year, month, day)
        except ValueError as e:
            logger.error(f"Invalid date_key: {date_key}", extra={"error": str(e)})
            raise ValueError(f"Invalid date_key: {date_key}") from e

    @staticmethod
    def date_to_date_key(d: date) -> int:
        """
        Convert datetime.date to date_key (YYYYMMDD).

        Args:
            d: date object

        Returns:
            Integer in format YYYYMMDD

        Example:
            DateWindow.date_to_date_key(date(2026, 5, 9)) → 20260509
        """
        return int(f"{d.year}{d.month:02d}{d.day:02d}")

    @staticmethod
    def format_period(date_key: int) -> str:
        """
        Format date_key as readable period string (YYYY-MM).

        Useful for display in charts and reports.

        Args:
            date_key: Integer in format YYYYMMDD

        Returns:
            String in format YYYY-MM

        Example:
            DateWindow.format_period(20260509) → "2026-05"
        """
        date_str = str(date_key).zfill(8)
        year = date_str[:4]
        month = date_str[4:6]
        return f"{year}-{month}"

    @staticmethod
    def is_within_window(
        date_key: int,
        window_years: int = 5,
    ) -> bool:
        """
        Check if a date_key falls within the rolling window.

        Useful for validation.

        Args:
            date_key: Date to check (format YYYYMMDD)
            window_years: Window size in years

        Returns:
            True if date_key is within window, False otherwise

        Example:
            # Today = May 9, 2026
            DateWindow.is_within_window(20210501) → True (exactly 5yr ago)
            DateWindow.is_within_window(20210430) → False (outside window)
            DateWindow.is_within_window(20260501) → True (current month)
            DateWindow.is_within_window(20260601) → False (future)
        """
        start_key, end_key = DateWindow.rolling_window(window_years)
        return start_key <= date_key <= end_key

    @staticmethod
    def get_window_summary(window_years: int = 5) -> dict:
        """
        Get human-readable summary of the current window.

        Useful for display in UI or logs.

        Args:
            window_years: Window size in years

        Returns:
            Dictionary with window details

        Example:
            {
                'start_key': 20210501,
                'end_key': 20260501,
                'start_date': '2021-05-01',
                'end_date': '2026-05-01',
                'duration_months': 60,
                'years': 5,
                'generated_at': '2026-05-09T12:34:56'
            }
        """
        start_key, end_key = DateWindow.rolling_window(window_years)
        start_date = DateWindow.date_key_to_date(start_key)
        end_date = DateWindow.date_key_to_date(end_key)
        
        # Calculate months between dates
        months = (end_date.year - start_date.year) * 12 + (
            end_date.month - start_date.month
        )
        
        return {
            "start_key": start_key,
            "end_key": end_key,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "duration_months": months,
            "years": window_years,
            "generated_at": date.today().isoformat(),
        }


# Convenience function - use this as default
def get_rolling_window() -> Tuple[int, int]:
    """Shorthand for DateWindow.rolling_window(). Use this in queries."""
    return DateWindow.rolling_window()


def get_current_fy() -> int:
    """Shorthand for DateWindow.current_fy(). Use this for FY-based queries."""
    return DateWindow.current_fy()


def get_fy_range(years: int = 5) -> Tuple[int, int]:
    """Shorthand for DateWindow.fy_range(). Use this for FY ranges."""
    return DateWindow.fy_range(years)
