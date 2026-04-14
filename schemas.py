from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── User / Onboarding ───────────────────────────────────────────────────────

class OnboardingData(BaseModel):
    sleep_goal_hours: float = 8.0
    bedtime_target: str = "23:00"
    wake_time_target: str = "07:00"
    stress_level: str = "moderate"
    onboarding_data: Optional[Any] = None  # raw JSON from onboarding flow

class UserProfile(BaseModel):
    id: int
    email: str
    name: Optional[str]
    sleep_goal_hours: float
    bedtime_target: str
    wake_time_target: str
    stress_level: str

    class Config:
        from_attributes = True


# ─── Tasks ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    task_type: str = "work"
    priority: str = "normal"
    estimated_minutes: int = 30
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    date_for: Optional[str] = None  # "YYYY-MM-DD"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    task_type: Optional[str] = None
    priority: Optional[str] = None
    estimated_minutes: Optional[int] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    is_completed: Optional[bool] = None

class TaskOut(BaseModel):
    id: int
    title: str
    task_type: str
    priority: str
    estimated_minutes: int
    deadline: Optional[datetime]
    notes: Optional[str]
    is_completed: bool
    date_for: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Schedule Generation ─────────────────────────────────────────────────────

class ScheduleRequest(BaseModel):
    """What the frontend sends when asking for an AI schedule."""
    date: str                       # "YYYY-MM-DD"
    task_ids: Optional[List[int]] = None   # specific tasks to schedule; if None, uses all for date
    free_text_tasks: Optional[str] = None  # raw text/speech-to-text input e.g. "finish report by 5pm, gym 1 hour"

class ScheduleBlockOut(BaseModel):
    id: int
    task_id: Optional[int]
    block_type: str
    title: str
    start_time: str
    end_time: str
    is_locked: bool
    is_auto_adjusted: bool
    color: str

    class Config:
        from_attributes = True

class ScheduleOut(BaseModel):
    id: int
    date: str
    ai_notes: Optional[str]
    confidence: int
    blocks: List[ScheduleBlockOut]

    class Config:
        from_attributes = True


# ─── Focus Sessions ──────────────────────────────────────────────────────────

class FocusSessionStart(BaseModel):
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    duration_minutes: int = 25

class FocusSessionEnd(BaseModel):
    completed: bool = True

class FocusSessionOut(BaseModel):
    id: int
    task_title: Optional[str]
    duration_minutes: int
    completed: bool
    xp_earned: int
    started_at: datetime
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Sleep Logs ──────────────────────────────────────────────────────────────

class SleepLogCreate(BaseModel):
    date: str
    bedtime_actual: Optional[str] = None
    wake_time_actual: Optional[str] = None
    sleep_hours: Optional[float] = None
    quality_score: Optional[int] = None
    schedule_adherence: Optional[float] = None

class SleepLogOut(BaseModel):
    id: int
    date: str
    bedtime_actual: Optional[str]
    wake_time_actual: Optional[str]
    sleep_hours: Optional[float]
    quality_score: Optional[int]
    schedule_adherence: Optional[float]

    class Config:
        from_attributes = True


# ─── Progress / Analytics ────────────────────────────────────────────────────

class ProgressStats(BaseModel):
    streak_days: int
    avg_sleep_hours: float
    avg_adherence: float
    total_focus_sessions: int
    total_xp: int
    sleep_logs: List[SleepLogOut]


# ─── Speech to Text ──────────────────────────────────────────────────────────

class TranscriptionResult(BaseModel):
    text: str
    parsed_tasks: Optional[List[TaskCreate]] = None
