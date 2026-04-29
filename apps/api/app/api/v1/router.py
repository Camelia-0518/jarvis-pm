"""API v1 router"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, prds, agents, ai, tools, skills, code, evaluation, rag, prd_generator, workflows, battles, websocket, feedback, annotations, personas, competitors, reviews, requirements, templates, prompts

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
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(annotations.router, prefix="/prds/{prd_id}/annotations", tags=["Annotations"])
api_router.include_router(personas.router, tags=["Personas"])
api_router.include_router(competitors.router, tags=["Competitors"])
api_router.include_router(reviews.router, tags=["Reviews"])
api_router.include_router(requirements.router, tags=["Requirements"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["Prompts"])
