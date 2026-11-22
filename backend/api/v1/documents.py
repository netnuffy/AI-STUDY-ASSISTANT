import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from core.config import get_settings
from core.exceptions import BadRequestError, NotFoundError
from database.session import get_db
from models.study_document import StudyDocument
from models.user import User
from schemas.common import Paginated
from schemas.document import DocumentResponse
from services import document_service
from services.document_service import process_document_background

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise BadRequestError("Only PDF files are allowed")
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise BadRequestError(f"File is too large (max {settings.MAX_UPLOAD_MB} MB)")
    if not contents.startswith(b"%PDF-"):
        raise BadRequestError("Uploaded file is not a valid PDF")

    stored_name = f"{uuid.uuid4()}.pdf"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(contents)

    title = os.path.splitext(file.filename)[0]
    doc = document_service.create_document(
        db,
        current_user,
        title=title,
        filename=file.filename,
        file_path=file_path,
        file_size=len(contents),
    )
    background_tasks.add_task(process_document_background, doc.id)
    return doc


@router.get("", response_model=Paginated[DocumentResponse])
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(StudyDocument)
        .filter(StudyDocument.user_id == current_user.id)
        .order_by(StudyDocument.created_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Paginated(items=items, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise NotFoundError("StudyDocument not found")
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document_service.delete_document(db, current_user, document_id)
    return None
