from fastapi import APIRouter

from app.routers import corridors, doors, fire_protection_items, projects, rooms

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(doors.router, prefix="/doors", tags=["doors"])
api_router.include_router(corridors.router, prefix="/corridors", tags=["corridors"])
api_router.include_router(
    fire_protection_items.router,
    prefix="/fire-protection-items",
    tags=["fire-protection-items"],
)
