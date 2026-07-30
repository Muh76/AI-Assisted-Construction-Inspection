from pathlib import Path

import pdfplumber
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_repo_root
from app.models import RegulationDocument, RegulationText


def _resolve_document_path(document: RegulationDocument) -> Path:
    file_path = Path(document.file_path)
    if file_path.is_absolute():
        return file_path
    return get_repo_root() / file_path


def extract_regulation_pages(
    document_id: int,
    start_page: int,
    end_page: int,
    db: Session,
) -> int:
    """Extract raw text from a page range in a stored regulation PDF."""
    if start_page < 1:
        raise ValueError("start_page must be at least 1")
    if end_page < start_page:
        raise ValueError("end_page must be greater than or equal to start_page")

    document = db.get(RegulationDocument, document_id)
    if document is None:
        raise ValueError(f"Regulation document {document_id} not found")

    pdf_path = _resolve_document_path(document)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Regulation PDF not found at {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if end_page > total_pages:
            raise ValueError(
                f"end_page {end_page} exceeds document page count ({total_pages})"
            )

        db.execute(
            delete(RegulationText).where(
                RegulationText.document_id == document_id,
                RegulationText.page_number >= start_page,
                RegulationText.page_number <= end_page,
            )
        )

        pages_processed = 0
        for page_number in range(start_page, end_page + 1):
            page = pdf.pages[page_number - 1]
            raw_text = page.extract_text() or ""
            db.add(
                RegulationText(
                    document_id=document_id,
                    page_number=page_number,
                    raw_text=raw_text,
                )
            )
            pages_processed += 1

    db.commit()
    return pages_processed
