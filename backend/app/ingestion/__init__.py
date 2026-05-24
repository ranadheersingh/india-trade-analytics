"""Registry of all available ingestion pipelines."""

from app.ingestion.base import Pipeline, IngestionResult
from app.ingestion.world_bank import WorldBankPipeline
from app.ingestion.comtrade import ComtradePipeline
from app.ingestion.tradestat import TradestatPipeline
from app.ingestion.oec import OecPipeline
from app.ingestion.fx_rates import FxRatesPipeline
from app.ingestion.niryat import NiryatPipeline
from app.ingestion.dgcis import DgcisPipeline

PIPELINES: dict[str, type[Pipeline]] = {
    WorldBankPipeline.name: WorldBankPipeline,
    ComtradePipeline.name: ComtradePipeline,
    TradestatPipeline.name: TradestatPipeline,
    OecPipeline.name: OecPipeline,
    FxRatesPipeline.name: FxRatesPipeline,
    NiryatPipeline.name: NiryatPipeline,
    DgcisPipeline.name: DgcisPipeline,
}

def get_pipeline(name: str) -> Pipeline:
    """
    Get a pipeline by name. Supports both registered and special pipelines.
    
    Special pipelines:
    - niryat_phase2: NIRYAT Phase 2 with sample data
    - niryat_real: Real NIRYAT government API (when credentials available)
    """
    
    # Special case: NIRYAT Phase 2 (sample data)
    if name == "niryat_phase2":
        from app.ingestion.niryat_phase2 import NiryatPhase2Pipeline
        return NiryatPhase2Pipeline()
    
    # Special case: NIRYAT Real (DGFT eBRC API — needs credentials in .env)
    if name == "niryat_real":
        from app.ingestion.niryat_real_data import NIRYATDataLoader

        class _NiryatRealPipeline(Pipeline):
            name = "niryat_real"
            schedule_cron = None

            async def fetch(self, db) -> list[dict]:
                from app.core.config import get_settings
                import asyncio
                s = get_settings()
                if not s.dgft_x_api_key:
                    return []  # no credentials configured
                loader = NIRYATDataLoader()
                from datetime import date, timedelta
                to_d = date.today()
                return await asyncio.to_thread(
                    loader.api_client.get_export_data, to_d - timedelta(days=30), to_d
                ) or []

            async def transform(self, db, raw: list[dict]) -> list[dict]:
                return raw

            async def load(self, db, rows: list[dict]) -> int:
                if not rows:
                    return 0
                loader = NIRYATDataLoader()
                for record in rows:
                    loader._load_export_record(db, record)
                db.commit()
                return len(rows)

        return _NiryatRealPipeline()
    
    # Regular pipelines
    cls = PIPELINES.get(name)
    if not cls:
        raise KeyError(f"Unknown pipeline: {name}. Available: {list(PIPELINES.keys())}")
    return cls()

__all__ = ["PIPELINES", "get_pipeline", "Pipeline", "IngestionResult"]
