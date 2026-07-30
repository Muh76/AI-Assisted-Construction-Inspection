from fastapi import APIRouter

from app.routers import corridors, doors, projects, rooms

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(doors.router, prefix="/doors", tags=["doors"])
api_router.include_router(corridors.router, prefix="/corridors", tags=["corridors"])
