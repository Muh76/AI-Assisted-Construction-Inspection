from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Door, Project, Room, User
from app.schemas import DoorCreate, DoorRead
from app.services.ownership import get_owned_door, get_owned_room

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=DoorRead, status_code=status.HTTP_201_CREATED)
def create_door(payload: DoorCreate, db: Session = Depends(get_db)) -> Door:
    room = db.get(Room, payload.room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    door = Door(**payload.model_dump())
    db.add(door)
    db.commit()
    db.refresh(door)
    return door


@router.get("", response_model=list[DoorRead])
def list_doors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Door]:
    return list(
        db.scalars(
            select(Door)
            .join(Room)
            .join(Project)
            .where(Project.owner_id == current_user.id)
        ).all()
    )


@router.get("/{door_id}", response_model=DoorRead)
def get_door(
    door_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Door:
    return get_owned_door(db, door_id, current_user)


@router.put("/{door_id}", response_model=DoorRead)
def update_door(
    door_id: int,
    payload: DoorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Door:
    door = get_owned_door(db, door_id, current_user)
    get_owned_room(db, payload.room_id, current_user)

    for field, value in payload.model_dump().items():
        setattr(door, field, value)

    db.commit()
    db.refresh(door)
    return door


@router.delete("/{door_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_door(
    door_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    door = get_owned_door(db, door_id, current_user)
    db.delete(door)
    db.commit()
