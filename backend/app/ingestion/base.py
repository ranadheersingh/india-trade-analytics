"""Base class for all ingestion pipelines."""
from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import IngestionLog

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    source: str
    status: str
    rows_fetched: int
    rows_loaded: int
    duration_s: float
    error: str | None = None


class Pipeline(ABC):
    """Each pipeline must set name and implement fetch/transform/load."""
    name: str = ""
    schedule_cron: str | None = None  # e.g. "0 2 * * *"

    @abstractmethod
    async def fetch(self, db: Session) -> list[dict]:
        ...

    @abstractmethod
    async def transform(self, db: Session, raw: list[dict]) -> list[dict]:
        ...

    @abstractmethod
    async def load(self, db: Session, rows: list[dict]) -> int:
        """Returns rows actually loaded (after upsert)."""
        ...
    async def run(self) -> IngestionResult:
        start = time.monotonic()
        db: Session = SessionLocal()
        log = IngestionLog(source=self.name, status="running")
        db.add(log)
        db.commit()
        db.refresh(log)
        rows_fetched = 0
        rows_loaded = 0
        error: str | None = None
        final_status = "failed"
        try:
            logger.info("[%s] fetch…", self.name)
            raw = await self.fetch(db)
            rows_fetched = len(raw)
            logger.info("[%s] fetched %d rows", self.name, rows_fetched)

            logger.info("[%s] transform…", self.name)
            rows = await self.transform(db, raw)

            logger.info("[%s] load…", self.name)
            rows_loaded = await self.load(db, rows)
            logger.info("[%s] loaded %d rows", self.name, rows_loaded)

            log.status = "success"
            final_status = "success"
        except Exception as e:
            logger.exception("[%s] failed: %s", self.name, e)
            log.status = "failed"
            final_status = "failed"
            error = str(e)[:1000]
            log.error_message = error
        finally:
            log.finished_at = datetime.now(timezone.utc)
            log.rows_fetched = rows_fetched
            log.rows_loaded = rows_loaded
            try:
                db.commit()
            except Exception as ce:
                logger.exception("[%s] failed to commit ingestion log: %s", self.name, ce)
                db.rollback()
            db.close()

        duration = time.monotonic() - start
        return IngestionResult(
            source=self.name,
            status=final_status,
            rows_fetched=rows_fetched,
            rows_loaded=rows_loaded,
            duration_s=duration,
            error=error,
        )
