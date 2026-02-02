
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.pronunciation import PronunciationService
from app.dependencies import get_current_user
from app.database import get_db
from app.models.word import Word

router = APIRouter(
    prefix="/api/speech",
    tags=["speech"]
)

@router.post("/analyze")
async def analyze_speech(
    audio: UploadFile = File(...),
    word_id: int = Form(...),
    tier: str = Form("2"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user) 
):
    """
    Analyze speech audio file.
    Tier 1: Basic energy check (client side mostly)
    Tier 2: Server STT (Vosk)
    """
    
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
        
    # analyze_audio expects (file_obj, expected_text)
    # Depending on how analyze_audio is implemented, it might need the file object or bytes.
    # The service I wrote takes UploadFile.
    result = await PronunciationService.analyze_audio(audio, word.swedish)
    return result

# Removed redundant endpoint
