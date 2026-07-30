from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Corridor, Project, User
from app.schemas import CorridorCreate, CorridorRead
from app.services.ownership import get_owned_corridor, get_owned_project

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=CorridorRead, status_code=status.HTTP_201_CREATED)
def create_corridor(payload: CorridorCreate, db: Session = Depends(get_db)) -> Corridor:
    corridor = Corridor(**payload.model_dump())
    db.add(corridor)
    db.commit()
    db.refresh(corridor)
    return corridor


@router.get("", response_model=list[CorridorRead])
def list_corridors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Corridor]:
    return list(
        db.scalars(
            select(Corridor).join(Project).where(Project.owner_id == current_user.id)
        ).all()
    )


@router.get("/{corridor_id}", response_model=CorridorRead)
def get_corridor(
    corridor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Corridor:
    return get_owned_corridor(db, corridor_id, current_user)


@router.put("/{corridor_id}", response_model=CorridorRead)
def update_corridor(
    corridor_id: int,
    payload: CorridorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Corridor:
    corridor = get_owned_corridor(db, corridor_id, current_user)
    get_owned_project(db, payload.project_id, current_user)

    for field, value in payload.model_dump().items():
        setattr(corridor, field, value)

    db.commit()
    db.refresh(corridor)
    return corridor


@router.delete("/{corridor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_corridor(
    corridor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    corridor = get_owned_corridor(db, corridor_id, current_user)
    db.delete(corridor)
    db.commit()
