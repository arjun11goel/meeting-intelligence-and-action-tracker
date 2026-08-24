"""SQLite persistence for MeetingMind."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from src.config import get_settings
from src.schemas import MeetingAnalysis


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection with dictionary-style rows."""
    database_path = get_settings().data_directory / "meetingmind.db"

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database() -> None:
    """Create MeetingMind database tables if they do not exist."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                transcript TEXT NOT NULL,
                executive_summary TEXT NOT NULL,
                key_topics_json TEXT NOT NULL,
                risks_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                owner TEXT,
                due_date TEXT,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_excerpt TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                owner TEXT,
                confidence REAL NOT NULL,
                evidence_excerpt TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            );
            """
        )


def save_meeting(transcript: str, analysis: MeetingAnalysis) -> int:
    """Save a completed meeting analysis and return its database ID."""
    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO meetings (
                title,
                transcript,
                executive_summary,
                key_topics_json,
                risks_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.title,
                transcript,
                analysis.executive_summary,
                json.dumps(analysis.key_topics),
                json.dumps(analysis.risks),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

        meeting_id = cursor.lastrowid

        connection.executemany(
            """
            INSERT INTO action_items (
                meeting_id,
                task,
                owner,
                due_date,
                priority,
                status,
                confidence,
                evidence_excerpt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    meeting_id,
                    item.task,
                    item.owner,
                    item.due_date,
                    item.priority.value,
                    item.status.value,
                    item.confidence,
                    item.evidence.excerpt,
                )
                for item in analysis.action_items
            ],
        )

        connection.executemany(
            """
            INSERT INTO decisions (
                meeting_id,
                decision,
                owner,
                confidence,
                evidence_excerpt
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    meeting_id,
                    decision.decision,
                    decision.owner,
                    decision.confidence,
                    decision.evidence.excerpt,
                )
                for decision in analysis.decisions
            ],
        )

        return int(meeting_id)


def list_meetings(limit: int = 50) -> list[dict]:
    """Return recent meetings with action-item counts."""
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                meetings.id,
                meetings.title,
                meetings.executive_summary,
                meetings.created_at,
                COUNT(action_items.id) AS action_item_count
            FROM meetings
            LEFT JOIN action_items ON action_items.meeting_id = meetings.id
            GROUP BY meetings.id
            ORDER BY meetings.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]