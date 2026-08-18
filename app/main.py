from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.bootstrap import ensure_admin_user
from app.config import get_settings
from app.database import engine, init_db
from app.routers import agent, auth, connections, dashboard, health, library, logs, oauth_google, oauth_tiktok, queue, settings_router
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.media_inbox_dir.mkdir(parents=True, exist_ok=True)
    settings.media_import_dir.mkdir(parents=True, exist_ok=True)
    settings.media_processed_dir.mkdir(parents=True, exist_ok=True)
    settings.media_youtube_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    with Session(engine) as session:
        ensure_admin_user(session)

    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="ShortBridge", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(connections.router)
app.include_router(oauth_google.router)
app.include_router(oauth_tiktok.router)
app.include_router(agent.router)
app.include_router(library.router)
app.include_router(queue.router)
app.include_router(settings_router.router)
app.include_router(logs.router)
