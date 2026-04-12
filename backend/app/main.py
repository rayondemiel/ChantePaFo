import os
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import socketio
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import models  # noqa: F401
from app.auth.router import router as auth_router
from app.config import settings
from app.database import create_tables
from app.logging_config import configure_logging, get_logger
from app.middlewares.metrics import PrometheusMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.rooms.router import router as rooms_router

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting ChantePaFo backend v%s", "0.1.0")
    await create_tables()
    yield
    logger.info("shutting down ChantePaFo backend")


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=settings.cors_origins)

app = FastAPI(title="ChantePaFo", version="0.1.0", lifespan=lifespan)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
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

from app.audio.router import router as audio_router  # noqa: E402

app.include_router(audio_router)

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


_metrics_auth_scheme = HTTPBasic(auto_error=False)


def _verify_metrics_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_metrics_auth_scheme)],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.metrics_username.encode("utf-8"),
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.metrics_password.encode("utf-8"),
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint(
    _: Annotated[None, Depends(_verify_metrics_auth)],
) -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


from app.game import blindtest as _blindtest  # noqa: F401, E402
from app.game import karaoke as _karaoke  # noqa: F401, E402
from app.game import telephone as _telephone  # noqa: F401, E402
from app.sockets.handlers import register_handlers  # noqa: E402

register_handlers()
