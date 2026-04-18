from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base
from routers import auth, users, tasks, schedule, focus, progress, speech

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="SleepWell API",
    description="Backend for the SleepWell AI-powered scheduling app",
    version="1.0.0",
    lifespan=lifespan
)

# Handle CORS manually
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
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