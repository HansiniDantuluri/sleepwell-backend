from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()


@router.get("/me", response_model=schemas.UserProfile)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/onboarding", response_model=schemas.UserProfile)
def save_onboarding(
    payload: schemas.OnboardingData,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Save onboarding answers — sleep goals, bedtime, stress level, etc."""
    current_user.sleep_goal_hours = payload.sleep_goal_hours
    current_user.bedtime_target   = payload.bedtime_target
    current_user.wake_time_target = payload.wake_time_target
    current_user.stress_level     = payload.stress_level
    current_user.onboarding_data  = payload.onboarding_data
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/profile", response_model=schemas.UserProfile)
def update_profile(
    payload: schemas.OnboardingData,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update sleep settings from the Settings screen."""
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
