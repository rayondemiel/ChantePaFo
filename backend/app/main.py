import os
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins=settings.cors_origins
)

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

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/health")
async def health():
    return {"status": "ok"}
