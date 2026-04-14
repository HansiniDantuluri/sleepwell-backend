from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name          = Column(String)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Sleep goals (set during onboarding)
    sleep_goal_hours    = Column(Float, default=8.0)
    bedtime_target      = Column(String, default="23:00")   # "HH:MM" 24h
    wake_time_target    = Column(String, default="07:00")
    stress_level        = Column(String, default="moderate") # low / moderate / high

    # Onboarding answers stored as JSON for flexibility
    onboarding_data     = Column(JSON, nullable=True)

    # Relationships
    tasks           = relationship("Task",         back_populates="user", cascade="all, delete")
    schedules       = relationship("Schedule",     back_populates="user", cascade="all, delete")
    focus_sessions  = relationship("FocusSession", back_populates="user", cascade="all, delete")
    sleep_logs      = relationship("SleepLog",     back_populates="user", cascade="all, delete")


class Task(Base):
    __tablename__ = "tasks"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    title           = Column(String, nullable=False)
    task_type       = Column(String, default="work")   # work / study / personal / health
    priority        = Column(String, default="normal") # urgent / normal / flexible
    estimated_minutes = Column(Integer, default=30)
    deadline        = Column(DateTime(timezone=True), nullable=True)
    notes           = Column(Text, nullable=True)
    is_completed    = Column(Boolean, default=False)
    date_for        = Column(String, nullable=True)    # "YYYY-MM-DD" — which day this task belongs to
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user            = relationship("User", back_populates="tasks")
    schedule_blocks = relationship("ScheduleBlock", back_populates="task")


class Schedule(Base):
    __tablename__ = "schedules"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    date        = Column(String, nullable=False)       # "YYYY-MM-DD"
    ai_notes    = Column(Text, nullable=True)          # AI explanation of decisions made
    confidence  = Column(Integer, default=85)          # AI confidence score 0-100
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    user    = relationship("User",          back_populates="schedules")
    blocks  = relationship("ScheduleBlock", back_populates="schedule", cascade="all, delete")


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id              = Column(Integer, primary_key=True, index=True)
    schedule_id     = Column(Integer, ForeignKey("schedules.id"),  nullable=False)
    task_id         = Column(Integer, ForeignKey("tasks.id"),      nullable=True)  # null for sleep/break blocks
    block_type      = Column(String, default="task")  # task / sleep / break / wind_down / buffer
    title           = Column(String, nullable=False)
    start_time      = Column(String, nullable=False)  # "HH:MM"
    end_time        = Column(String, nullable=False)  # "HH:MM"
    is_locked       = Column(Boolean, default=False)  # sleep blocks are locked
    is_auto_adjusted = Column(Boolean, default=False) # flagged by AI rescheduling
    color           = Column(String, default="blue")  # red/yellow/blue/purple

    schedule    = relationship("Schedule", back_populates="blocks")
    task        = relationship("Task",     back_populates="schedule_blocks")


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id         = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    task_title      = Column(String)
    duration_minutes = Column(Integer, default=25)
    completed       = Column(Boolean, default=False)
    xp_earned       = Column(Integer, default=0)
    started_at      = Column(DateTime(timezone=True), server_default=func.now())
    ended_at        = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="focus_sessions")


class SleepLog(Base):
    __tablename__ = "sleep_logs"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    date            = Column(String, nullable=False)   # "YYYY-MM-DD"
    bedtime_actual  = Column(String, nullable=True)    # "HH:MM"
    wake_time_actual = Column(String, nullable=True)
    sleep_hours     = Column(Float, nullable=True)
    quality_score   = Column(Integer, nullable=True)   # 1-10 self-report
    schedule_adherence = Column(Float, nullable=True)  # 0.0-1.0

    user = relationship("User", back_populates="sleep_logs")
