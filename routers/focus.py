from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()

# XP formula: base XP for completing a focus session
def calculate_xp(duration_minutes: int, completed: bool) -> int:
    if not completed:
        return max(5, duration_minutes // 5)  # partial XP for abandoned sessions
    base = duration_minutes * 2
    bonus = 20 if duration_minutes >= 25 else 0  # bonus for full Pomodoro
    return base + bonus


@router.post("/start", response_model=schemas.FocusSessionOut, status_code=201)
def start_focus(
    payload: schemas.FocusSessionStart,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Resolve task title
    task_title = payload.task_title
    if payload.task_id and not task_title:
        task = db.query(models.Task).filter(models.Task.id == payload.task_id).first()
        task_title = task.title if task else "Focus Session"

    session = models.FocusSession(
        user_id=current_user.id,
        task_id=payload.task_id,
        task_title=task_title,
        duration_minutes=payload.duration_minutes
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/end", response_model=schemas.FocusSessionOut)
def end_focus(
    session_id: int,
    payload: schemas.FocusSessionEnd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.FocusSession).filter(
        models.FocusSession.id == session_id,
        models.FocusSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.completed = payload.completed
    session.ended_at  = datetime.utcnow()
    session.xp_earned = calculate_xp(session.duration_minutes, payload.completed)
    db.commit()
    db.refresh(session)
    return session


@router.get("/", response_model=list[schemas.FocusSessionOut])
def get_focus_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.FocusSession).filter(
        models.FocusSession.user_id == current_user.id
    ).order_by(models.FocusSession.started_at.desc()).limit(limit).all()
