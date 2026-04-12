import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

# Paths that must not be instrumented to avoid self-referential noise / cardinality.
_EXCLUDED_PATHS = {"/metrics", "/health"}
_ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"})


class PrometheusMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "") or ""
        if path in _EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        raw_method: str = scope.get("method", "GET") or "GET"
        method = raw_method if raw_method in _ALLOWED_METHODS else "OTHER"
        status_holder: dict[str, int] = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = int(message["status"])
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            # Prefer route template (e.g. /rooms/{code}) to bound label cardinality.
            route = scope.get("route")
            route_template = getattr(route, "path", None) if route is not None else None
            label_path = route_template or "unmatched"
            HTTP_REQUEST_DURATION_SECONDS.labels(method, label_path).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(method, label_path, str(status_holder["status"])).inc()
