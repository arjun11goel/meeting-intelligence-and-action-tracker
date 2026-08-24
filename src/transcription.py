"""Audio transcription using Gemini."""

from pathlib import Path
import tempfile

from google import genai

from src.config import get_settings


class AudioTranscriptionError(RuntimeError):
    """Raised when an audio file cannot be transcribed."""


TRANSCRIPTION_INSTRUCTIONS = """
Generate a faithful transcript of this meeting audio.

Requirements:
- Preserve the spoken language.
- Add approximate [MM:SS] timestamps when a speaker begins a new turn.
- Identify speakers as Speaker 1, Speaker 2, and so on when names are unknown.
- Use a participant's name only when it is clearly spoken or otherwise obvious.
- Do not summarize, omit content, or invent speech.
- Include only the transcript, with no introduction or commentary.
"""


def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
) -> str:
    """Upload audio temporarily to Gemini and return its transcript."""
    if not audio_bytes:
        raise AudioTranscriptionError("The uploaded audio file is empty.")

    settings = get_settings()
    if not settings.has_gemini_key:
        raise AudioTranscriptionError(
            "GEMINI_API_KEY is missing. Add it to .env and restart Streamlit."
        )

    suffix = Path(filename).suffix or ".mp3"
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temporary_file:
            temporary_file.write(audio_bytes)
            temporary_path = Path(temporary_file.name)

        client = genai.Client(api_key=settings.gemini_api_key)
        uploaded_file = client.files.upload(file=str(temporary_path))

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[TRANSCRIPTION_INSTRUCTIONS, uploaded_file],
        )

        if not response.text:
            raise AudioTranscriptionError("Gemini returned an empty transcript.")

        return response.text.strip()

    except AudioTranscriptionError:
        raise
    except Exception as error:
        raise AudioTranscriptionError(
            f"Gemini could not transcribe this audio file: {error}"
        ) from error
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()