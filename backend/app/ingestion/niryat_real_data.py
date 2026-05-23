"""
Real NIRYAT Data Integration
============================
Connects to DGFT eBRC API using IEC + DSC for real export data.
Ready for credentials - currently placeholder.
"""

import logging
import requests
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import (
    DimExporter, DimCountry, DimHsCode, DimDate, DimPort, DimTransportMode,
    FactExportTransaction, FactShipmentTracking,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NIRYATAPIClient:
    """DGFT eBRC API client for real export data"""

    def __init__(self):
        self.base_url = "https://eb-rc.dgft.gov.in"  # Placeholder - actual API URL
        self.iec_code = settings.dgft_iec_code or "AXGPK0287Q"
        self.dsc_token = settings.dgft_dsc_token
        self.session = requests.Session()

    def authenticate(self) -> bool:
        """Authenticate with IEC + DSC token"""
        if not self.dsc_token:
            logger.warning("No DSC token configured - real API access disabled")
            return False

        # Placeholder authentication
        # In real implementation:
        # - Use DSC certificate for authentication
        # - Get bearer token
        # - Set session headers
        logger.info("Authenticated with IEC: %s", self.iec_code)
        return True

    def get_export_data(self, from_date: date, to_date: date) -> List[Dict]:
        """Fetch real export transactions from DGFT API"""
        if not self.authenticate():
            return []

        # Placeholder API call
        # Real implementation would:
        # - Call actual DGFT eBRC endpoints
        # - Parse XML/JSON responses
        # - Handle pagination
        logger.info("Fetching export data from %s to %s", from_date, to_date)

        # Return empty for now - ready for real implementation
        return []


class NIRYATDataLoader:
    """Loads real NIRYAT data into warehouse"""

    def __init__(self):
        self.api_client = NIRYATAPIClient()

    def load_recent_exports(self, days_back: int = 30):
        """Load recent export data"""
        to_date = date.today()
        from_date = to_date - timedelta(days=days_back)

        logger.info("Loading NIRYAT data from %s to %s", from_date, to_date)

        export_data = self.api_client.get_export_data(from_date, to_date)

        if not export_data:
            logger.info("No new export data from NIRYAT API")
            return

        with SessionLocal() as db:
            try:
                loaded_count = 0
                for record in export_data:
                    self._load_export_record(db, record)
                    loaded_count += 1

                db.commit()
                logger.info("Loaded %d export records from NIRYAT", loaded_count)

            except Exception as e:
                db.rollback()
                logger.error("Failed to load NIRYAT data: %s", e)
                raise

    def _load_export_record(self, db: Session, record: Dict):
        """Load a single export record"""
        # Placeholder mapping - real implementation would map DGFT fields
        transaction_id = record.get("sb_no")  # Shipping Bill Number

        # Check if already exists
        existing = db.query(FactExportTransaction).filter(
            FactExportTransaction.transaction_id == transaction_id
        ).first()
        if existing:
            return

        # Get dimension keys
        exporter = self._get_or_create_exporter(db, record)
        country = self._get_country(db, record.get("country_code"))
        hs_code = self._get_hs_code(db, record.get("hs_code"))
        date_key = self._get_date_key(db, record.get("sb_date"))
        transport_mode = self._get_transport_mode(db, record.get("mode_of_transport"))

        # Create transaction
        transaction = FactExportTransaction(
            transaction_id=transaction_id,
            export_date_key=date_key,
            exporter_key=exporter.exporter_key,
            destination_country_key=country.country_key if country else None,
            hs_code_key=hs_code.hs_code_key if hs_code else None,
            transport_mode_key=transport_mode.transport_mode_key if transport_mode else None,
            value_usd=float(record.get("fob_value_usd", 0)),
            quantity=float(record.get("quantity", 0)),
            quantity_unit=record.get("unit"),
            currency_code=record.get("currency", "USD"),
            shipment_status="completed",
            source_system="niryat_api",
            extract_date_key=self._get_date_key(db, date.today()),
        )

        db.add(transaction)

    def _get_or_create_exporter(self, db: Session, record: Dict) -> DimExporter:
        """Get or create exporter dimension"""
        iec_code = record.get("iec_code", self.api_client.iec_code)

        exporter = db.query(DimExporter).filter(DimExporter.iec_code == iec_code).first()
        if not exporter:
            exporter = DimExporter(
                iec_code=iec_code,
                company_name=record.get("exporter_name", "Unknown"),
                is_active=True
            )
            db.add(exporter)
            db.flush()

        return exporter

    def _get_country(self, db: Session, country_code: str) -> Optional[DimCountry]:
        """Get country by code"""
        return db.query(DimCountry).filter(
            (DimCountry.iso_alpha_2 == country_code) |
            (DimCountry.iso_alpha_3 == country_code)
        ).first()

    def _get_hs_code(self, db: Session, hs_code: str) -> Optional[DimHsCode]:
        """Get HS code"""
        if not hs_code:
            return None
        return db.query(DimHsCode).filter(DimHsCode.hs_code == hs_code).first()

    def _get_date_key(self, db: Session, date_val: date) -> int:
        """Get date key for date"""
        dim_date = db.query(DimDate).filter(DimDate.full_date == date_val).first()
        return dim_date.date_key if dim_date else None

    def _get_transport_mode(self, db: Session, mode: str) -> Optional[DimTransportMode]:
        """Get transport mode"""
        mode_map = {
            "SEA": "SEA",
            "AIR": "AIR",
            "RAIL": "RAIL",
            "ROAD": "ROAD"
        }
        code = mode_map.get(mode.upper() if mode else "")
        if code:
            return db.query(DimTransportMode).filter(DimTransportMode.transport_mode_code == code).first()
        return None


def load_niryat_real_data():
    """Main entry point for real NIRYAT data loading"""
    loader = NIRYATDataLoader()
    loader.load_recent_exports()


if __name__ == "__main__":
    load_niryat_real_data()