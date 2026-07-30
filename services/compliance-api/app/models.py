import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DrawingType(str, enum.Enum):
    ARCHITECTURAL = "architectural"
    MECHANICAL = "mechanical"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    drawings: Mapped[list["Drawing"]] = relationship(back_populates="project")
    rooms: Mapped[list["Room"]] = relationship(back_populates="project")
    corridors: Mapped[list["Corridor"]] = relationship(back_populates="project")


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


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    occupancy_category: Mapped[str] = mapped_column(String(64), nullable=False)
    floor_area: Mapped[float] = mapped_column(Float, nullable=False)
    occupant_load: Mapped[int] = mapped_column(Integer, nullable=False)

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
