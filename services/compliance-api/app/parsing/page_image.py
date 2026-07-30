from pathlib import Path

import pdfplumber
from pdf2image import convert_from_path
from sqlalchemy.orm import Session

from app.config import get_repo_root
from app.models import Drawing
from app.parsing.raw_extract import _resolve_drawing_path


def _processed_page_path(drawing_id: int, page_number: int) -> tuple[Path, str]:
    relative_path = f"data/processed/{drawing_id}/page_{page_number}.png"
    absolute_path = get_repo_root() / relative_path
    return absolute_path, relative_path


def render_drawing_page(drawing_id: int, page_number: int, db: Session) -> str:
    """Render one stored drawing PDF page to PNG and return the saved relative path."""
    if page_number < 1:
        raise ValueError("page_number must be at least 1")

    drawing = db.get(Drawing, drawing_id)
    if drawing is None:
        raise ValueError(f"Drawing {drawing_id} not found")

    pdf_path = _resolve_drawing_path(drawing)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Drawing PDF not found at {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        if page_number > page_count:
            raise ValueError(
                f"page_number {page_number} exceeds drawing page count ({page_count})"
            )

    images = convert_from_path(
        pdf_path,
        first_page=page_number,
        last_page=page_number,
    )
    if not images:
        raise ValueError(f"Failed to render page {page_number}")

    output_path, relative_path = _processed_page_path(drawing_id, page_number)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(output_path, "PNG")
    return relative_path
