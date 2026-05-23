import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.core.security import hash_password
from app.api.deps import require_admin
from app.models import User
from app.schemas.auth import UserCreate, UserOut
from app.ingestion import PIPELINES, get_pipeline

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# ---- Users ----

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [UserOut.model_validate(u) for u in rows]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if req.role not in ("viewer", "analyst", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = db.execute(select(User).where(User.email == req.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(require_admin),
):
    if user_id == me.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"status": "ok"}


# ---- Ingestion ----

_EXTRA_SOURCES = [
    {"name": "niryat_phase2", "schedule": None},
    {"name": "niryat_real",   "schedule": None},
]

@router.get("/ingestion/sources")
def list_sources(_: User = Depends(require_admin)):
    regular = [{"name": n, "schedule": cls.schedule_cron} for n, cls in PIPELINES.items()]
    return regular + _EXTRA_SOURCES

@router.post("/ingestion/trigger/{source}")
async def trigger_ingestion(
    source: str,
    background: BackgroundTasks,
    _: User = Depends(require_admin),
):
    try:
        get_pipeline(source)  # validate — raises KeyError if unknown
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    async def _run():
        try:
            pipe = get_pipeline(source)
            result = await pipe.run()
            logger.info("[admin] %s finished: %s", source, result)
        except Exception as e:
            logger.exception("[admin] %s failed: %s", source, e)

    background.add_task(_run)
    return {"status": "started", "source": source}
