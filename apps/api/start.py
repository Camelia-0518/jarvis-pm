#!/usr/bin/env python3
"""
Startup script for Jarvis PM API
Handles environment setup and server start
"""

import asyncio
import os
import sys

# Windows event loop: ProactorEventLoop (default in Python 3.8+) is required for
# StreamingResponse to work correctly with concurrent httpx async I/O.
# SelectorEventLoop causes SSE data to hang and never flush to the client.

import subprocess
import time
from pathlib import Path

from app.core.config import settings

def check_venv():
    """Check if running in virtual environment"""
    return getattr(sys, 'base_prefix', sys.prefix) != sys.prefix

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

# Database (SQLite for local dev, PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./jarvis_pm.db
DATABASE_URL_SYNC=sqlite:///./jarvis_pm.db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI/LLM - DeepSeek (default, recommended for PRD generation)
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4-flash
DEFAULT_AI_PROVIDER=deepseek

# AI/LLM - Kimi (alternative)
KIMI_API_KEY=your-kimi-api-key
KIMI_BASE_URL=https://api.kimi.com/coding/
KIMI_MODEL=k2.6-code-preview

# AI/LLM - Anthropic (alternative)
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# AI/LLM - OpenAI (alternative)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4

# App
DEBUG=True
HOST=0.0.0.0
PORT=8000
SINGLE_USER_MODE=False
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

def _find_pids_on_port(port: int) -> set:
    """Find all PIDs listening on the given port."""
    pids = set()
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, shell=False, check=False,
            encoding="utf-8", errors="replace"
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
    except Exception as e:
        print(f"[WARN] Could not scan port {port}: {e}")
    return pids


def _kill_pids(pids: set, label: str = "") -> int:
    """Kill given PIDs with taskkill /T /F. Returns count of killed."""
    killed = 0
    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, shell=False, check=False
            )
            killed += 1
        except Exception as e:
            print(f"[WARN] Failed to kill PID {pid}: {e}")
    if label and killed:
        print(f"[INFO] {label}: killed {killed} process(es)")
    return killed


def _kill_zombie_python_in_project() -> int:
    """Kill all python.exe/uvicorn processes whose command line references this project."""
    killed = 0
    project_root = Path(__file__).resolve().parent
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "processid,commandline"],
            capture_output=True, text=True, shell=False, check=False,
            encoding="utf-8", errors="replace"
        )
        for line in result.stdout.splitlines():
            if "jarvis-pm" in line or "uvicorn" in line.lower():
                parts = line.strip().split()
                if parts:
                    try:
                        pid = int(parts[-1])
                        subprocess.run(
                            ["taskkill", "/PID", str(pid), "/T", "/F"],
                            capture_output=True, shell=False, check=False
                        )
                        killed += 1
                    except (ValueError, IndexError):
                        pass
    except Exception:
        pass
    return killed


def kill_port_processes(port: int):
    """Force kill any process listening on the given port. Windows-only robust version.
    Three-tier strategy: (1) kill PIDs on port, (2) retry, (3) kill all project Python processes."""
    print(f"[INFO] Cleaning up port {port}...")

    pids = _find_pids_on_port(port)
    if not pids:
        print(f"[OK] Port {port} is already free")
        return

    print(f"[INFO] Found processes on port {port}: {pids}")

    # Pass 1: kill PIDs on port
    _kill_pids(pids, "Pass 1")
    time.sleep(1)

    # Pass 2: re-scan and kill whatever is still on the port
    retry_pids = _find_pids_on_port(port)
    if retry_pids:
        print(f"[WARN] Port {port} still occupied, retrying...")
        _kill_pids(retry_pids, "Pass 2")
        time.sleep(1.5)

    # Pass 3: if port still occupied, kill ALL Python processes in this project
    still_there = _find_pids_on_port(port)
    if still_there:
        print(f"[WARN] Port {port} still occupied after two passes. Sweeping zombie Python processes...")
        killed = _kill_zombie_python_in_project()
        if killed:
            print(f"[INFO] Killed {killed} zombie Python process(es)")
        time.sleep(2)

        # Final check
        final_check = _find_pids_on_port(port)
        if final_check:
            print(f"[ERROR] Port {port} could not be freed. Remaining PIDs: {final_check}")
            print(f"[ERROR] Manual fix: netstat -ano | findstr :{port}")
            print(f"[ERROR] Then: taskkill /PID <PID> /F")
            sys.exit(1)
        else:
            print(f"[OK] Port {port} freed after zombie sweep")

    print(f"[OK] Port {port} freed successfully")

def start_server():
    """Start the FastAPI server"""
    import uvicorn
    print("\n[START] Starting Jarvis PM API...")
    print("[INFO] API Documentation: http://localhost:8000/docs")
    print("[INFO] Health Check: http://localhost:8000/health\n")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
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

    # Clean up port before starting
    kill_port_processes(settings.PORT)

    # Start server
    start_server()

if __name__ == "__main__":
    main()
