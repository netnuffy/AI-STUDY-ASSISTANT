import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from core.exceptions import NotFoundError
from database.session import get_db
from models.study_plan import StudyPlan
from models.user import User
from schemas.study_plan import StudyPlanCreate, StudyPlanResponse, TaskUpdate
from services import plan_service

router = APIRouter(prefix="/study-plans", tags=["study-plans"])


@router.post("", response_model=StudyPlanResponse, status_code=201)
def create_study_plan(
    data: StudyPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return plan_service.generate_study_plan(db, current_user, data)


@router.get("", response_model=list[StudyPlanResponse])
def list_study_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(StudyPlan)
        .filter(StudyPlan.user_id == current_user.id)
        .order_by(StudyPlan.created_at.desc())
        .all()
    )


@router.get("/{plan_id}", response_model=StudyPlanResponse)
def get_study_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = (
        db.query(StudyPlan)
        .filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id)
        .first()
    )
    if not plan:
        raise NotFoundError("Study plan not found")
    return plan


@router.patch("/{plan_id}/tasks/{task_index}", response_model=StudyPlanResponse)
def update_task(
    plan_id: uuid.UUID,
    task_index: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return plan_service.update_task(db, current_user, plan_id, task_index, data.done)


@router.delete("/{plan_id}", status_code=204)
def delete_study_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = (
        db.query(StudyPlan)
        .filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id)
        .first()
    )
    if not plan:
        raise NotFoundError("Study plan not found")
    db.delete(plan)
    db.commit()
    return None
