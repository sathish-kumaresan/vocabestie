
import os
import json
import wave
import tempfile
import asyncio
import zipfile
import urllib.request
from pathlib import Path
from fastapi import UploadFile
from vosk import Model, KaldiRecognizer
import Levenshtein

# Model configuration
MODEL_NAME = "vosk-model-small-sv-rhasspy-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / MODEL_NAME

# Global model instance (lazy loaded)
_vosk_model = None


def download_model():
    """Download and extract the Swedish Vosk model if not present."""
    if MODEL_PATH.exists():
        return

    print(f"Downloading Vosk Swedish model...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = MODEL_DIR / f"{MODEL_NAME}.zip"

    # Download
    urllib.request.urlretrieve(MODEL_URL, zip_path)

    # Extract
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MODEL_DIR)

    # Cleanup zip
    zip_path.unlink()
    print(f"Vosk model downloaded to {MODEL_PATH}")


def get_vosk_model():
    """Get or load the Vosk model."""
    global _vosk_model
    if _vosk_model is None:
        download_model()
        print("Loading Vosk model...")
        _vosk_model = Model(str(MODEL_PATH))
        print("Vosk model loaded.")
    return _vosk_model


def convert_to_wav(input_path: str, output_path: str):
    """Convert audio file to WAV format for Vosk (16kHz mono)."""
    from pydub import AudioSegment

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_path, format="wav")


class PronunciationService:
    @staticmethod
    async def analyze_audio(file: UploadFile, expected_text: str):
        """
        Analyze uploaded audio against expected text using Vosk.
        Returns score, transcription, and feedback.
        """
        # Save temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)

        wav_path = tmp_path + ".wav"

        try:
            # Convert to WAV format
            await asyncio.to_thread(convert_to_wav, tmp_path, wav_path)

            # Transcribe with Vosk
            transcribed_text = await asyncio.to_thread(
                PronunciationService._transcribe, wav_path
            )

            # Compare and score
            score, feedback = PronunciationService._calculate_score(
                transcribed_text, expected_text
            )

            return {
                "transcription": transcribed_text,
                "score": score,
                "feedback": feedback,
                "syllables": PronunciationService._generate_dummy_syllables(
                    expected_text, score
                )
            }

        except Exception as e:
            print(f"Error analyzing audio: {e}")
            raise e
        finally:
            # Cleanup temp files
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(wav_path):
                os.remove(wav_path)

    @staticmethod
    def _transcribe(wav_path: str) -> str:
        """Transcribe audio using Vosk."""
        model = get_vosk_model()

        wf = wave.open(wav_path, "rb")

        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            raise ValueError("Audio must be mono WAV 16kHz 16-bit")

        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)

        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part = json.loads(rec.Result())
                results.append(part.get("text", ""))

        # Get final result
        final = json.loads(rec.FinalResult())
        results.append(final.get("text", ""))

        wf.close()
        return " ".join(results).strip()

    @staticmethod
    def _calculate_score(transcribed: str, expected: str):
        """Calculate pronunciation score using Levenshtein distance."""
        t_norm = transcribed.lower().strip(".,!?")
        e_norm = expected.lower().strip(".,!?")

        if not t_norm:
            return 0, "No speech detected. Try again."

        # Sanity check for noise
        if len(expected) < 5 and len(t_norm) > len(e_norm) * 3:
            return 0, "Could not understand. Try again."

        # Levenshtein distance
        dist = Levenshtein.distance(t_norm, e_norm)
        max_len = max(len(t_norm), len(e_norm))

        if max_len == 0:
            return 0, "Error"

        similarity = (1 - (dist / max_len)) * 100
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
        """Generate syllable breakdown for UI display."""
        import re

        # Simple split for visual effect
        simple_parts = []
        l = len(text)
        if l <= 4:
            simple_parts = [text]
        else:
            mid = l // 2
            simple_parts = [text[:mid], text[mid:]]

        return [{"syllable": p, "score": total_score} for p in simple_parts]
