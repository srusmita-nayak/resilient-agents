import heapq
import time
from dataclasses import dataclass, field
from typing import Callable, Any, Optional

@dataclass(order=True)
class ScheduledEvent:
    timestamp: float
    tie_breaker: int
    callback: Callable[[], None] = field(compare=False)
    description: str = field(compare=False, default="")
    event_id: str = field(compare=False, default="")
    cancelled: bool = field(compare=False, default=False)

class DiscreteEventScheduler:
    """Deterministic discrete-event scheduler with a virtual clock."""
    def __init__(self, max_sim_time: float = 1000.0, max_events: int = 10000, max_wall_seconds: float = 60.0):
        self.virtual_time: float = 0.0
        self._queue: list[ScheduledEvent] = []
        self._tie_breaker_counter: int = 0
        self._events_processed: int = 0
        self.max_sim_time: float = max_sim_time
        self.max_events: int = max_events
        self.max_wall_seconds: float = max_wall_seconds
        self._events_by_id: dict[str, ScheduledEvent] = {}

    @property
    def now(self) -> float:
        return self.virtual_time

    @property
    def events_processed(self) -> int:
        return self._events_processed

    def schedule(self, delay: float, callback: Callable[[], None], description: str = "", event_id: str = "") -> str:
        """Schedule a callback at virtual_time + delay."""
        if delay < 0:
            raise ValueError(f"Schedule delay cannot be negative: {delay}")
        target_time = self.virtual_time + delay
        self._tie_breaker_counter += 1
        ev_id = event_id or f"ev_{self._tie_breaker_counter}"
        event = ScheduledEvent(
            timestamp=target_time,
            tie_breaker=self._tie_breaker_counter,
            callback=callback,
            description=description,
            event_id=ev_id,
        )
        heapq.heappush(self._queue, event)
        self._events_by_id[ev_id] = event
        return ev_id

    def cancel(self, event_id: str) -> bool:
        """Cancel a pending event by event_id."""
        if event_id in self._events_by_id:
            ev = self._events_by_id[event_id]
            if not ev.cancelled:
                ev.cancelled = True
                return True
        return False

    def step(self) -> bool:
        """Process the next scheduled event. Returns True if an event was processed, False if queue is empty."""
        while self._queue:
            event = heapq.heappop(self._queue)
            if event.event_id in self._events_by_id:
                del self._events_by_id[event.event_id]
            if event.cancelled:
                continue

            self.virtual_time = event.timestamp
            self._events_processed += 1
            event.callback()
            return True
        return False

    def has_pending(self) -> bool:
        """Check if any non-cancelled events are in the queue."""
        for ev in self._queue:
            if not ev.cancelled:
                return True
        return False

    def peek_next_time(self) -> Optional[float]:
        for ev in self._queue:
            if not ev.cancelled:
                return ev.timestamp
        return None
