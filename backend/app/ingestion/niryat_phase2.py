"""
Phase 2 Sample Data Loader
==========================
Loads sample export transactions, exporters, and tracking data.
"""

import logging
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import (
    DimExporter, DimImporter, DimPort, DimTransportMode,
    FactExportTransaction, FactImportTransaction, FactShipmentTracking,
    DimCountry, DimHsCode, DimDate,
)

logger = logging.getLogger(__name__)


def load_sample_data():
    """Load sample Phase 2-4 data"""
    with SessionLocal() as db:
        try:
            # Check if data already exists
            if db.query(FactExportTransaction).first():
                logger.info("Sample data already loaded, skipping")
                return

            logger.info("Loading Phase 2-4 sample data...")

            # Get reference data
            usa = db.query(DimCountry).filter(DimCountry.iso_alpha_3 == "USA").first()
            deu = db.query(DimCountry).filter(DimCountry.iso_alpha_3 == "DEU").first()
            chn = db.query(DimCountry).filter(DimCountry.iso_alpha_3 == "CHN").first()

            hs_tea = db.query(DimHsCode).filter(DimHsCode.hs_code.like("0902%")).first()
            hs_textiles = db.query(DimHsCode).filter(DimHsCode.hs_code.like("5201%")).first()
            hs_electronics = db.query(DimHsCode).filter(DimHsCode.hs_code.like("8541%")).first()
            hs_spices = db.query(DimHsCode).filter(DimHsCode.hs_code.like("0904%")).first()

            date_2024 = db.query(DimDate).filter(DimDate.calendar_year == 2024).first()

            # Create transport modes
            sea_mode = DimTransportMode(
                transport_mode_code="SEA",
                transport_mode_name="Sea Freight",
                is_active=True
            )
            air_mode = DimTransportMode(
                transport_mode_code="AIR",
                transport_mode_name="Air Freight",
                is_active=True
            )
            rail_mode = DimTransportMode(
                transport_mode_code="RAIL",
                transport_mode_name="Rail Freight",
                is_active=True
            )
            road_mode = DimTransportMode(
                transport_mode_code="ROAD",
                transport_mode_name="Road Freight",
                is_active=True
            )

            db.add_all([sea_mode, air_mode, rail_mode, road_mode])
            db.flush()

            # Create exporters
            exporter1 = DimExporter(
                iec_code="AXGPK0287Q",  # Real IEC from summary
                company_name="Test Exporter",
                city="Mumbai",
                state_code="MH",
                is_active=True
            )
            exporter2 = DimExporter(
                iec_code="ABCDE1234F",
                company_name="Apex Textiles",
                city="Surat",
                state_code="GJ",
                is_active=True
            )
            exporter3 = DimExporter(
                iec_code="FGHIJ5678K",
                company_name="Global Electronics",
                city="Bangalore",
                state_code="KA",
                is_active=True
            )
            exporter4 = DimExporter(
                iec_code="KLMNO9012P",
                company_name="Spice Traders",
                city="Kochi",
                state_code="KL",
                is_active=True
            )

            db.add_all([exporter1, exporter2, exporter3, exporter4])
            db.flush()

            # Create ports
            mumbai_port = DimPort(
                port_code="INBOM",
                port_name="Mumbai Port",
                country_key=usa.country_key,  # India
                port_type="sea",
                is_active=True
            )
            delhi_airport = DimPort(
                port_code="DEL",
                port_name="Indira Gandhi International Airport",
                country_key=usa.country_key,
                port_type="air",
                is_active=True
            )

            db.add_all([mumbai_port, delhi_airport])
            db.flush()

            # Create sample export transactions
            transactions = [
                FactExportTransaction(
                    transaction_id="EXP2024001",
                    export_date_key=date_2024.date_key,
                    exporter_key=exporter1.exporter_key,
                    destination_country_key=usa.country_key,
                    hs_code_key=hs_textiles.hs_code_key,
                    port_key=mumbai_port.port_key,
                    transport_mode_key=sea_mode.transport_mode_key,
                    value_usd=50000.00,
                    quantity=1000.0,
                    quantity_unit="KG",
                    shipment_status="completed",
                    source_system="sample",
                    extract_date_key=date_2024.date_key,
                ),
                FactExportTransaction(
                    transaction_id="EXP2024002",
                    export_date_key=date_2024.date_key,
                    exporter_key=exporter2.exporter_key,
                    destination_country_key=deu.country_key,
                    hs_code_key=hs_textiles.hs_code_key,
                    port_key=mumbai_port.port_key,
                    transport_mode_key=sea_mode.transport_mode_key,
                    value_usd=75000.00,
                    quantity=1500.0,
                    quantity_unit="KG",
                    shipment_status="in_transit",
                    source_system="sample",
                    extract_date_key=date_2024.date_key,
                ),
                FactExportTransaction(
                    transaction_id="EXP2024003",
                    export_date_key=date_2024.date_key,
                    exporter_key=exporter3.exporter_key,
                    destination_country_key=chn.country_key,
                    hs_code_key=hs_electronics.hs_code_key,
                    port_key=delhi_airport.port_key,
                    transport_mode_key=air_mode.transport_mode_key,
                    value_usd=120000.00,
                    quantity=500.0,
                    quantity_unit="PCS",
                    shipment_status="completed",
                    source_system="sample",
                    extract_date_key=date_2024.date_key,
                ),
                FactExportTransaction(
                    transaction_id="EXP2024004",
                    export_date_key=date_2024.date_key,
                    exporter_key=exporter4.exporter_key,
                    destination_country_key=usa.country_key,
                    hs_code_key=hs_spices.hs_code_key,
                    port_key=mumbai_port.port_key,
                    transport_mode_key=sea_mode.transport_mode_key,
                    value_usd=25000.00,
                    quantity=200.0,
                    quantity_unit="KG",
                    shipment_status="completed",
                    source_system="sample",
                    extract_date_key=date_2024.date_key,
                ),
                FactExportTransaction(
                    transaction_id="EXP2024005",
                    export_date_key=date_2024.date_key,
                    exporter_key=exporter1.exporter_key,
                    destination_country_key=deu.country_key,
                    hs_code_key=hs_tea.hs_code_key,
                    port_key=mumbai_port.port_key,
                    transport_mode_key=rail_mode.transport_mode_key,
                    value_usd=30000.00,
                    quantity=300.0,
                    quantity_unit="KG",
                    shipment_status="completed",
                    source_system="sample",
                    extract_date_key=date_2024.date_key,
                ),
                FactExportTransaction(
                    transaction_id="EXP2024006",
                    export_date_key=date_2024.date_key,
                    exporter_key=exporter2.exporter_key,
                    destination_country_key=chn.country_key,
                    hs_code_key=hs_textiles.hs_code_key,
                    port_key=None,
                    transport_mode_key=road_mode.transport_mode_key,
                    value_usd=15000.00,
                    quantity=250.0,
                    quantity_unit="KG",
                    shipment_status="in_transit",
                    source_system="sample",
                    extract_date_key=date_2024.date_key,
                ),
            ]

            db.add_all(transactions)
            db.flush()

            # Create sample tracking events
            tracking_events = [
                FactShipmentTracking(
                    transaction_id="EXP2024001",
                    tracking_event="departed",
                    event_timestamp=datetime(2024, 5, 1, 10, 0),
                    location="Mumbai Port, India",
                    status_description="Container loaded onto vessel",
                    carrier_name="Maersk Line",
                    vessel_name="Maersk Dubai",
                    voyage_number="MDU001",
                    source_system="sample",
                ),
                FactShipmentTracking(
                    transaction_id="EXP2024001",
                    tracking_event="arrived",
                    event_timestamp=datetime(2024, 5, 15, 14, 30),
                    location="Los Angeles Port, USA",
                    status_description="Container unloaded and customs cleared",
                    carrier_name="Maersk Line",
                    vessel_name="Maersk Dubai",
                    voyage_number="MDU001",
                    actual_arrival=datetime(2024, 5, 15, 14, 30),
                    source_system="sample",
                ),
                FactShipmentTracking(
                    transaction_id="EXP2024002",
                    tracking_event="departed",
                    event_timestamp=datetime(2024, 5, 2, 8, 0),
                    location="Mumbai Port, India",
                    status_description="Container loaded onto vessel",
                    carrier_name="MSC",
                    vessel_name="MSC Anna",
                    voyage_number="MSC002",
                    source_system="sample",
                ),
                FactShipmentTracking(
                    transaction_id="EXP2024003",
                    tracking_event="departed",
                    event_timestamp=datetime(2024, 5, 3, 16, 0),
                    location="Delhi Airport, India",
                    status_description="Air freight departed",
                    carrier_name="Lufthansa Cargo",
                    voyage_number="LH123",
                    source_system="sample",
                ),
                FactShipmentTracking(
                    transaction_id="EXP2024003",
                    tracking_event="arrived",
                    event_timestamp=datetime(2024, 5, 4, 6, 0),
                    location="Shanghai Airport, China",
                    status_description="Air freight arrived and customs processing",
                    carrier_name="Lufthansa Cargo",
                    voyage_number="LH123",
                    actual_arrival=datetime(2024, 5, 4, 6, 0),
                    source_system="sample",
                ),
            ]

            db.add_all(tracking_events)
            db.commit()

            logger.info("✅ Loaded 6 sample export transactions, 4 exporters, 13 transport modes, 4 tracking events")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to load sample data: {e}")
            raise


if __name__ == "__main__":
    load_sample_data()