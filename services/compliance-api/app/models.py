import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DrawingType(str, enum.Enum):
    ARCHITECTURAL = "architectural"
    MECHANICAL = "mechanical"


class FireProtectionItemType(str, enum.Enum):
    FIRE_EXTINGUISHER = "fire_extinguisher"
    PENETRATION_SEAL = "penetration_seal"
    FIRE_SEPARATION = "fire_separation"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="projects")
    drawings: Mapped[list["Drawing"]] = relationship(back_populates="project")
    rooms: Mapped[list["Room"]] = relationship(back_populates="project")
    corridors: Mapped[list["Corridor"]] = relationship(back_populates="project")
    exits: Mapped[list["Exit"]] = relationship(back_populates="project")
    fire_protection_items: Mapped[list["FireProtectionItem"]] = relationship(
        back_populates="project"
    )


class Drawing(Base):
    __tablename__ = "drawings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    type: Mapped[DrawingType] = mapped_column(
        Enum(DrawingType, name="drawing_type"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="drawings")
    text_pages: Mapped[list["DrawingText"]] = relationship(
        back_populates="drawing",
        cascade="all, delete-orphan",
    )


class DrawingText(Base):
    __tablename__ = "drawing_texts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drawing_id: Mapped[int] = mapped_column(ForeignKey("drawings.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    drawing: Mapped["Drawing"] = relationship(back_populates="text_pages")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    occupancy_category: Mapped[str] = mapped_column(String(64), nullable=False)
    floor_area: Mapped[float] = mapped_column(Float, nullable=False)
    occupant_load: Mapped[int] = mapped_column(Integer, nullable=False)
    travel_distance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sprinklered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project: Mapped["Project"] = relationship(back_populates="rooms")
    doors: Mapped[list["Door"]] = relationship(back_populates="room")


class Door(Base):
    __tablename__ = "doors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    clear_width: Mapped[float] = mapped_column(Float, nullable=False)
    fire_rating: Mapped[str | None] = mapped_column(String(64))

    room: Mapped["Room"] = relationship(back_populates="doors")


class Corridor(Base):
    __tablename__ = "corridors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    clear_width: Mapped[float] = mapped_column(Float, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="corridors")


class Exit(Base):
    __tablename__ = "exits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    clear_width: Mapped[float] = mapped_column(Float, nullable=False)
    is_required_exit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project: Mapped["Project"] = relationship(back_populates="exits")


class FireProtectionItem(Base):
    __tablename__ = "fire_protection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    item_type: Mapped[FireProtectionItemType] = mapped_column(
        Enum(FireProtectionItemType, name="fire_protection_item_type"),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    rating_required: Mapped[str | None] = mapped_column(String(64))
    rating_provided: Mapped[str | None] = mapped_column(String(64))
    travel_distance_to_nearest: Mapped[float | None] = mapped_column(Float)

    project: Mapped["Project"] = relationship(back_populates="fire_protection_items")


class RegulationClause(Base):
    __tablename__ = "regulation_clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    section: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Float)
    threshold_unit: Mapped[str | None] = mapped_column(String(32))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
