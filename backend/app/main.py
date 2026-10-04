"""Nova Commerce API — FastAPI entrypoint. Docs at /docs and /redoc."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, engine
from .api.v1 import api_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0",
              description="Production e-commerce REST API + Google ADK shopping agent.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
