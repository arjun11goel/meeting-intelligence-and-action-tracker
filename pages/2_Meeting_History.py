"""MeetingMind meeting history page."""

import streamlit as st

from src.database import initialize_database, list_meetings


st.set_page_config(page_title="Meeting History | MeetingMind", page_icon="📚")

initialize_database()

st.title("📚 Meeting History")
st.write("Review saved meetings and their extracted action items.")

meetings = list_meetings()

if not meetings:
    st.info(
        "No saved meetings yet. Analyze a transcript on the main page, "
        "then click **Save meeting to history**."
    )
else:
    st.metric("Saved meetings", len(meetings))

    for meeting in meetings:
        with st.expander(
            f"{meeting['title']} — {meeting['action_item_count']} action items"
        ):
            st.caption(f"Saved: {meeting['created_at']}")
            st.write(meeting["executive_summary"])