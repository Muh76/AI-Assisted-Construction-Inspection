from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_repo_root
from app.db import get_db
from app.models import Corridor, Door, Drawing, Room
from app.parsing.corridor_vision import parse_corridor_width_callouts
from app.parsing.door_schedule import extract_door_schedule
from app.parsing.page_image import render_drawing_page
from app.parsing.raw_extract import extract_text
from app.parsing.room_schedule import extract_room_schedule
from app.schemas import (
    CorridorRead,
    CorridorVisionConfirmRequest,
    CorridorVisionConfirmResponse,
    CorridorVisionPreviewResponse,
    CorridorWidthCalloutPreviewRow,
    DoorScheduleConfirmRequest,
    DoorScheduleConfirmResponse,
    DoorSchedulePreviewResponse,
    DoorSchedulePreviewRow,
    DoorRead,
    DrawingExtractResponse,
    DrawingPageRenderResponse,
    DrawingRead,
    RoomScheduleConfirmRequest,
    RoomScheduleConfirmResponse,
    RoomSchedulePreviewResponse,
    RoomSchedulePreviewRow,
    RoomRead,
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


@router.get("/{drawing_id}", response_model=DrawingRead)
def get_drawing(drawing_id: int, db: Session = Depends(get_db)) -> Drawing:
    return _get_drawing_or_404(drawing_id, db)


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
    "/{drawing_id}/pages/{page_number}/render",
    response_model=DrawingPageRenderResponse,
    status_code=status.HTTP_200_OK,
)
def render_drawing_page_image(
    drawing_id: int,
    page_number: int,
    db: Session = Depends(get_db),
) -> DrawingPageRenderResponse:
    _get_drawing_or_404(drawing_id, db)

    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_number must be at least 1",
        )

    try:
        file_path = render_drawing_page(drawing_id, page_number, db)
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

    return DrawingPageRenderResponse(
        drawing_id=drawing_id,
        page_number=page_number,
        file_path=file_path,
    )


@router.get("/{drawing_id}/pages/{page_number}/image")
def get_drawing_page_image(
    drawing_id: int,
    page_number: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    _get_drawing_or_404(drawing_id, db)

    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_number must be at least 1",
        )

    image_path = get_repo_root() / f"data/processed/{drawing_id}/page_{page_number}.png"
    if not image_path.is_file():
        try:
            render_drawing_page(drawing_id, page_number, db)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            message = str(exc)
            status_code = (
                status.HTTP_404_NOT_FOUND
                if "not found" in message
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(status_code=status_code, detail=message) from exc
        image_path = get_repo_root() / f"data/processed/{drawing_id}/page_{page_number}.png"

    if not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rendered page image not found for drawing {drawing_id} page {page_number}",
        )

    return FileResponse(image_path, media_type="image/png")


@router.post(
    "/{drawing_id}/pages/{page_number}/parse-corridors/confirm",
    response_model=CorridorVisionConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_parsed_corridor_widths(
    drawing_id: int,
    page_number: int,
    payload: CorridorVisionConfirmRequest,
    db: Session = Depends(get_db),
) -> CorridorVisionConfirmResponse:
    drawing = _get_drawing_or_404(drawing_id, db)
    created_corridors: list[Corridor] = []

    for row in payload.callouts:
        corridor = Corridor(
            project_id=drawing.project_id,
            clear_width=row.width_mm,
            length=row.length,
        )
        db.add(corridor)
        created_corridors.append(corridor)

    db.commit()
    for corridor in created_corridors:
        db.refresh(corridor)

    return CorridorVisionConfirmResponse(
        drawing_id=drawing_id,
        page_number=page_number,
        created=[CorridorRead.model_validate(corridor) for corridor in created_corridors],
    )


@router.post(
    "/{drawing_id}/pages/{page_number}/parse-corridors",
    response_model=CorridorVisionPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_parsed_corridor_widths(
    drawing_id: int,
    page_number: int,
    db: Session = Depends(get_db),
) -> CorridorVisionPreviewResponse:
    _get_drawing_or_404(drawing_id, db)

    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_number must be at least 1",
        )

    try:
        image_path, callouts = parse_corridor_width_callouts(
            drawing_id,
            page_number,
            db,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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

    return CorridorVisionPreviewResponse(
        drawing_id=drawing_id,
        page_number=page_number,
        preview=True,
        image_path=image_path,
        callouts=[
            CorridorWidthCalloutPreviewRow.model_validate(callout)
            for callout in callouts
        ],
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


@router.post(
    "/{drawing_id}/parse-rooms/confirm",
    response_model=RoomScheduleConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_parsed_rooms(
    drawing_id: int,
    payload: RoomScheduleConfirmRequest,
    db: Session = Depends(get_db),
) -> RoomScheduleConfirmResponse:
    drawing = _get_drawing_or_404(drawing_id, db)
    created_rooms: list[Room] = []

    for row in payload.rows:
        room = Room(
            project_id=drawing.project_id,
            name=row.name,
            occupancy_category=row.occupancy_category,
            floor_area=row.floor_area,
            occupant_load=row.occupant_load,
        )
        db.add(room)
        created_rooms.append(room)

    db.commit()
    for room in created_rooms:
        db.refresh(room)

    return RoomScheduleConfirmResponse(
        drawing_id=drawing_id,
        created=[RoomRead.model_validate(room) for room in created_rooms],
    )


@router.post(
    "/{drawing_id}/parse-rooms",
    response_model=RoomSchedulePreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_parsed_rooms(
    drawing_id: int,
    page_number: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> RoomSchedulePreviewResponse:
    _get_drawing_or_404(drawing_id, db)

    try:
        rows = extract_room_schedule(drawing_id, page_number, db)
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

    return RoomSchedulePreviewResponse(
        drawing_id=drawing_id,
        page_number=page_number,
        preview=True,
        rows=[RoomSchedulePreviewRow.model_validate(row) for row in rows],
    )
