import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.auth import router as auth_router
from app.api.machines import router as machines_router
from app.api.metrics import router as metrics_router
from app.api.alerts import router as alerts_router
from app.api.reports import router as reports_router
from app.api.companies import router as companies_router
from app.api.downloads import router as downloads_router
from app.services.alert_engine import run_alert_check
from app.services.retention import run_retention_cleanup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pcmonitor")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Numbers10 PCMonitor backend...")
    await init_db()
    logger.info("Database initialized, default admin created if needed")

    scheduler.add_job(
        run_alert_check,
        "interval",
        seconds=settings.ALERT_CHECK_INTERVAL,
        id="alert_engine",
        replace_existing=True,
    )
    scheduler.add_job(
        run_retention_cleanup,
        "cron",
        hour=0,
        minute=0,
        id="retention_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Alert engine started (every {settings.ALERT_CHECK_INTERVAL}s)")
    logger.info("Retention cleanup scheduled at midnight")

    yield

    scheduler.shutdown(wait=False)
    logger.info("Backend shutdown complete")


app = FastAPI(
    title="Numbers10 PCMonitor API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(machines_router)
app.include_router(metrics_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(companies_router)
app.include_router(downloads_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Numbers10 PCMonitor"}
