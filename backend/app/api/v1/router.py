from fastapi import APIRouter

from app.api.v1.endpoints import health, me, members, projects, sessions, snippets

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    members.router, prefix="/projects/{project_id}/members", tags=["members"]
)
api_router.include_router(
    sessions.project_scoped_router,
    prefix="/projects/{project_id}/sessions",
    tags=["sessions"],
)
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(snippets.router, prefix="/snippets", tags=["snippets"])
