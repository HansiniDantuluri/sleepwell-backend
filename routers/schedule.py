from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth_utils import get_current_user
from ai_scheduler import generate_schedule
import models, schemas

router = APIRouter()


@router.post("/generate", response_model=schemas.ScheduleOut)
def generate_ai_schedule(
    payload: schemas.ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Core endpoint: generates an AI schedule for the given date.
    Accepts task IDs from DB and/or free-text/speech input.
    """
    # Load tasks from DB
    task_dicts = []
    if payload.task_ids:
        tasks = db.query(models.Task).filter(
            models.Task.id.in_(payload.task_ids),
            models.Task.user_id == current_user.id
        ).all()
    else:
        # Use all incomplete tasks for this date
        tasks = db.query(models.Task).filter(
            models.Task.user_id == current_user.id,
            models.Task.is_completed == False,
            models.Task.date_for == payload.date
        ).all()

    for t in tasks:
        task_dicts.append({
            "id": t.id,
            "title": t.title,
            "task_type": t.task_type,
            "priority": t.priority,
            "estimated_minutes": t.estimated_minutes,
            "deadline": t.deadline.strftime("%H:%M") if t.deadline else None,
            "notes": t.notes
        })

    # Build user profile dict for the AI
    user_profile = {
        "name": current_user.name or "You",
        "sleep_goal_hours": current_user.sleep_goal_hours,
        "bedtime_target": current_user.bedtime_target,
        "wake_time_target": current_user.wake_time_target,
        "stress_level": current_user.stress_level
    }

    # Call AI scheduler
    ai_result = generate_schedule(
        user_profile=user_profile,
        tasks=task_dicts,
        target_date=payload.date,
        free_text=payload.free_text_tasks
    )

    # Save any tasks parsed from free text
    for extra in ai_result.get("parsed_extra_tasks", []):
        new_task = models.Task(
            user_id=current_user.id,
            title=extra.get("title", "Unnamed task"),
            task_type=extra.get("task_type", "work"),
            priority=extra.get("priority", "normal"),
            estimated_minutes=extra.get("estimated_minutes", 30),
            date_for=payload.date
        )
        db.add(new_task)
        db.flush()  # get ID before commit
        # Update task_dicts so blocks can map to it
        task_dicts.append({"id": new_task.id, "title": new_task.title})

    # Delete existing schedule for this date (regeneration)
    existing = db.query(models.Schedule).filter(
        models.Schedule.user_id == current_user.id,
        models.Schedule.date == payload.date
    ).first()
    if existing:
        db.delete(existing)
        db.flush()

    # Save new schedule
    schedule = models.Schedule(
        user_id=current_user.id,
        date=payload.date,
        ai_notes=ai_result.get("ai_notes"),
        confidence=ai_result.get("confidence", 80)
    )
    db.add(schedule)
    db.flush()

    # Build a title→task_id lookup for linking blocks to tasks
    title_to_id = {t["title"].lower(): t["id"] for t in task_dicts}

    # Save schedule blocks
    for block_data in ai_result.get("blocks", []):
        task_ref = block_data.get("task_ref", "")
        matched_task_id = None
        if task_ref:
            matched_task_id = title_to_id.get(task_ref.lower())

        block = models.ScheduleBlock(
            schedule_id=schedule.id,
            task_id=matched_task_id,
            block_type=block_data.get("block_type", "task"),
            title=block_data.get("title", ""),
            start_time=block_data.get("start_time", ""),
            end_time=block_data.get("end_time", ""),
            is_locked=block_data.get("is_locked", False),
            is_auto_adjusted=block_data.get("is_auto_adjusted", False),
            color=block_data.get("color", "blue")
        )
        db.add(block)

    db.commit()
    db.refresh(schedule)

    # Return warnings in response headers (optional) - they're in ai_notes too
    return schedule


@router.get("/{date}", response_model=Optional[schemas.ScheduleOut])
def get_schedule(
    date: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get the saved schedule for a specific date."""
    schedule = db.query(models.Schedule).filter(
        models.Schedule.user_id == current_user.id,
        models.Schedule.date == date
    ).first()
    return schedule  # Returns null if no schedule yet — frontend handles this


@router.get("/", response_model=List[schemas.ScheduleOut])
def list_schedules(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Schedule).filter(
        models.Schedule.user_id == current_user.id
    ).order_by(models.Schedule.date.desc()).limit(30).all()
