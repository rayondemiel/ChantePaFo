import os
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401
from app.auth.router import router as auth_router
from app.config import settings
from app.database import create_tables
from app.logging_config import configure_logging, get_logger
from app.rooms.router import router as rooms_router

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting ChantePaFo backend v%s", "0.1.0")
    await create_tables()
    yield
    logger.info("shutting down ChantePaFo backend")


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=settings.cors_origins)

app = FastAPI(title="ChantePaFo", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth_router)
app.include_router(rooms_router)

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/health")
async def health():
    return {"status": "ok"}


from app.sockets.handlers import register_handlers  # noqa: E402

register_handlers()
