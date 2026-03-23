"""
Scoring Engine — server-side only.
Answers are never sent to the client. This service loads the question bank,
scores a session's responses, and computes percentile ranks.
"""
import json
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).parent.parent.parent / "content"


def load_test(test_key: str) -> dict:
    path = CONTENT_DIR / f"{test_key}.json"
    if not path.exists():
        raise ValueError(f"Unknown test: {test_key}")
    return json.loads(path.read_text())


def get_questions_for_client(test_key: str) -> list[dict]:
    """Return questions stripped of correct_answer — safe for client delivery."""
    test = load_test(test_key)
    questions = []
    for q in test["questions"]:
        questions.append({
            "id": q["id"],
            "text": q["text"],
            "options": q["options"],   # [{key, text}]
            "type": q.get("type", "mcq"),
        })
    return questions


def score_session(
    test_key: str,
    responses: list[dict],  # [{question_id, answer}]
) -> dict[str, Any]:
    """
    Returns:
        {
            raw_score: int,           # correct answers
            total_questions: int,
            percentage: float,        # 0-100
            label: str,               # Excellent / Good / Fair / Below Average
        }
    """
    test = load_test(test_key)
    answer_key = {q["id"]: q["correct_answer"] for q in test["questions"]}
    total = len(answer_key)

    resp_map = {r["question_id"]: r["answer"] for r in responses}
    correct = sum(1 for qid, ans in answer_key.items() if resp_map.get(qid) == ans)

    pct = round((correct / total) * 100, 1) if total else 0.0

    if pct >= 80:
        label = "Excellent"
    elif pct >= 60:
        label = "Good"
    elif pct >= 40:
        label = "Fair"
    else:
        label = "Below Average"

    return {
        "raw_score": correct,
        "total_questions": total,
        "percentage": pct,
        "label": label,
    }


def compute_weighted_total(
    scores_by_test: dict,     # {test_key: {percentage, ...}}
    test_config: list[dict],  # [{test_key, weight}]
) -> float:
    """Weighted average across selected tests. Returns 0–100."""
    total_weight = sum(t["weight"] for t in test_config)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(
        scores_by_test.get(t["test_key"], {}).get("percentage", 0) * t["weight"]
        for t in test_config
    )
    return round(weighted_sum / total_weight, 2)


def compute_percentile_ranks(totals: list[float]) -> list[float]:
    """
    Given a list of total scores (one per candidate, ordered),
    return the percentile rank for each.
    """
    n = len(totals)
    if n == 0:
        return []
    ranks = []
    for score in totals:
        below = sum(1 for s in totals if s < score)
        ranks.append(round((below / n) * 100, 1))
    return ranks
