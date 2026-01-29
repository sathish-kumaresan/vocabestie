import os
from pathlib import Path
from gtts import gTTS
import logging

# Setup logger
logger = logging.getLogger(__name__)

AUDIO_DIR = Path("app/static/audio/words")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def get_audio_path(text: str) -> str:
    """Returns the relative web path for the audio file."""
    # Sanitize filename: 'hej' -> 'hej.mp3', 'en katt' -> 'en_katt.mp3'
    safe_name = "".join([c if c.isalnum() else "_" for c in text.lower()])
    filename = f"{safe_name}.mp3"
    file_path = AUDIO_DIR / filename
    
    # If not exists, generate
    if not file_path.exists():
        try:
            logger.info(f"Generating audio for: {text}")
            tts = gTTS(text=text, lang='sv')
            tts.save(str(file_path))
        except Exception as e:
            logger.error(f"Failed to generate audio for {text}: {e}")
            return None

    return f"/static/audio/words/{filename}"
