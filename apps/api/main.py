"""FastAPI application main entry point"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.core.config import settings
from app.core.database import init_db, close_db, create_indexes
from app.core.cache import init_cache, close_cache
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging, audit
from app.api.v1.router import api_router
from app.api.v1.endpoints.rag import retrieval_engine
from app.rag.knowledge_loader import load_obsidian_documents
from app.websocket import websocket_manager
from app.websocket.router import websocket_router


# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting up...")

    # Validate LLM configuration
    available = settings.available_llm_providers
    if not available:
        logging.warning(
            "No real LLM provider API keys are configured. "
            "The application will fall back to MockLLM. "
            "Set KIMI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY to enable real LLM responses."
        )
    else:
        logging.info("Available LLM providers: %s", ", ".join(available))

    # Initialize cache
    await init_cache()

    # Initialize database
    await init_db()

    # Create indexes
    await create_indexes()

    # Load Obsidian knowledge base into RAG engine
    loaded_docs = load_obsidian_documents(retrieval_engine)
    if loaded_docs:
        logging.info("RAG engine loaded with %d documents.", loaded_docs)

    print("✅ Application started successfully")

    yield

    # Shutdown
    print("🛑 Shutting down...")

    # Close cache
    await close_cache()

    # Close database
    await close_db()

    print("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Jarvis PM - AI-powered Product Management Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Register exception handlers
register_exception_handlers(app)

# Add middleware (order matters - first added is first executed)

# 1. Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "*.jarvis-pm.com"]
)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. GZip Compression — disabled to prevent SSE streaming buffering
# app.add_middleware(GZipMiddleware, minimum_size=1000)



# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Ensure UTF-8 charset for JSON responses
@app.middleware("http")
async def add_content_type_charset(request: Request, call_next):
    """Add charset=utf-8 to JSON responses for Windows terminal compatibility"""
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and "charset" not in content_type:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include WebSocket routes
app.include_router(websocket_router, prefix="/ws")
app.include_router(websocket_router, prefix="/api/v1/ws")  # Unified prefix


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    from app.core.database import check_db_health
    from app.core.cache import cache_manager

    # Check database
    db_health = await check_db_health()

    # Check cache
    cache_health = await cache_manager.health_check()

    healthy = db_health["status"] == "healthy" and cache_health["status"] in ["connected", "active"]

    return {
        "status": "healthy" if healthy else "unhealthy",
        "timestamp": time.time(),
        "services": {
            "database": db_health,
            "cache": cache_health
        }
    }


@app.get("/health/llm", tags=["Health"])
async def health_llm():
    """LLM provider health check"""
    from app.agents.llm_client import LLMClientFactory

    available = settings.available_llm_providers
    default = settings.DEFAULT_AI_PROVIDER

    # Check if default provider is usable (real LLM client constructible without ValueError)
    try:
        LLMClientFactory.create(default if default != "fallback" else "kimi")
        default_usable = True
    except (ValueError, RuntimeError):
        default_usable = False

    return {
        "status": "healthy" if available else "degraded",
        "default_provider": default,
        "default_provider_usable": default_usable,
        "available_providers": available,
        "mock_fallback": False,
    }


# Readiness check endpoint
@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check for Kubernetes"""
    return {"status": "ready"}


# Liveness check endpoint
@app.get("/alive", tags=["Health"])
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
