from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base
from routers import auth, users, tasks, schedule, focus, progress, speech

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="SleepWell API",
    description="Backend for the SleepWell AI-powered scheduling app",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sleepwell-delta.vercel.app", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",     tags=["Authentication"])
app.include_router(users.router,    prefix="/api/users",    tags=["Users"])
app.include_router(tasks.router,    prefix="/api/tasks",    tags=["Tasks"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(focus.router,    prefix="/api/focus",    tags=["Focus Sessions"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
app.include_router(speech.router,   prefix="/api/speech",   tags=["Speech to Text"])

@app.get("/")
def root():
    return {"message": "SleepWell API is running ✅"}
