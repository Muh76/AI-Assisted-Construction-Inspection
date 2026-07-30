from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Corridor
from app.schemas import CorridorCreate, CorridorRead

router = APIRouter()


@router.post("", response_model=CorridorRead, status_code=status.HTTP_201_CREATED)
def create_corridor(payload: CorridorCreate, db: Session = Depends(get_db)) -> Corridor:
    corridor = Corridor(**payload.model_dump())
    db.add(corridor)
    db.commit()
    db.refresh(corridor)
    return corridor


@router.get("", response_model=list[CorridorRead])
def list_corridors(db: Session = Depends(get_db)) -> list[Corridor]:
    return list(db.scalars(select(Corridor)).all())


@router.get("/{corridor_id}", response_model=CorridorRead)
def get_corridor(corridor_id: int, db: Session = Depends(get_db)) -> Corridor:
    corridor = db.get(Corridor, corridor_id)
    if corridor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corridor not found")
    return corridor


@router.put("/{corridor_id}", response_model=CorridorRead)
def update_corridor(
    corridor_id: int,
    payload: CorridorCreate,
    db: Session = Depends(get_db),
) -> Corridor:
    corridor = db.get(Corridor, corridor_id)
    if corridor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corridor not found")

    for field, value in payload.model_dump().items():
        setattr(corridor, field, value)

    db.commit()
    db.refresh(corridor)
    return corridor


@router.delete("/{corridor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_corridor(corridor_id: int, db: Session = Depends(get_db)) -> None:
    corridor = db.get(Corridor, corridor_id)
    if corridor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corridor not found")

    db.delete(corridor)
    db.commit()
