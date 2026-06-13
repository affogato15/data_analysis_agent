from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SavedReportsStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, reports: list[dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(reports, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def save_report(
        self,
        user_id: str,
        question: str,
        sql: str,
        report: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        reports = self._load()

        report_id = str(uuid.uuid4())

        reports.append(
            {
                "report_id": report_id,
                "user_id": user_id,
                "question": question,
                "sql": sql,
                "report": report,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "deleted_at": None,
            }
        )

        self._save(reports)

        return report_id

    def list_reports(self, user_id: str) -> list[dict[str, Any]]:
        return [
            report
            for report in self._load()
            if report["user_id"] == user_id and report.get("deleted_at") is None
        ]

    def find_reports_mentioning(
        self,
        user_id: str,
        text: str,
    ) -> list[dict[str, Any]]:
        text_lower = text.lower()

        matches = []

        for report in self.list_reports(user_id):
            searchable_text = " ".join(
                [
                    str(report.get("question", "")),
                    str(report.get("report", "")),
                    str(report.get("sql", "")),
                ]
            ).lower()

            if text_lower in searchable_text:
                matches.append(report)

        return matches

    def delete_reports(
        self,
        user_id: str,
        report_ids: list[str],
        confirmation: str,
    ) -> int:
        if confirmation != "DELETE":
            raise ValueError("Deletion requires exact confirmation: DELETE")

        reports = self._load()
        report_ids_set = set(report_ids)

        deleted_count = 0
        deleted_at = datetime.now(timezone.utc).isoformat()

        for report in reports:
            if (
                report["user_id"] == user_id
                and report["report_id"] in report_ids_set
                and report.get("deleted_at") is None
            ):
                report["deleted_at"] = deleted_at
                deleted_count += 1

        self._save(reports)

        return deleted_count