"""FastAPI application main entry point"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.database import init_db, close_db, create_indexes
from app.core.cache import init_cache, close_cache
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging, audit
from app.api.v1.router import api_router
from app.api.v1.endpoints.rag import retrieval_engine
from app.rag.knowledge_loader import load_obsidian_documents, ObsidianWatcher


# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting up...")

    # Validate LLM configuration
    available = settings.available_llm_providers
    if not available:
        logging.error(
            "[CRITICAL] No real LLM provider API keys are configured. "
            "Jarvis PM requires a real AI provider to function. "
            "Set KIMI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in your .env file."
        )
    else:
        logging.info("Available LLM providers: %s", ", ".join(available))
        try:
            from app.agents.llm_client import LLMClientFactory
            test_client = LLMClientFactory.create(settings.DEFAULT_AI_PROVIDER)
            logging.info("Default LLM client (%s) initialized successfully", settings.DEFAULT_AI_PROVIDER)
        except Exception as e:
            logging.error("Failed to initialize default LLM client: %s", e)

    # Single-user mode safety warning
    if settings.SINGLE_USER_MODE:
        logging.warning(
            "[SECURITY] SINGLE_USER_MODE is enabled. All requests without "
            "authentication will be treated as 'single-user'. "
            "This should NEVER be used in production (DEBUG=false)."
        )
        if not settings.DEBUG:
            logging.error(
                "[CRITICAL] SINGLE_USER_MODE is enabled with DEBUG=false. "
                "This is a security risk. Disable SINGLE_USER_MODE for production."
            )

    # Initialize cache
    await init_cache()

    # Initialize database
    await init_db()

    # Create indexes
    await create_indexes()

    # Load Obsidian knowledge base into RAG engine
    vault_watcher = None
    loaded_docs = load_obsidian_documents(retrieval_engine)
    if loaded_docs:
        logging.info("RAG engine loaded with %d documents.", loaded_docs)
        vault_watcher = ObsidianWatcher(retrieval_engine)
        if vault_watcher.start():
            logging.info("Vault watcher started for hot reload")

    logger.info("✅ Application started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")

    if vault_watcher:
        vault_watcher.stop()

    # Close cache
    await close_cache()

    # Close database
    await close_db()

    logger.info("✅ Application shutdown complete")


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

# 1. Trusted Host Middleware — skipped in DEBUG mode to avoid Starlette
#    rejecting wildcard host checks (e.g. TestClient requests)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "*.jarvis-pm.com"]
    )

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
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


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing. Reuses client-provided ID if present."""
    import uuid
    client_request_id = request.headers.get("X-Request-ID")
    request_id = client_request_id or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Include API router
app.include_router(api_router, prefix="/api/v1")


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

    # Check if default provider is usable (real AI only)
    try:
        client = LLMClientFactory.create(default if default != "fallback" else "kimi")
        default_usable = True
    except ValueError as e:
        default_usable = False
        init_error = str(e)
    except Exception as e:
        default_usable = False
        init_error = str(e)
    else:
        init_error = None

    return {
        "status": "healthy" if (available and default_usable) else "degraded",
        "default_provider": default,
        "default_provider_usable": default_usable,
        "available_providers": available,
        "init_error": init_error,
        "real_ai_only": True,
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
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
