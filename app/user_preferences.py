from __future__ import annotations

import json
from pathlib import Path


class UserPreferencesStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def get_preferences(self, user_id: str) -> dict:
        data = json.loads(self.path.read_text(encoding="utf-8"))

        return data.get(
            user_id,
            {
                "report_format": "table_with_comments",
                "tone": "concise executive",
            },
        )

    def update_preferences(self, user_id: str, preferences: dict) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))

        current = data.get(user_id, {})
        current.update(preferences)

        data[user_id] = current

        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )