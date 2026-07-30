from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RegulationClause
from app.schemas import RegulationClauseCreate, RegulationClauseRead

router = APIRouter()


@router.post("", response_model=RegulationClauseRead, status_code=status.HTTP_201_CREATED)
def create_regulation_clause(
    payload: RegulationClauseCreate,
    db: Session = Depends(get_db),
) -> RegulationClause:
    clause = RegulationClause(**payload.model_dump())
    db.add(clause)
    db.commit()
    db.refresh(clause)
    return clause


@router.get("", response_model=list[RegulationClauseRead])
def list_regulation_clauses(db: Session = Depends(get_db)) -> list[RegulationClause]:
    return list(db.scalars(select(RegulationClause)).all())


@router.get("/{clause_id}", response_model=RegulationClauseRead)
def get_regulation_clause(
    clause_id: int,
    db: Session = Depends(get_db),
) -> RegulationClause:
    clause = db.get(RegulationClause, clause_id)
    if clause is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulation clause not found",
        )
    return clause


@router.put("/{clause_id}", response_model=RegulationClauseRead)
def update_regulation_clause(
    clause_id: int,
    payload: RegulationClauseCreate,
    db: Session = Depends(get_db),
) -> RegulationClause:
    clause = db.get(RegulationClause, clause_id)
    if clause is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulation clause not found",
        )

    for field, value in payload.model_dump().items():
        setattr(clause, field, value)

    db.commit()
    db.refresh(clause)
    return clause


@router.delete("/{clause_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_regulation_clause(clause_id: int, db: Session = Depends(get_db)) -> None:
    clause = db.get(RegulationClause, clause_id)
    if clause is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulation clause not found",
        )

    db.delete(clause)
    db.commit()
