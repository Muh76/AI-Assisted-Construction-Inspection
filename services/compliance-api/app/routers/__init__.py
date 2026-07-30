from fastapi import APIRouter

from app.routers import auth, corridors, doors, drawings, exits, fire_protection_items, projects, regulation_clauses, rooms

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(drawings.router, prefix="/drawings", tags=["drawings"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(doors.router, prefix="/doors", tags=["doors"])
api_router.include_router(corridors.router, prefix="/corridors", tags=["corridors"])
api_router.include_router(exits.router, prefix="/exits", tags=["exits"])
api_router.include_router(
    fire_protection_items.router,
    prefix="/fire-protection-items",
    tags=["fire-protection-items"],
)
api_router.include_router(
    regulation_clauses.router,
    prefix="/regulation-clauses",
    tags=["regulation-clauses"],
)
