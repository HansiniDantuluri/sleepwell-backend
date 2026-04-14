from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.TaskOut])
def get_tasks(
    date_for: Optional[str] = None,  # filter by date "YYYY-MM-DD"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Task).filter(models.Task.user_id == current_user.id)
    if date_for:
        query = query.filter(models.Task.date_for == date_for)
    return query.order_by(models.Task.created_at.desc()).all()


@router.post("/", response_model=schemas.TaskOut, status_code=201)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = models.Task(user_id=current_user.id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@router.patch("/{task_id}/complete", response_model=schemas.TaskOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = True
    db.commit()
    db.refresh(task)
    return task
