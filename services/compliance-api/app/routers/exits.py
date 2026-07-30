from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Exit, Project, User
from app.schemas import ExitCreate, ExitRead
from app.services.ownership import get_owned_exit, get_owned_project

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=ExitRead, status_code=status.HTTP_201_CREATED)
def create_exit(payload: ExitCreate, db: Session = Depends(get_db)) -> Exit:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    exit_ = Exit(**payload.model_dump())
    db.add(exit_)
    db.commit()
    db.refresh(exit_)
    return exit_


@router.get("", response_model=list[ExitRead])
def list_exits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Exit]:
    return list(
        db.scalars(
            select(Exit).join(Project).where(Project.owner_id == current_user.id)
        ).all()
    )


@router.get("/{exit_id}", response_model=ExitRead)
def get_exit(
    exit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Exit:
    return get_owned_exit(db, exit_id, current_user)


@router.put("/{exit_id}", response_model=ExitRead)
def update_exit(
    exit_id: int,
    payload: ExitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Exit:
    exit_ = get_owned_exit(db, exit_id, current_user)
    get_owned_project(db, payload.project_id, current_user)

    for field, value in payload.model_dump().items():
        setattr(exit_, field, value)

    db.commit()
    db.refresh(exit_)
    return exit_


@router.delete("/{exit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exit(
    exit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    exit_ = get_owned_exit(db, exit_id, current_user)
    db.delete(exit_)
    db.commit()
