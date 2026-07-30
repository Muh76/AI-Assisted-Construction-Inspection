from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import get_data_raw_dir
from app.db import get_db
from app.models import Drawing, DrawingType, Project, User
from app.reports.pdf import build_compliance_pdf
from app.schemas import ComplianceReport, DrawingRead, ProjectCreate, ProjectRead
from app.services.compliance import build_compliance_report
from app.services.ownership import get_owned_project

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = Project(name=payload.name, owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    return list(
        db.scalars(select(Project).where(Project.owner_id == current_user.id)).all()
    )


@router.get("/{project_id}/compliance/export")
def export_project_compliance_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    project = get_owned_project(db, project_id, current_user)
    report = build_compliance_report(project_id, db)
    pdf_bytes = build_compliance_pdf(report, project.name)
    filename = f"compliance-report-project-{project_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/compliance", response_model=ComplianceReport)
def get_project_compliance(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceReport:
    get_owned_project(db, project_id, current_user)
    return build_compliance_report(project_id, db)


@router.post(
    "/{project_id}/drawings",
    response_model=DrawingRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_drawing(
    project_id: int,
    file: UploadFile = File(...),
    type: DrawingType = Form(DrawingType.ARCHITECTURAL),
    db: Session = Depends(get_db),
) -> Drawing:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

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

    upload_date = datetime.now(UTC).replace(tzinfo=None)
    timestamp = upload_date.strftime("%Y%m%d_%H%M%S")
    saved_filename = f"project-{project_id}-{timestamp}.pdf"

    raw_dir = get_data_raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / saved_filename
    destination.write_bytes(await file.read())

    drawing = Drawing(
        project_id=project_id,
        type=type,
        file_path=f"data/raw/{saved_filename}",
        upload_date=upload_date,
    )
    db.add(drawing)
    db.commit()
    db.refresh(drawing)
    return drawing


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    return get_owned_project(db, project_id, current_user)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = get_owned_project(db, project_id, current_user)

    for field, value in payload.model_dump().items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    project = get_owned_project(db, project_id, current_user)
    db.delete(project)
    db.commit()
