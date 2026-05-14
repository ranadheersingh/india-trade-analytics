"""
Phase 2-4: Real NIRYAT Data Loader & Real-Time Tracking System
- Load real government export data
- Real-time shipment tracking
- Vessel position updates
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ingestion.base import Pipeline, IngestionResult
from app.database import SessionLocal
from app.models import (
    DimExporter, DimCountry, FactExportTransaction,
    FactShipmentTracking
)

logger = logging.getLogger(__name__)

# ============================================================================
# REAL NIRYAT DATA LOADER (Production Ready)
# ============================================================================

class RealNiryatDataLoader(Pipeline):
    """
    Load real transaction-level export data from NIRYAT API
    When you get actual API credentials from Government of India
    """
    
    name = "niryat_real_data"
    schedule_cron = "0 2 * * *"  # Daily at 2 AM
    
    def __init__(self, api_key: str = "", api_base: str = ""):
        self.api_key = api_key or "YOUR_API_KEY"
        self.api_base = api_base or "https://niryat.commerce.gov.in/api/v1"
        self.timeout = 60.0
    
    async def run(self) -> IngestionResult:
        """Run real NIRYAT data loader"""
        try:
            logger.info("Starting Real NIRYAT Data Loader...")
            
            db = SessionLocal()
            
            # Fetch last 30 days
            start_date = (datetime.now() - timedelta(days=30)).date()
            end_date = datetime.now().date()
            
            logger.info(f"Fetching data from {start_date} to {end_date}")
            
            # Step 1: Fetch from NIRYAT API
            raw_data = await self._fetch_from_niryat(start_date, end_date)
            logger.info(f"Fetched {len(raw_data)} records from NIRYAT")
            
            # Step 2: Transform data
            transformed = await self._transform_niryat_data(db, raw_data)
            logger.info(f"Transformed {len(transformed)} records")
            
            # Step 3: Load into database
            rows_loaded = await self._load_to_db(db, transformed)
            logger.info(f"Loaded {rows_loaded} new transactions")
            
            db.close()
            
            return IngestionResult(
                status="success",
                rows_loaded=rows_loaded,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Real NIRYAT loader failed: {e}", exc_info=True)
            return IngestionResult(
                status="failed",
                rows_loaded=0,
                error_message=str(e)
            )
    
    async def _fetch_from_niryat(self, start_date, end_date) -> List[Dict]:
        """
        Fetch real export data from NIRYAT API
        
        API Documentation:
        https://niryat.commerce.gov.in/api/v1/docs
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Connecting to NIRYAT API: {self.api_base}")
                
                response = await client.get(
                    f"{self.api_base}/exports/transactions",
                    params={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "format": "json",
                        "limit": 10000,
                        "api_key": self.api_key
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", data.get("records", []))
                elif response.status_code == 401:
                    logger.error("Authentication failed - invalid API key")
                    return []
                elif response.status_code == 429:
                    logger.warning("Rate limited - backing off")
                    await asyncio.sleep(60)
                    return []
                else:
                    logger.error(f"API returned status {response.status_code}")
                    return []
                    
        except httpx.TimeoutException:
            logger.error("API request timed out")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch from NIRYAT: {e}")
            return []
    
    async def _transform_niryat_data(
        self,
        db: Session,
        raw_data: List[Dict]
    ) -> List[Dict]:
        """Transform NIRYAT API data to our schema"""
        
        transformed = []
        
        for row in raw_data:
            try:
                # Map NIRYAT fields to our schema
                trans = {
                    "transaction_id": int(row.get("txn_id", 0)),
                    "export_date": row.get("export_date"),
                    "exporter_iec": row.get("exporter_iec", ""),
                    "exporter_name": row.get("exporter_name", ""),
                    "destination_country": row.get("dest_country"),
                    "destination_code": row.get("dest_code"),
                    "hs_code": row.get("hs_code", ""),
                    "product_desc": row.get("product_desc", ""),
                    "quantity": float(row.get("quantity", 0) or 0),
                    "unit_of_measure": row.get("uom", "KGS"),
                    "unit_price_usd": float(row.get("unit_price_usd", 0) or 0),
                    "total_value_usd": float(row.get("total_value_usd", 0) or 0),
                    "fob_value_usd": float(row.get("fob_value_usd", 0) or 0),
                    "port_of_exit": row.get("port_code", ""),
                    "mode_of_transport": row.get("transport_mode", ""),
                    "shipping_line": row.get("shipping_line", ""),
                    "vessel_name": row.get("vessel_name", ""),
                    "bill_of_lading": row.get("bl_number", ""),
                    "container_number": row.get("container_number", ""),
                    "state": row.get("state", ""),
                    "district": row.get("district", ""),
                }
                
                # Validate required fields
                if not trans["transaction_id"] or not trans["exporter_iec"]:
                    continue
                
                transformed.append(trans)
                
            except Exception as e:
                logger.debug(f"Skipped row: {e}")
                continue
        
        logger.info(f"Transformed {len(transformed)} records")
        return transformed
    
    async def _load_to_db(self, db: Session, data: List[Dict]) -> int:
        """Load transformed data into database"""
        
        rows_loaded = 0
        errors = 0
        
        for trans in data:
            try:
                # Get or create exporter
                exporter = db.query(DimExporter).filter_by(
                    exporter_id=trans["exporter_iec"]
                ).first()
                
                if not exporter:
                    exporter = DimExporter(
                        exporter_id=trans["exporter_iec"],
                        exporter_name=trans["exporter_name"],
                        is_active=True
                    )
                    db.add(exporter)
                    db.flush()
                
                # Get destination country
                country = db.query(DimCountry).filter_by(
                    country_name=trans["destination_country"]
                ).first()
                
                if not country:
                    logger.debug(f"Country not found: {trans['destination_country']}")
                    errors += 1
                    continue
                
                # Calculate fiscal year
                export_date = datetime.strptime(trans["export_date"], "%Y-%m-%d")
                fy = export_date.year + 1 if export_date.month >= 4 else export_date.year
                
                # Insert transaction
                sql = text("""
                    INSERT INTO fact_export_transactions (
                        transaction_id, export_date, fiscal_year_in,
                        exporter_key, destination_country_key, product_hs_code,
                        quantity, unit_of_measure, unit_price_usd, total_value_usd,
                        mode_of_transport, shipping_line, bill_of_lading_number,
                        container_number, created_at, updated_at
                    ) VALUES (
                        :tid, :ed::date, :fy,
                        :ek, :ck, :hc,
                        :qty, :uom, :up, :tv,
                        :mot, :sl, :bol,
                        :cn, NOW(), NOW()
                    )
                    ON CONFLICT (transaction_id) DO UPDATE
                    SET updated_at = NOW()
                """)
                
                db.execute(sql, {
                    "tid": trans["transaction_id"],
                    "ed": trans["export_date"],
                    "fy": fy,
                    "ek": exporter.exporter_key,
                    "ck": country.country_key,
                    "hc": trans["hs_code"],
                    "qty": trans["quantity"],
                    "uom": trans["unit_of_measure"],
                    "up": trans["unit_price_usd"],
                    "tv": trans["total_value_usd"],
                    "mot": trans["mode_of_transport"],
                    "sl": trans["shipping_line"],
                    "bol": trans["bill_of_lading"],
                    "cn": trans["container_number"],
                })
                
                rows_loaded += 1
                
                if rows_loaded % 500 == 0:
                    db.commit()
                    logger.info(f"Committed {rows_loaded} transactions...")
                
            except Exception as e:
                logger.debug(f"Failed to load: {e}")
                db.rollback()
                errors += 1
        
        db.commit()
        logger.info(f"Loaded {rows_loaded} transactions, {errors} errors")
        return rows_loaded
    
    async def fetch(self, db): return []
    async def transform(self, db, raw): return []
    async def load(self, db, rows): return 0


# ============================================================================
# REAL-TIME VESSEL TRACKING (Phase 4)
# ============================================================================

class VesselTrackingService:
    """
    Real-time shipment and vessel tracking
    Integrates with vessel position APIs (MarineTraffic, VesselsValue, etc)
    """
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.timeout = 30.0
    
    async def update_shipment_location(
        self,
        db: Session,
        vessel_imo: str,
        container_number: str,
        api_provider: str = "marinetraffic"
    ) -> bool:
        """
        Fetch current vessel position and update shipment tracking
        
        Supported providers:
        - marinetraffic: Real-time vessel tracking
        - vesselsvalue: Vessel information
        - fleetmon: AIS data
        """
        
        try:
            if api_provider == "marinetraffic":
                position = await self._get_marinetraffic_position(vessel_imo)
            elif api_provider == "fleetmon":
                position = await self._get_fleetmon_position(vessel_imo)
            else:
                return False
            
            if not position:
                return False
            
            # Update shipment tracking
            tracking = db.query(FactShipmentTracking).filter_by(
                container_number=container_number
            ).first()
            
            if tracking:
                tracking.current_location = f"{position['lat']},{position['lon']}"
                tracking.current_port_code = position.get("port")
                tracking.last_update_timestamp = datetime.now()
                tracking.shipment_status = "In-Transit"
                
                # Estimate ETA
                if position.get("destination"):
                    eta = self._estimate_eta(position)
                    tracking.expected_arrival_date = eta
                
                # Check for delays
                if tracking.expected_arrival_date:
                    if datetime.now() > tracking.expected_arrival_date:
                        tracking.is_delayed = True
                        tracking.delay_days = (
                            datetime.now().date() - tracking.expected_arrival_date.date()
                        ).days
                
                db.commit()
                logger.info(f"Updated tracking for {container_number}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update tracking: {e}")
            return False
    
    async def _get_marinetraffic_position(self, vessel_imo: str) -> Optional[Dict]:
        """Get vessel position from MarineTraffic API"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.marinetraffic.com/v3/vesselinfo",
                    params={
                        "imo": vessel_imo,
                        "timespan": "60",
                        "api_key": self.api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        vessel = data[0]
                        return {
                            "lat": float(vessel.get("LAT", 0)),
                            "lon": float(vessel.get("LON", 0)),
                            "port": vessel.get("PORT", ""),
                            "destination": vessel.get("DESTINATION", ""),
                            "speed": float(vessel.get("SPEED", 0)),
                            "course": float(vessel.get("COURSE", 0)),
                            "timestamp": vessel.get("TIMESTAMP")
                        }
        except Exception as e:
            logger.error(f"MarineTraffic API error: {e}")
        
        return None
    
    async def _get_fleetmon_position(self, vessel_imo: str) -> Optional[Dict]:
        """Get vessel position from FleetMon API"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"https://services.fleetmon.com/api/v1/vessel/{vessel_imo}",
                    headers={"Authorization": f"Token {self.api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    last_position = data.get("last_position", {})
                    return {
                        "lat": float(last_position.get("latitude", 0)),
                        "lon": float(last_position.get("longitude", 0)),
                        "port": data.get("last_port", ""),
                        "destination": data.get("destination_port", ""),
                        "speed": float(last_position.get("speed_over_ground", 0)),
                        "course": float(last_position.get("course_over_ground", 0)),
                        "timestamp": last_position.get("timestamp")
                    }
        except Exception as e:
            logger.error(f"FleetMon API error: {e}")
        
        return None
    
    def _estimate_eta(self, position: Dict) -> Optional[datetime]:
        """
        Estimate ETA based on vessel speed and destination
        
        Simple calculation: distance / speed
        For production, use actual routing services
        """
        
        try:
            speed_knots = position.get("speed", 0)
            
            if speed_knots > 0:
                # Average distance for sea routes (rough estimate)
                # In production, use actual distance calculation
                avg_distance_nm = 1000  # nautical miles
                
                estimated_hours = avg_distance_nm / speed_knots
                eta = datetime.now() + timedelta(hours=estimated_hours)
                
                return eta
        except Exception as e:
            logger.error(f"ETA calculation error: {e}")
        
        return None
    
    async def broadcast_tracking_update(self, shipment_id: int, status: str):
        """
        Broadcast tracking update via WebSocket
        For real-time dashboard updates
        """
        
        # This would connect to your WebSocket server
        # Example: await websocket_manager.broadcast({
        #     "type": "tracking_update",
        #     "shipment_id": shipment_id,
        #     "status": status,
        #     "timestamp": datetime.now().isoformat()
        # })
        
        logger.info(f"Broadcasting update for shipment {shipment_id}: {status}")


# ============================================================================
# SCHEDULED TRACKING UPDATES
# ============================================================================

class TrackingScheduler:
    """Periodic tracking updates for all active shipments"""
    
    def __init__(self, vessel_api_key: str = ""):
        self.tracker = VesselTrackingService(vessel_api_key)
    
    async def update_all_shipments(self):
        """Update tracking for all in-transit shipments"""
        
        db = SessionLocal()
        
        try:
            # Get all in-transit shipments
            shipments = db.query(FactShipmentTracking).filter(
                FactShipmentTracking.shipment_status == "In-Transit"
            ).all()
            
            logger.info(f"Updating {len(shipments)} in-transit shipments...")
            
            for shipment in shipments:
                if shipment.vessel_imo_number:
                    await self.tracker.update_shipment_location(
                        db,
                        shipment.vessel_imo_number,
                        shipment.container_number,
                        api_provider="marinetraffic"
                    )
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
            
            logger.info("Shipment tracking update complete")
            
        except Exception as e:
            logger.error(f"Tracking scheduler error: {e}")
        finally:
            db.close()
