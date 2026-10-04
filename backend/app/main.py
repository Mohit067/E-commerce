"""Nova Commerce API — FastAPI entrypoint. Docs at /docs and /redoc."""
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, engine
from .api.v1 import api_router

settings = get_settings()

# --- tiny in-memory sliding-window rate limiter (auth + agent endpoints) ---
_hits: dict[str, deque] = defaultdict(deque)
LIMITS = {"/api/v1/auth": (30, 60), "/api/v1/agent": (60, 60)}  # (max_requests, window_sec)


async def rate_limit_mw(request: Request, call_next):
    for prefix, (mx, win) in LIMITS.items():
        if request.url.path.startswith(prefix):
            key = f"{prefix}:{request.client.host if request.client else '?'}"
            now = time.time()
            q = _hits[key]
            while q and q[0] < now - win:
                q.popleft()
            if len(q) >= mx:
                return JSONResponse(status_code=429, content={
                    "error": {"code": "RATE_LIMITED", "message": "Too many requests, slow down."}})
            q.append(now)
    return await call_next(request)

app = FastAPI(title=settings.app_name, version="1.0.0",
              description="Production e-commerce REST API + Google ADK shopping agent.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.middleware("http")(rate_limit_mw)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}})
    return JSONResponse(status_code=500,
                        content={"error": {"code": "INTERNAL_ERROR", "message": "Something went wrong"}})


@app.on_event("startup")
def startup():
    from . import models  # noqa: F401 — register tables
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["system"])
def health():
    return {"ok": True, "service": settings.app_name}


app.include_router(api_router, prefix=settings.api_v1_prefix)
