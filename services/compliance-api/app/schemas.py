from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import DrawingType, FireProtectionItemType


class ProjectCreate(BaseModel):
    name: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int


class DrawingCreate(BaseModel):
    project_id: int
    type: DrawingType
    file_path: str
    upload_date: datetime


class DrawingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    type: DrawingType
    file_path: str
    upload_date: datetime


class DrawingExtractResponse(BaseModel):
    drawing_id: int
    pages_processed: int


class DrawingPageRenderResponse(BaseModel):
    drawing_id: int
    page_number: int
    file_path: str


class CorridorWidthCalloutPreviewRow(BaseModel):
    label: str
    width_mm: float
    approximate_location: str


class CorridorVisionPreviewResponse(BaseModel):
    drawing_id: int
    page_number: int
    preview: bool = True
    image_path: str
    callouts: list[CorridorWidthCalloutPreviewRow]


class CorridorVisionConfirmRow(BaseModel):
    label: str
    width_mm: float
    approximate_location: str
    length: float


class CorridorVisionConfirmRequest(BaseModel):
    callouts: list[CorridorVisionConfirmRow]


class DoorSchedulePreviewRow(BaseModel):
    door_number: str
    width: float
    fire_rating: str | None = None


class DoorSchedulePreviewResponse(BaseModel):
    drawing_id: int
    page_number: int
    preview: bool = True
    rows: list[DoorSchedulePreviewRow]


class DoorScheduleConfirmRow(BaseModel):
    door_number: str
    width: float
    fire_rating: str | None = None
    room_id: int


class DoorScheduleConfirmRequest(BaseModel):
    rows: list[DoorScheduleConfirmRow]


class RoomCreate(BaseModel):
    project_id: int
    name: str
    occupancy_category: str
    floor_area: float
    occupant_load: int


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    occupancy_category: str
    floor_area: float
    occupant_load: int


class DoorCreate(BaseModel):
    room_id: int
    clear_width: float
    fire_rating: str | None = None


class DoorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    clear_width: float
    fire_rating: str | None


class DoorScheduleConfirmResponse(BaseModel):
    drawing_id: int
    created: list[DoorRead]


class RoomSchedulePreviewRow(BaseModel):
    name: str
    occupancy_category: str
    floor_area: float
    occupant_load: int


class RoomSchedulePreviewResponse(BaseModel):
    drawing_id: int
    page_number: int
    preview: bool = True
    rows: list[RoomSchedulePreviewRow]


class RoomScheduleConfirmRow(BaseModel):
    name: str
    occupancy_category: str
    floor_area: float
    occupant_load: int


class RoomScheduleConfirmRequest(BaseModel):
    rows: list[RoomScheduleConfirmRow]


class RoomScheduleConfirmResponse(BaseModel):
    drawing_id: int
    created: list[RoomRead]


class CorridorCreate(BaseModel):
    project_id: int
    clear_width: float
    length: float


class CorridorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    clear_width: float
    length: float


class CorridorVisionConfirmResponse(BaseModel):
    drawing_id: int
    page_number: int
    created: list[CorridorRead]


class ExitCreate(BaseModel):
    project_id: int
    location: str
    clear_width: float
    is_required_exit: bool = False


class ExitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    location: str
    clear_width: float
    is_required_exit: bool


class FireProtectionItemCreate(BaseModel):
    project_id: int
    item_type: FireProtectionItemType
    location: str
    rating_required: str | None = None
    rating_provided: str | None = None
    travel_distance_to_nearest: float | None = None


class FireProtectionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    item_type: FireProtectionItemType
    location: str
    rating_required: str | None
    rating_provided: str | None
    travel_distance_to_nearest: float | None


class RegulationClauseCreate(BaseModel):
    code: str
    section: str
    title: str
    description: str
    threshold_value: float | None = None
    threshold_unit: str | None = None


class RegulationClauseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    section: str
    title: str
    description: str
    threshold_value: float | None
    threshold_unit: str | None


class RegulationDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    edition: str
    file_path: str
    uploaded_at: datetime


class RegulationExtractResponse(BaseModel):
    document_id: int
    start_page: int
    end_page: int
    pages_processed: int


class RegulationClausePreviewRow(BaseModel):
    section: str
    text: str
    page_number: int
    is_regulation_clause: bool
    title: str | None = None
    threshold_value: float | None = None
    threshold_unit: str | None = None
    claude_confidence_note: str | None = None


class RegulationClausePreviewResponse(BaseModel):
    document_id: int
    preview: bool = True
    clauses: list[RegulationClausePreviewRow]


class RegulationClauseConfirmRow(BaseModel):
    section: str
    text: str
    threshold_value: float | None = None
    threshold_unit: str | None = None


class RegulationClauseConfirmRequest(BaseModel):
    clauses: list[RegulationClauseConfirmRow]


class RegulationClauseConfirmResponse(BaseModel):
    document_id: int
    created: list[RegulationClauseRead]
    updated: list[RegulationClauseRead]


class RuleResultRead(BaseModel):
    rule_id: str
    passed: bool
    message: str
    evidence: dict[str, Any]
    regulation_clause_id: int | None = None
    regulation_citation: str | None = None


class ComplianceSummary(BaseModel):
    passed: int
    failed: int


class ComplianceReport(BaseModel):
    project_id: int
    generated_at: datetime
    results: list[RuleResultRead]
    summary: ComplianceSummary


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
