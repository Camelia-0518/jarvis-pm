#!/usr/bin/env python3
"""
Startup script for Jarvis PM API
Handles environment setup and server start
"""

import os
import sys
import subprocess
from pathlib import Path

def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    return in_venv

def setup_env():
    """Setup environment variables"""
    env_file = Path('.env')
    if env_file.exists():
        print("[OK] Found .env file")
    else:
        print("[WARN] No .env file found, creating from template...")
        create_env_template()

def create_env_template():
    """Create .env template file"""
    template = """# Jarvis PM API Configuration

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jarvis_pm
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/jarvis_pm

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI/LLM (Required for PRD generation)
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
DEFAULT_AI_MODEL=claude-3-5-sonnet-20241022

# App
DEBUG=True
HOST=0.0.0.0
PORT=8000
"""
    with open('.env', 'w') as f:
        f.write(template)
    print("[OK] Created .env template - please update with your API keys")

def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import fastapi
        import sqlalchemy
        import anthropic
        print("[OK] Dependencies installed")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def start_server():
    """Start the FastAPI server"""
    import uvicorn
    print("\n[START] Starting Jarvis PM API...")
    print("[INFO] API Documentation: http://localhost:8000/docs")
    print("[INFO] Health Check: http://localhost:8000/health\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

def main():
    """Main entry point"""
    print("="*50)
    print("Jarvis PM API Startup")
    print("="*50)

    # Check virtual environment
    if not check_venv():
        print("[WARN] Not running in virtual environment")
        print("Recommended: python -m venv venv && source venv/bin/activate")

    # Setup environment
    setup_env()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Start server
    start_server()

if __name__ == "__main__":
    main()
