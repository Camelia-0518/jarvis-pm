"""API v1 router"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, prds, agents, ai, tools, skills, code, evaluation, rag, prd_generator, workflows, battles, websocket

api_router = APIRouter()

# Include all endpoint routers with standardized tags
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(prds.router, prefix="/prds", tags=["PRDs"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(tools.router, prefix="/tools", tags=["Tools"])
api_router.include_router(skills.router, prefix="/skills", tags=["Skills"])
api_router.include_router(code.router, prefix="/code", tags=["Code Generation"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["Evaluation"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG"])
api_router.include_router(prd_generator.router, prefix="/prd-generator", tags=["PRD Generator"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(battles.router, prefix="/battles", tags=["Battles"])
api_router.include_router(websocket.router, tags=["WebSocket"])
