from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Door, Room
from app.schemas import DoorCreate, DoorRead

router = APIRouter()


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
def list_doors(db: Session = Depends(get_db)) -> list[Door]:
    return list(db.scalars(select(Door)).all())


@router.get("/{door_id}", response_model=DoorRead)
def get_door(door_id: int, db: Session = Depends(get_db)) -> Door:
    door = db.get(Door, door_id)
    if door is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Door not found")
    return door


@router.put("/{door_id}", response_model=DoorRead)
def update_door(
    door_id: int,
    payload: DoorCreate,
    db: Session = Depends(get_db),
) -> Door:
    door = db.get(Door, door_id)
    if door is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Door not found")

    room = db.get(Room, payload.room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    for field, value in payload.model_dump().items():
        setattr(door, field, value)

    db.commit()
    db.refresh(door)
    return door


@router.delete("/{door_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_door(door_id: int, db: Session = Depends(get_db)) -> None:
    door = db.get(Door, door_id)
    if door is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Door not found")

    db.delete(door)
    db.commit()
