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
    
    # Special case: NIRYAT Real (government API)
    if name == "niryat_real":
        try:
            from app.ingestion.niryat_real_data import RealNiryatDataLoader
            import os
            return RealNiryatDataLoader(
                api_key=os.getenv("NIRYAT_API_KEY", ""),
                api_base=os.getenv("NIRYAT_API_BASE", "https://niryat.commerce.gov.in/api/v1")
            )
        except ImportError:
            raise KeyError(f"Real NIRYAT pipeline not available. Available: {list(PIPELINES.keys())}")
    
    # Regular pipelines
    cls = PIPELINES.get(name)
    if not cls:
        raise KeyError(f"Unknown pipeline: {name}. Available: {list(PIPELINES.keys())}")
    return cls()

__all__ = ["PIPELINES", "get_pipeline", "Pipeline", "IngestionResult"]
