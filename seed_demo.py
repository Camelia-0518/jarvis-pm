# -*- coding: utf-8 -*-
"""Seed demo data for visible e2e demo"""

import asyncio
import httpx
import json

BASE_API = "http://localhost:8000/api/v1"
AUTH_HEADER = {}

async def seed():
    client = httpx.AsyncClient(timeout=300.0)

    # Use existing project directly
    project_id = "e72fa690-2439-40d6-934e-9da78979251a"
    print(f"Using existing project: {project_id}")

    # Create PRD (this triggers AI generation)
    prd_payload = {
        "project_id": project_id,
        "title": "Wenzhou Slide Lending Platform PRD",
        "template": "medical"
    }
    print("\nCreating PRD, waiting for AI generation...")
    r2 = await client.post(f"{BASE_API}/prds", json=prd_payload, headers=AUTH_HEADER)
    print("Create PRD:", r2.status_code)
    prd = r2.json()
    print(json.dumps(prd, ensure_ascii=False, indent=2)[:3000])
    prd_id = prd["data"]["id"]

    print(f"\n--- SEED COMPLETE ---")
    print(f"Project ID: {project_id}")
    print(f"PRD ID: {prd_id}")
    print(f"PRD URL: http://localhost:3000/prd/{prd_id}")
    print(f"Workspace URL: http://localhost:3000/workspace?id={project_id}")

if __name__ == "__main__":
    asyncio.run(seed())
