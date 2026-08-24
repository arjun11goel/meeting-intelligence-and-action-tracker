"""Gemini-powered structured extraction for meeting transcripts."""

from typing import Any

from google import genai
from google.genai import types

from src.config import get_settings
from src.schemas import MeetingAnalysis


class GeminiExtractionError(RuntimeError):
    """Raised when Gemini cannot return a valid meeting analysis."""


EXTRACTION_INSTRUCTIONS = """
You are MeetingMind, an evidence-grounded meeting-intelligence assistant.

Analyze the supplied meeting transcript and return only data that matches the
provided MeetingAnalysis schema.

Rules:
1. Extract only facts explicitly stated in the transcript. Never invent tasks,
   owners, deadlines, decisions, risks, or questions.
2. Every action item, decision, and open question must include an evidence
   excerpt copied exactly from the transcript.
3. If an owner or deadline is not explicit, use null. Do not guess.
4. For due_date, use YYYY-MM-DD only when the transcript explicitly provides
   a complete date including its year. Otherwise preserve the deadline wording
   exactly as stated, such as "next Monday" or "August 27".
5. Write action items as clear verb-led tasks.
6. Use confidence between 0.0 and 1.0. Confidence reflects how explicitly the
   transcript supports the extraction.
7. Keep the executive summary concise, factual, and action-oriented.
8. Return empty lists when a category has no supported items.
"""


def remove_unsupported_schema_fields(value: Any) -> Any:
    """
    Remove JSON Schema fields not accepted by Gemini.

    Pydantic creates additionalProperties when extra='forbid' is enabled.
    We retain strict validation locally but remove this field from the schema
    sent to Gemini.
    """
    if isinstance(value, dict):
        return {
            key: remove_unsupported_schema_fields(item)
            for key, item in value.items()
            if key != "additionalProperties"
        }

    if isinstance(value, list):
        return [remove_unsupported_schema_fields(item) for item in value]

    return value


def get_gemini_response_schema() -> dict[str, Any]:
    """Create a Gemini-compatible version of the Pydantic schema."""
    return remove_unsupported_schema_fields(MeetingAnalysis.model_json_schema())


def extract_meeting_analysis(transcript: str) -> MeetingAnalysis:
    """Use Gemini to convert one transcript into validated meeting intelligence."""
    if len(transcript.strip()) < 50:
        raise GeminiExtractionError(
            "Please provide a longer meeting transcript before analyzing it."
        )

    settings = get_settings()
    if not settings.has_gemini_key:
        raise GeminiExtractionError(
            "GEMINI_API_KEY is missing. Add it to your .env file and restart Streamlit."
        )

    prompt = (
        f"{EXTRACTION_INSTRUCTIONS}\n\n"
        "MEETING TRANSCRIPT:\n"
        "-------------------\n"
        f"{transcript.strip()}"
    )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=get_gemini_response_schema(),
            ),
        )

        if response.parsed is not None:
            return MeetingAnalysis.model_validate(response.parsed)

        if response.text:
            return MeetingAnalysis.model_validate_json(response.text)

        raise GeminiExtractionError("Gemini returned an empty response.")

    except GeminiExtractionError:
        raise
    except Exception as error:
        raise GeminiExtractionError(
            f"Gemini could not analyze this transcript: {error}"
        ) from error