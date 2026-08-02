from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import get_data_regulations_dir
from app.db import get_db
from app.models import RegulationClause, RegulationDocument, RegulationText
from app.parsing.clause_extract import extract_candidate_clauses
from app.parsing.regulation_text import extract_regulation_pages
from app.schemas import (
    RegulationClauseConfirmRequest,
    RegulationClauseConfirmResponse,
    RegulationClausePreviewResponse,
    RegulationClausePreviewRow,
    RegulationClauseRead,
    RegulationDocumentRead,
    RegulationExtractResponse,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _safe_filename_part(value: str) -> str:
    sanitized = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in value.strip()
    )
    return sanitized or "document"


def _get_document_or_404(document_id: int, db: Session) -> RegulationDocument:
    document = db.get(RegulationDocument, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulation document not found",
        )
    return document


def _title_and_description(text: str) -> tuple[str, str]:
    stripped = text.strip()
    if not stripped:
        return "", ""

    first_line = stripped.splitlines()[0].strip()
    return first_line, stripped


def _get_document_text_pages(
    document_id: int,
    db: Session,
) -> list[RegulationText]:
    return list(
        db.scalars(
            select(RegulationText)
            .where(RegulationText.document_id == document_id)
            .order_by(RegulationText.page_number)
        ).all()
    )


@router.post(
    "/documents",
    response_model=RegulationDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_regulation_document(
    file: UploadFile = File(...),
    code: str = Form(...),
    edition: str = Form(...),
    db: Session = Depends(get_db),
) -> RegulationDocument:
    filename = file.filename or ""
    is_pdf = (
        file.content_type in {"application/pdf", "application/x-pdf"}
        or filename.lower().endswith(".pdf")
    )
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    uploaded_at = datetime.now(UTC).replace(tzinfo=None)
    timestamp = uploaded_at.strftime("%Y%m%d_%H%M%S")
    saved_filename = (
        f"{_safe_filename_part(code)}-{_safe_filename_part(edition)}-{timestamp}.pdf"
    )

    regulations_dir = get_data_regulations_dir()
    regulations_dir.mkdir(parents=True, exist_ok=True)
    destination = regulations_dir / saved_filename
    destination.write_bytes(await file.read())

    document = RegulationDocument(
        code=code,
        edition=edition,
        file_path=f"data/regulations/{saved_filename}",
        uploaded_at=uploaded_at,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents", response_model=list[RegulationDocumentRead])
def list_regulation_documents(
    db: Session = Depends(get_db),
) -> list[RegulationDocument]:
    return list(
        db.scalars(
            select(RegulationDocument).order_by(RegulationDocument.uploaded_at.desc())
        ).all()
    )


@router.post(
    "/documents/{document_id}/extract",
    response_model=RegulationExtractResponse,
    status_code=status.HTTP_200_OK,
)
def extract_regulation_document_text(
    document_id: int,
    start: int = Query(..., ge=1),
    end: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> RegulationExtractResponse:
    _get_document_or_404(document_id, db)

    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end must be greater than or equal to start",
        )

    try:
        pages_processed = extract_regulation_pages(document_id, start, end, db)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if "not found" in message:
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc

    return RegulationExtractResponse(
        document_id=document_id,
        start_page=start,
        end_page=end,
        pages_processed=pages_processed,
    )


@router.post(
    "/documents/{document_id}/parse-clauses/confirm",
    response_model=RegulationClauseConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_parsed_clauses(
    document_id: int,
    payload: RegulationClauseConfirmRequest,
    db: Session = Depends(get_db),
) -> RegulationClauseConfirmResponse:
    document = _get_document_or_404(document_id, db)
    created: list[RegulationClause] = []
    updated: list[RegulationClause] = []

    for row in payload.clauses:
        title, description = _title_and_description(row.text)
        existing = db.scalar(
            select(RegulationClause).where(
                RegulationClause.code == document.code,
                RegulationClause.section == row.section,
            )
        )
        if existing is None:
            clause = RegulationClause(
                code=document.code,
                section=row.section,
                title=title,
                description=description,
                threshold_value=row.threshold_value,
                threshold_unit=row.threshold_unit,
            )
            db.add(clause)
            created.append(clause)
            continue

        existing.title = title
        existing.description = description
        existing.threshold_value = row.threshold_value
        existing.threshold_unit = row.threshold_unit
        updated.append(existing)

    db.commit()
    for clause in created + updated:
        db.refresh(clause)

    return RegulationClauseConfirmResponse(
        document_id=document_id,
        created=[RegulationClauseRead.model_validate(clause) for clause in created],
        updated=[RegulationClauseRead.model_validate(clause) for clause in updated],
    )


@router.post(
    "/documents/{document_id}/parse-clauses",
    response_model=RegulationClausePreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_parsed_clauses(
    document_id: int,
    db: Session = Depends(get_db),
) -> RegulationClausePreviewResponse:
    _get_document_or_404(document_id, db)
    text_pages = _get_document_text_pages(document_id, db)
    candidates = extract_candidate_clauses(text_pages)

    return RegulationClausePreviewResponse(
        document_id=document_id,
        preview=True,
        clauses=[RegulationClausePreviewRow.model_validate(clause) for clause in candidates],
    )
