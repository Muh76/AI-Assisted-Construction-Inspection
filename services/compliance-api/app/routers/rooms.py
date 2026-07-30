from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Project, Room, User
from app.schemas import RoomCreate, RoomRead
from app.services.ownership import get_owned_project, get_owned_room

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)) -> Room:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("", response_model=list[RoomRead])
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Room]:
    return list(
        db.scalars(
            select(Room).join(Project).where(Project.owner_id == current_user.id)
        ).all()
    )


@router.get("/{room_id}", response_model=RoomRead)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Room:
    return get_owned_room(db, room_id, current_user)


@router.put("/{room_id}", response_model=RoomRead)
def update_room(
    room_id: int,
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Room:
    room = get_owned_room(db, room_id, current_user)
    get_owned_project(db, payload.project_id, current_user)

    for field, value in payload.model_dump().items():
        setattr(room, field, value)

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    room = get_owned_room(db, room_id, current_user)
    db.delete(room)
    db.commit()
