from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Door, Drawing, Room
from app.parsing.door_schedule import extract_door_schedule
from app.parsing.raw_extract import extract_text
from app.schemas import (
    DoorScheduleConfirmRequest,
    DoorScheduleConfirmResponse,
    DoorSchedulePreviewResponse,
    DoorSchedulePreviewRow,
    DoorRead,
    DrawingExtractResponse,
)

router = APIRouter()


def _get_drawing_or_404(drawing_id: int, db: Session) -> Drawing:
    drawing = db.get(Drawing, drawing_id)
    if drawing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing not found",
        )
    return drawing


@router.post(
    "/{drawing_id}/extract",
    response_model=DrawingExtractResponse,
    status_code=status.HTTP_200_OK,
)
def extract_drawing_text(
    drawing_id: int,
    db: Session = Depends(get_db),
) -> DrawingExtractResponse:
    _get_drawing_or_404(drawing_id, db)

    try:
        pages_processed = extract_text(drawing_id, db)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return DrawingExtractResponse(
        drawing_id=drawing_id,
        pages_processed=pages_processed,
    )


@router.post(
    "/{drawing_id}/parse-doors/confirm",
    response_model=DoorScheduleConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_parsed_doors(
    drawing_id: int,
    payload: DoorScheduleConfirmRequest,
    db: Session = Depends(get_db),
) -> DoorScheduleConfirmResponse:
    drawing = _get_drawing_or_404(drawing_id, db)
    created_doors: list[Door] = []

    for row in payload.rows:
        room = db.get(Room, row.room_id)
        if room is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room {row.room_id} not found",
            )
        if room.project_id != drawing.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Room {row.room_id} does not belong to the same project "
                    f"as drawing {drawing_id}"
                ),
            )

        door = Door(
            room_id=row.room_id,
            clear_width=row.width,
            fire_rating=row.fire_rating,
        )
        db.add(door)
        created_doors.append(door)

    db.commit()
    for door in created_doors:
        db.refresh(door)

    return DoorScheduleConfirmResponse(
        drawing_id=drawing_id,
        created=[DoorRead.model_validate(door) for door in created_doors],
    )


@router.post(
    "/{drawing_id}/parse-doors",
    response_model=DoorSchedulePreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_parsed_doors(
    drawing_id: int,
    page_number: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> DoorSchedulePreviewResponse:
    _get_drawing_or_404(drawing_id, db)

    try:
        rows = extract_door_schedule(drawing_id, page_number, db)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return DoorSchedulePreviewResponse(
        drawing_id=drawing_id,
        page_number=page_number,
        preview=True,
        rows=[DoorSchedulePreviewRow.model_validate(row) for row in rows],
    )
