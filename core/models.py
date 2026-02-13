from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class SearchTask:
    task_id: int
    user_id: int
    search_url: str
    interval: int
    last_run: datetime | None = None
    active: bool = True

    def is_ready(self) -> bool:
        if not self.active:
            return False

        if self.last_run is None:
            return True

        return datetime.utcnow() - self.last_run >= timedelta(seconds=self.interval)

    def mark_run(self):
        self.last_run = datetime.utcnow()
