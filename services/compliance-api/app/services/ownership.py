from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Corridor, Door, Exit, Project, Room, User


def get_owned_project(db: Session, project_id: int, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_owned_room(db: Session, room_id: int, user: User) -> Room:
    room = db.scalar(
        select(Room)
        .join(Project)
        .where(Room.id == room_id, Project.owner_id == user.id)
    )
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


def get_owned_door(db: Session, door_id: int, user: User) -> Door:
    door = db.scalar(
        select(Door)
        .join(Room)
        .join(Project)
        .where(Door.id == door_id, Project.owner_id == user.id)
    )
    if door is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Door not found")
    return door


def get_owned_corridor(db: Session, corridor_id: int, user: User) -> Corridor:
    corridor = db.scalar(
        select(Corridor)
        .join(Project)
        .where(Corridor.id == corridor_id, Project.owner_id == user.id)
    )
    if corridor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corridor not found")
    return corridor


def get_owned_exit(db: Session, exit_id: int, user: User) -> Exit:
    exit_ = db.scalar(
        select(Exit)
        .join(Project)
        .where(Exit.id == exit_id, Project.owner_id == user.id)
    )
    if exit_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit not found")
    return exit_
