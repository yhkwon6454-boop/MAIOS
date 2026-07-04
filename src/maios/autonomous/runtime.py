from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any
from uuid import uuid4

from maios.core import MAIOSCore, MissionResult


@dataclass
class MissionRecord:
    goal: str
    mission_id: str
    status: str = "QUEUED"
    result: MissionResult | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "goal": self.goal,
            "mission_id": self.mission_id,
            "status": self.status,
            "error": self.error,
            "result": None,
        }

        if self.result is not None:
            data["result"] = {
                "goal": self.result.goal,
                "status": self.result.status.value,
                "final_output": self.result.final_output,
                "qa_score": self.result.qa_result.score,
                "reflection_report_id": (
                    self.result.reflection_report.report_id if self.result.reflection_report else ""
                ),
            }

        return data


class MissionScheduler:
    """Thread-safe queue and persistent history for autonomous missions."""

    def __init__(self, history_path: str | Path | None = None) -> None:
        self.history_path = Path(history_path) if history_path else None
        self._queue: Queue[str] = Queue()
        self._records: dict[str, MissionRecord] = {}
        self._lock = Lock()
        self._load_history()

    def submit(self, goal: str) -> MissionRecord:
        record = MissionRecord(goal=goal, mission_id=f"AM-{uuid4().hex[:8]}")
        with self._lock:
            self._records[record.mission_id] = record
            self._persist()
        self._queue.put(record.mission_id)
        return record

    def get_next(self, timeout: float | None = None) -> MissionRecord | None:
        try:
            mission_id = self._queue.get(timeout=timeout)
        except Empty:
            return None

        with self._lock:
            record = self._records[mission_id]
            record.status = "RUNNING"
            self._persist()
            return record

    def complete(self, record: MissionRecord, result: MissionResult) -> None:
        with self._lock:
            record.result = result
            record.status = "COMPLETED"
            self._records[record.mission_id] = record
            self._persist()
        self._queue.task_done()

    def fail(self, record: MissionRecord, error: str) -> None:
        with self._lock:
            record.error = error
            record.status = "FAILED"
            self._records[record.mission_id] = record
            self._persist()
        self._queue.task_done()

    def get(self, mission_id: str) -> MissionRecord | None:
        with self._lock:
            return self._records.get(mission_id)

    def history(self) -> list[MissionRecord]:
        with self._lock:
            return list(self._records.values())

    def pending_count(self) -> int:
        return self._queue.qsize()

    def wait_until_idle(self) -> None:
        self._queue.join()

    def _load_history(self) -> None:
        if self.history_path is None or not self.history_path.exists():
            return

        data = json.loads(self.history_path.read_text(encoding="utf-8"))
        for item in data.get("missions", []):
            record = MissionRecord(
                goal=item["goal"],
                mission_id=item["mission_id"],
                status=item.get("status", "COMPLETED"),
                error=item.get("error", ""),
            )
            self._records[record.mission_id] = record

    def _persist(self) -> None:
        if self.history_path is None:
            return

        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            json.dumps(
                {"missions": [record.to_dict() for record in self._records.values()]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


class MAIOSAgent:
    """Autonomous MAIOS runtime that continuously accepts and executes goals."""

    def __init__(
        self,
        core: MAIOSCore | None = None,
        scheduler: MissionScheduler | None = None,
        core_factory: Callable[[], MAIOSCore] | None = None,
        max_workers: int = 1,
    ) -> None:
        self.core = core
        self.core_factory = core_factory
        self.scheduler = scheduler or MissionScheduler()
        self.max_workers = max_workers
        self._stop_event = Event()
        self._workers: list[Thread] = []

    def submit_goal(self, goal: str) -> MissionRecord:
        return self.scheduler.submit(goal)

    def run_next(self) -> MissionRecord | None:
        record = self.scheduler.get_next(timeout=0)
        if record is None:
            return None

        self._execute_record(record)
        return record

    def run_pending(self) -> list[MissionRecord]:
        records = []
        while True:
            record = self.run_next()
            if record is None:
                break
            records.append(record)
        return records

    def start_background(self) -> None:
        if self._workers:
            return

        self._stop_event.clear()
        for index in range(self.max_workers):
            worker = Thread(
                target=self._worker_loop,
                name=f"maios-agent-{index}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

    def stop_background(self) -> None:
        self._stop_event.set()
        for worker in self._workers:
            worker.join(timeout=2)
        self._workers = []

    def wait_until_idle(self) -> None:
        self.scheduler.wait_until_idle()

    def history(self) -> list[MissionRecord]:
        return self.scheduler.history()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            record = self.scheduler.get_next(timeout=0.1)
            if record is None:
                continue
            self._execute_record(record)

    def _execute_record(self, record: MissionRecord) -> None:
        try:
            result = self._core().run(record.goal)
        except Exception as exc:
            self.scheduler.fail(record, str(exc))
            return

        self.scheduler.complete(record, result)

    def _core(self) -> MAIOSCore:
        if self.core_factory is not None:
            return self.core_factory()
        if self.core is not None:
            return self.core
        self.core = MAIOSCore()
        return self.core
