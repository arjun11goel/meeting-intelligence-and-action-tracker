"""Run a small, reproducible evaluation of MeetingMind extraction quality."""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import analyze_meeting
from src.validation import validate_evidence_grounding


DATASET_PATH = PROJECT_ROOT / "evals" / "annotated_meetings.json"


def normalize(text: str | None) -> str:
    """Normalize text for simple case-insensitive comparisons."""
    return (text or "").strip().casefold()


def matches_keywords(text: str, keywords: list[str]) -> bool:
    """Return true when every expected keyword occurs in an extracted text."""
    normalized_text = normalize(text)
    return all(normalize(keyword) in normalized_text for keyword in keywords)


def calculate_percentage(correct: int, total: int) -> float:
    """Return a safe percentage."""
    return round((correct / total) * 100, 1) if total else 0.0


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    expected_actions_total = 0
    extracted_actions_total = 0
    matched_actions_total = 0

    expected_decisions_total = 0
    extracted_decisions_total = 0
    matched_decisions_total = 0

    owner_total = 0
    owner_correct = 0

    deadline_total = 0
    deadline_correct = 0

    evidence_total = 0
    evidence_supported = 0

    print("\nMeetingMind Evaluation Results")
    print("=" * 35)

    for example in dataset:
        print(f"\nEvaluating: {example['id']}")
        analysis = analyze_meeting(example["transcript"])

        extracted_actions_total += len(analysis.action_items)
        extracted_decisions_total += len(analysis.decisions)
        expected_actions_total += len(example["expected_actions"])
        expected_decisions_total += len(example["expected_decisions"])

        matched_action_indexes: set[int] = set()

        for expected_action in example["expected_actions"]:
            for index, predicted_action in enumerate(analysis.action_items):
                if (
                    index not in matched_action_indexes
                    and matches_keywords(
                        predicted_action.task,
                        expected_action["task_keywords"],
                    )
                ):
                    matched_action_indexes.add(index)
                    matched_actions_total += 1

                    if expected_action["owner"] is not None:
                        owner_total += 1
                        if normalize(predicted_action.owner) == normalize(
                            expected_action["owner"]
                        ):
                            owner_correct += 1

                    if expected_action["due_date"] is not None:
                        deadline_total += 1
                        if normalize(predicted_action.due_date) == normalize(
                            expected_action["due_date"]
                        ):
                            deadline_correct += 1
                    break

        matched_decision_indexes: set[int] = set()

        for expected_decision in example["expected_decisions"]:
            for index, predicted_decision in enumerate(analysis.decisions):
                if (
                    index not in matched_decision_indexes
                    and matches_keywords(
                        predicted_decision.decision,
                        expected_decision["keywords"],
                    )
                ):
                    matched_decision_indexes.add(index)
                    matched_decisions_total += 1
                    break

        evidence_errors = validate_evidence_grounding(
            analysis,
            example["transcript"],
        )
        meeting_evidence_total = (
            len(analysis.action_items)
            + len(analysis.decisions)
            + len(analysis.open_questions)
        )

        evidence_total += meeting_evidence_total
        evidence_supported += meeting_evidence_total - len(evidence_errors)

        print(f"  Extracted actions: {len(analysis.action_items)}")
        print(f"  Extracted decisions: {len(analysis.decisions)}")
        print(f"  Evidence errors: {len(evidence_errors)}")

    action_precision = calculate_percentage(
        matched_actions_total,
        extracted_actions_total,
    )
    action_recall = calculate_percentage(
        matched_actions_total,
        expected_actions_total,
    )

    if action_precision + action_recall:
        action_f1 = round(
            2 * action_precision * action_recall / (action_precision + action_recall),
            1,
        )
    else:
        action_f1 = 0.0

    decision_precision = calculate_percentage(
        matched_decisions_total,
        extracted_decisions_total,
    )
    decision_recall = calculate_percentage(
        matched_decisions_total,
        expected_decisions_total,
    )

    print("\nFinal metrics")
    print("-" * 35)
    print(f"Action-item precision: {action_precision}%")
    print(f"Action-item recall:    {action_recall}%")
    print(f"Action-item F1 score:  {action_f1}%")
    print(f"Decision precision:    {decision_precision}%")
    print(f"Decision recall:       {decision_recall}%")
    print(f"Owner accuracy:        {calculate_percentage(owner_correct, owner_total)}%")
    print(
        f"Deadline accuracy:     "
        f"{calculate_percentage(deadline_correct, deadline_total)}%"
    )
    print(
        f"Evidence-grounding rate: "
        f"{calculate_percentage(evidence_supported, evidence_total)}%"
    )


if __name__ == "__main__":
    main()