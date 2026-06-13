from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


class AgentTrace:
    def __init__(self, log_path: Path):
        self.run_id = str(uuid.uuid4())
        self.start_time = time.perf_counter()
        self.log_path = log_path
        self.nodes_visited: list[str] = []
        self.events: list[dict[str, Any]] = []

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def node(self, name: str, **kwargs: Any) -> None:
        self.nodes_visited.append(name)
        self.events.append(
            {
                "event_type": "node",
                "node": name,
                "timestamp": time.time(),
                **kwargs,
            }
        )

    def finish(self, **kwargs: Any) -> None:
        record = {
            "run_id": self.run_id,
            "latency_ms": int((time.perf_counter() - self.start_time) * 1000),
            "nodes_visited": self.nodes_visited,
            "events": self.events,
            **kwargs,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")