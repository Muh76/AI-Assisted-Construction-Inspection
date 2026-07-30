from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import FireProtectionItem, Project
from app.schemas import FireProtectionItemCreate, FireProtectionItemRead

router = APIRouter()


@router.post("", response_model=FireProtectionItemRead, status_code=status.HTTP_201_CREATED)
def create_fire_protection_item(
    payload: FireProtectionItemCreate,
    db: Session = Depends(get_db),
) -> FireProtectionItem:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    item = FireProtectionItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[FireProtectionItemRead])
def list_fire_protection_items(
    db: Session = Depends(get_db),
) -> list[FireProtectionItem]:
    return list(db.scalars(select(FireProtectionItem)).all())


@router.get("/{item_id}", response_model=FireProtectionItemRead)
def get_fire_protection_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> FireProtectionItem:
    item = db.get(FireProtectionItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fire protection item not found",
        )
    return item


@router.put("/{item_id}", response_model=FireProtectionItemRead)
def update_fire_protection_item(
    item_id: int,
    payload: FireProtectionItemCreate,
    db: Session = Depends(get_db),
) -> FireProtectionItem:
    item = db.get(FireProtectionItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fire protection item not found",
        )

    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    for field, value in payload.model_dump().items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fire_protection_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> None:
    item = db.get(FireProtectionItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fire protection item not found",
        )

    db.delete(item)
    db.commit()
