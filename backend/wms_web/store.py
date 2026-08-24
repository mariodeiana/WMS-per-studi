from __future__ import annotations

from backend.wms_core.models import Practice
from backend.wms_core.templates import build_lipe_trim_tasks


class PracticeStore:
    def __init__(self) -> None:
        self.practices: dict[str, Practice] = {}

    def get(self, practice_id: str) -> Practice:
        return self.practices[practice_id]

    def all(self) -> list[Practice]:
        return list(self.practices.values())


def demo_store() -> PracticeStore:
    store = PracticeStore()
    tasks = build_lipe_trim_tasks()
    for index, task in enumerate(tasks):
        task.assigned_to = "mario" if index % 2 == 0 else "anna"
    store.practices["P-2026-0001"] = Practice(
        id="P-2026-0001",
        practice_type_code="LIPE_TRIM",
        client_id="CLIENT-001",
        client_name="Alfa Demo S.r.l.",
        period_start="2026-04-01",
        period_end="2026-06-30",
        due_date="2026-09-30",
        context={"periodo": "Secondo trimestre 2026", "regime": "IVA trimestrale"},
        tasks=tasks,
    )
    return store
