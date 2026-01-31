
import os
import tempfile
import asyncio
from fastapi import UploadFile
import whisper
import Levenshtein
# from app.services.speech import SpeechService

# Global model instance to avoid reloading (lazy loaded)
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        # Load the base model - good balance of speed and accuracy for Swedish
        print("Loading Whisper model...")
        _whisper_model = whisper.load_model("base")
        print("Whisper model loaded.")
    return _whisper_model

class PronunciationService:
    @staticmethod
    async def analyze_audio(file: UploadFile, expected_text: str):
        """
        Analyze uploaded audio against expected text using Whisper.
        Returns score, transcription, and feedback.
        """
        # Save temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)
            
        try:
            # Transcribe with Whisper
            result = await asyncio.to_thread(PronunciationService._transcribe, tmp_path)
            transcribed_text = result["text"].strip()
            
            # Clean up temp file
            os.remove(tmp_path)
            
            # Compare and score
            score, feedback = PronunciationService._calculate_score(transcribed_text, expected_text)
            
            return {
                "transcription": transcribed_text,
                "score": score,
                "feedback": feedback,
                "syllables": PronunciationService._generate_dummy_syllables(expected_text, score) # Placeholder for complex syllable mapping
            }
            
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            print(f"Error analyzing audio: {e}")
            raise e

    @staticmethod
    def _transcribe(file_path: str):
        model = get_whisper_model()
        # language='sv' forces Swedish, task='transcribe'
        return model.transcribe(file_path, language="sv", task="transcribe")

    @staticmethod
    def _calculate_score(transcribed: str, expected: str):
        t_norm = transcribed.lower().strip(".,!?")
        e_norm = expected.lower().strip(".,!?")
        
        if not t_norm:
            return 0, "No speech detected"
            
        # Levenshtein distance
        dist = Levenshtein.distance(t_norm, e_norm)
        max_len = max(len(t_norm), len(e_norm))
        
        if max_len == 0:
            return 0, "Error"
            
        similarity = (1 - (dist / max_len)) * 100
        
        # Adjust score curve
        score = int(similarity)
        
        if score >= 100:
            return 100, "Perfect!"
        elif score >= 80:
            return score, "Excellent pronunciation!"
        elif score >= 60:
            return score, "Good effort, almost there."
        elif score >= 40:
            return score, "Getting closer."
        else:
            return score, "Let's try that again."

    @staticmethod
    def _generate_dummy_syllables(text: str, total_score: int):
        # In a real implementation, we would align audio with phonemes.
        # For now, we split the word and assign the score roughly to all parts.
        # Basic heuristic syllable splitter for Swedish (vowel-consonant pattern)
        import re
        parts = re.split(r'([aeiouyåäö]+)', text, flags=re.IGNORECASE)
        syllables = []
        current = ""
        
        for part in parts:
            if not part: continue
            current += part
            # If we have a vowel group, it's a syllable core, append what we have
            if re.search(r'[aeiouyåäö]', part, re.IGNORECASE):
                # Check if next part is consonants, if so, maybe attach one to this syllable
                pass
            
            # Simple split by length for visual effect if regex split is too complex
        
        # Fallback simple split
        simple_parts = []
        l = len(text)
        if l <= 4:
            simple_parts = [text]
        else:
            mid = l // 2
            simple_parts = [text[:mid], text[mid:]]
            
        return [{"syllable": p, "score": total_score} for p in simple_parts]
