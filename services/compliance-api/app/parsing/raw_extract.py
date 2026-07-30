from pathlib import Path

import pdfplumber
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_repo_root
from app.models import Drawing, DrawingText


def _resolve_drawing_path(drawing: Drawing) -> Path:
    file_path = Path(drawing.file_path)
    if file_path.is_absolute():
        return file_path
    return get_repo_root() / file_path


def extract_text(drawing_id: int, db: Session) -> int:
    """Extract raw text from a stored drawing PDF, page by page."""
    drawing = db.get(Drawing, drawing_id)
    if drawing is None:
        raise ValueError(f"Drawing {drawing_id} not found")

    pdf_path = _resolve_drawing_path(drawing)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Drawing PDF not found at {pdf_path}")

    db.execute(delete(DrawingText).where(DrawingText.drawing_id == drawing_id))

    pages_processed = 0
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            db.add(
                DrawingText(
                    drawing_id=drawing_id,
                    page_number=page_number,
                    raw_text=raw_text,
                )
            )
            pages_processed += 1

    db.commit()
    return pages_processed
