from fastapi import APIRouter

from app.api.v1.endpoints import health, me, projects, sessions, snippets

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(snippets.router, prefix="/snippets", tags=["snippets"])
