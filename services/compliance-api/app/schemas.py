from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import DrawingType


class ProjectCreate(BaseModel):
    name: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


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


class RuleResultRead(BaseModel):
    rule_id: str
    passed: bool
    message: str
    evidence: dict[str, Any]


class ComplianceSummary(BaseModel):
    passed: int
    failed: int


class ComplianceReport(BaseModel):
    project_id: int
    generated_at: datetime
    results: list[RuleResultRead]
    summary: ComplianceSummary
