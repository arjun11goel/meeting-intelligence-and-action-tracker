"""MeetingMind Streamlit application."""

from pathlib import Path

import streamlit as st

from src.config import get_settings
from src.extraction import GeminiExtractionError
from src.pipeline import analyze_meeting
from src.transcription import AudioTranscriptionError, transcribe_audio
from src.validation import validate_evidence_grounding
from src.database import initialize_database, save_meeting


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_TRANSCRIPT_PATH = PROJECT_ROOT / "sample_data" / "product_planning.txt"
MAX_TRANSCRIPT_CHARS = 50_000


st.set_page_config(
    page_title="MeetingMind",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_sample_transcript() -> str:
    """Load the bundled sample transcript."""
    return SAMPLE_TRANSCRIPT_PATH.read_text(encoding="utf-8")


def initialize_session_state() -> None:
    """Create Streamlit state values on the first page load."""
    defaults = {
        "transcript": "",
        "analysis": None,
        "analyzed_transcript": "",
        "saved_meeting_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def show_analysis() -> None:
    """Render validated structured meeting intelligence."""
    analysis = st.session_state.analysis
    transcript = st.session_state.analyzed_transcript
    validation_errors = validate_evidence_grounding(analysis, transcript)

    st.divider()
    st.subheader(analysis.title)

    if st.session_state.saved_meeting_id:
        st.success(
            f"Saved to meeting history (Meeting #{st.session_state.saved_meeting_id})."
        )
    else:
        if st.button("Save meeting to history", type="primary"):
            meeting_id = save_meeting(
                transcript=st.session_state.analyzed_transcript,
                analysis=analysis,
            )
            st.session_state.saved_meeting_id = meeting_id
            st.rerun()
    
    st.markdown("#### Executive summary")
    st.write(analysis.executive_summary)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Action items", len(analysis.action_items))
    metric_2.metric("Decisions", len(analysis.decisions))
    metric_3.metric("Open questions", len(analysis.open_questions))
    metric_4.metric(
        "Evidence checks",
        "Passed" if not validation_errors else "Review",
    )

    st.markdown("#### Key topics")
    if analysis.key_topics:
        st.write(" • ".join(analysis.key_topics))
    else:
        st.caption("No key topics identified.")

    st.markdown("#### Action tracker")
    if analysis.action_items:
        action_rows = [
            {
                "Task": item.task,
                "Owner": item.owner or "Unassigned",
                "Due date": item.due_date or "Not specified",
                "Priority": item.priority.value.title(),
                "Confidence": f"{item.confidence:.0%}",
                "Status": item.status.value.replace("_", " ").title(),
            }
            for item in analysis.action_items
        ]
        st.dataframe(action_rows, use_container_width=True, hide_index=True)

        for item in analysis.action_items:
            with st.expander(f"Evidence: {item.task}"):
                st.markdown(f"> {item.evidence.excerpt}")
    else:
        st.success("No action items were explicitly stated.")

    st.markdown("#### Decisions")
    if analysis.decisions:
        for decision in analysis.decisions:
            with st.expander(decision.decision):
                st.caption(f"Confidence: {decision.confidence:.0%}")
                st.markdown(f"> {decision.evidence.excerpt}")
    else:
        st.caption("No explicit decisions identified.")

    st.markdown("#### Open questions")
    if analysis.open_questions:
        for question in analysis.open_questions:
            owner = question.owner or "Unassigned"
            st.markdown(f"- **{question.question}** — Owner: {owner}")
            st.caption(f'Evidence: "{question.evidence.excerpt}"')
    else:
        st.success("No unresolved questions were identified.")

    st.markdown("#### Risks and dependencies")
    if analysis.risks:
        for risk in analysis.risks:
            st.warning(risk)
    else:
        st.success("No risks or dependencies were identified.")

    st.markdown("#### Evidence audit")
    if validation_errors:
        for error in validation_errors:
            st.error(error)
    else:
        st.success(
            "All extracted tasks, decisions, and questions are grounded "
            "in supporting transcript evidence."
        )


initialize_session_state()
settings = get_settings()
initialize_database()

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1200px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("🧠 MeetingMind")
    st.caption("AI Meeting Intelligence & Action Tracker")
    st.divider()

    if settings.has_gemini_key:
        st.success("Gemini API key configured")
        st.caption(f"Model: {settings.gemini_model}")
    else:
        st.error("Gemini API key not found")
        st.caption("Add GEMINI_API_KEY to .env, then restart the app.")

    st.divider()
    st.markdown(
        """
        **Workflow**

        1. Add a meeting transcript  
        2. Extract structured facts  
        3. Ground facts in evidence  
        4. Save and search meeting memory
        """
    )
    st.divider()
    st.caption("Phase 1: transcript intelligence MVP")

st.title("Turn conversations into accountable action.")
st.write(
    "Extract decisions, action items, owners, deadlines, risks, and unresolved "
    "questions—each linked back to supporting transcript evidence."
)

left_column, right_column = st.columns([3, 2])

with left_column:
    st.subheader("Meeting input")

    uploaded_audio = st.file_uploader(
        "Upload meeting audio",
        type=["mp3", "wav", "m4a", "aac", "flac", "ogg"],
        help="Upload audio to generate a transcript before analysis.",
    )

    if uploaded_audio is not None:
        st.caption(
            f"Selected file: {uploaded_audio.name} "
            f"({uploaded_audio.size / 1_000_000:.1f} MB)"
        )

        if st.button("Transcribe audio", use_container_width=True):
            try:
                with st.spinner(
                    "Transcribing audio and identifying speaker turns..."
                ):
                    st.session_state.transcript = transcribe_audio(
                        audio_bytes=uploaded_audio.getvalue(),
                        filename=uploaded_audio.name,
                    )
                    st.session_state.saved_meeting_id = None
                    st.session_state.analysis = None
                    st.session_state.analyzed_transcript = ""
                st.rerun()
            except AudioTranscriptionError as error:
                st.error(str(error))

    st.markdown("**Or paste an existing transcript**")

    transcript = st.text_area(
        "Paste a transcript",
        value=st.session_state.transcript,
        placeholder="Paste your meeting transcript here...",
        height=360,
        label_visibility="collapsed",
    )
    st.session_state.transcript = transcript

with right_column:
    st.subheader("Analyze a meeting")
    st.write(
        "MeetingMind uses Gemini structured output and validates each extracted "
        "fact against the original transcript."
    )

    if st.button("Load sample meeting", use_container_width=True):
        st.session_state.transcript = load_sample_transcript()
        st.session_state.saved_meeting_id = None
        st.session_state.analysis = None
        st.rerun()

    can_analyze = bool(st.session_state.transcript.strip()) and settings.has_gemini_key

    if st.button(
        "Analyze meeting",
        type="primary",
        use_container_width=True,
        disabled=not can_analyze,
    ):
        if len(st.session_state.transcript) > MAX_TRANSCRIPT_CHARS:
            st.error(
                "This transcript is too long for the current demo limit. "
                "Please use fewer than 50,000 characters."
            )
        else:
            try:
                with st.spinner(
                    "Extracting actions, decisions, owners, deadlines, and evidence..."
                ):
                    st.session_state.analysis = analyze_meeting(
                        st.session_state.transcript
                    )
                    st.session_state.analyzed_transcript = (
                        st.session_state.transcript
                    )
                    st.session_state.saved_meeting_id = None
                st.rerun()
            except GeminiExtractionError as error:
                st.error(str(error))

    st.divider()
    st.markdown("**Current output includes**")
    st.markdown(
        """
        - Executive summary
        - Action tracker
        - Decisions
        - Open questions
        - Risks and dependencies
        - Evidence audit
        """
    )

if (
    st.session_state.analysis
    and st.session_state.transcript != st.session_state.analyzed_transcript
):
    st.info("The transcript changed. Click **Analyze meeting** to refresh the results.")

if st.session_state.analysis:
    show_analysis()