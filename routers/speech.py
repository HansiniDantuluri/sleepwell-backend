from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import tempfile, os, traceback
from database import get_db
from auth_utils import get_current_user
from ai_scheduler import parse_free_text_tasks
import models, schemas

router = APIRouter()

try:
    import openai
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


@router.post("/transcribe", response_model=schemas.TranscriptionResult)
async def transcribe_audio(
    audio: UploadFile = File(...),
    parse_tasks: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not WHISPER_AVAILABLE:
        raise HTTPException(status_code=503, detail="openai package not installed")

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set in .env file")

    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        client = openai.OpenAI(api_key=openai_key)
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en"
            )
        text = transcript.text.strip()
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"WHISPER ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    parsed = []
    if parse_tasks and text:
        user_context = {
            "bedtime_target": current_user.bedtime_target,
            "wake_time_target": current_user.wake_time_target
        }
        try:
            parsed = parse_free_text_tasks(text, user_context)
        except Exception:
            parsed = []

    return schemas.TranscriptionResult(text=text, parsed_tasks=parsed)


@router.post("/parse-text", response_model=schemas.TranscriptionResult)
def parse_text_to_tasks(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    user_context = {
        "bedtime_target": current_user.bedtime_target,
        "wake_time_target": current_user.wake_time_target
    }
    parsed = parse_free_text_tasks(text, user_context)
    return schemas.TranscriptionResult(text=text, parsed_tasks=parsed)