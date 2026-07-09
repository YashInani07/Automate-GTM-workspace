from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.api.v1.router import api_router

# Initialize structured logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Bind rate limiter and handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Register master API routers
app.include_router(api_router, prefix="/api/v1")

# Mount static files folder
app.mount("/static", StaticFiles(directory="/workspace/app/static"), name="static")

@app.get("/")
async def serve_ui():
    return FileResponse("/workspace/app/static/index.html")
