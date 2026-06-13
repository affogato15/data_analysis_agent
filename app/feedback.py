from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FeedbackCollector:
    def __init__(self, candidate_path: Path):
        self.candidate_path = candidate_path
        self.candidate_path.parent.mkdir(parents=True, exist_ok=True)

    def save_candidate_trio(
        self,
        question: str,
        sql: str,
        report: str,
        retrieved_examples: list[dict],
        user_feedback: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "question": question,
            "business_logic": "Candidate generated from a successful user interaction. Requires analyst review before promotion to Golden Bucket.",
            "metrics": [],
            "tables_used": [],
            "sql": sql,
            "report": report,
            "retrieved_examples": [ex["id"] for ex in retrieved_examples],
            "user_feedback": user_feedback,
            "status": "pending_review",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        with self.candidate_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")