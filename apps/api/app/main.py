from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import init_db
from app.core.logging import configure_logging, get_logger

configure_logging(settings.debug)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir, "screenshots").mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir, "uploads").mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir, "output").mkdir(parents=True, exist_ok=True)
    await init_db()
    log.info("startup.complete", llm=settings.llm_model)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


def _include_routers() -> None:
    from app.routers import auth, dashboard, runs, suggestions

    app.include_router(auth.router)
    app.include_router(runs.router)
    app.include_router(suggestions.router)
    app.include_router(dashboard.router)


_include_routers()
