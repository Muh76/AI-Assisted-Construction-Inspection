from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import get_data_regulations_dir
from app.db import get_db
from app.models import RegulationDocument
from app.parsing.regulation_text import extract_regulation_pages
from app.schemas import RegulationDocumentRead, RegulationExtractResponse

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
