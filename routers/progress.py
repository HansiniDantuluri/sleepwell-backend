from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()


@router.post("/sleep-log", response_model=schemas.SleepLogOut, status_code=201)
def log_sleep(
    payload: schemas.SleepLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Upsert: if log for this date exists, update it
    existing = db.query(models.SleepLog).filter(
        models.SleepLog.user_id == current_user.id,
        models.SleepLog.date == payload.date
    ).first()

    if existing:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    log = models.SleepLog(user_id=current_user.id, **payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/sleep-logs", response_model=List[schemas.SleepLogOut])
def get_sleep_logs(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.SleepLog).filter(
        models.SleepLog.user_id == current_user.id
    ).order_by(models.SleepLog.date.desc()).limit(days).all()


@router.get("/stats", response_model=schemas.ProgressStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    sleep_logs = db.query(models.SleepLog).filter(
        models.SleepLog.user_id == current_user.id
    ).order_by(models.SleepLog.date.desc()).limit(30).all()

    focus_sessions = db.query(models.FocusSession).filter(
        models.FocusSession.user_id == current_user.id,
        models.FocusSession.completed == True
    ).all()

    # Streak: count consecutive days with a sleep log
    streak = _calculate_streak(sleep_logs)

    # Averages
    logs_with_sleep = [l for l in sleep_logs if l.sleep_hours]
    avg_sleep = sum(l.sleep_hours for l in logs_with_sleep) / len(logs_with_sleep) if logs_with_sleep else 0.0

    logs_with_adherence = [l for l in sleep_logs if l.schedule_adherence is not None]
    avg_adherence = sum(l.schedule_adherence for l in logs_with_adherence) / len(logs_with_adherence) if logs_with_adherence else 0.0

    total_xp = sum(s.xp_earned for s in focus_sessions)

    return schemas.ProgressStats(
        streak_days=streak,
        avg_sleep_hours=round(avg_sleep, 1),
        avg_adherence=round(avg_adherence, 2),
        total_focus_sessions=len(focus_sessions),
        total_xp=total_xp,
        sleep_logs=sleep_logs
    )


def _calculate_streak(logs: list) -> int:
    """Count consecutive days in the logs (most recent first)."""
    from datetime import date, timedelta
    if not logs:
        return 0
    streak = 0
    dates = sorted({l.date for l in logs}, reverse=True)
    expected = None
    for d in dates:
        if expected is None or d == expected:
            streak += 1
            from datetime import date as dt
            expected = (dt.fromisoformat(d) - timedelta(days=1)).isoformat()
        else:
            break
    return streak
