import uuid
from typing import Dict, Set, Optional
from app.middleware.base import BaseMiddleware
from app.core.messages import Message, MessageKind

class TimeoutBaselineMiddleware(BaseMiddleware):
    """Mode B: Round barrier with timeout fallback. Skips silent peers; no ACKs, retries, or version checks."""
    def __init__(self, *args, barrier_timeout: float = 10.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.barrier_timeout = barrier_timeout
        self.received_for_round: Dict[int, Set[str]] = {}
        self.current_timeout_event_id: Optional[str] = None

    def start(self) -> None:
        self._begin_round(0)

    def _begin_round(self, r: int) -> None:
        if r >= self.round_budget:
            self.is_finished = True
            self.agent.finished = True
            return

        self.current_round = r
        self.agent.current_round = r
        if r not in self.received_for_round:
            self.received_for_round[r] = set()

        # Schedule barrier timeout in virtual time
        ev_id = f"barrier_timeout_{self.agent.agent_id}_{r}"
        self.current_timeout_event_id = self.scheduler.schedule(
            delay=self.barrier_timeout,
            callback=lambda round_idx=r: self._on_barrier_timeout(round_idx),
            description=f"Barrier timeout for {self.agent.agent_id} round {r}",
            event_id=ev_id,
        )

        # Broadcast state
        payload = {
            "node_states": {str(k): (v[0], v[1]) for k, v in self.agent.node_states.items()}
        }
        for peer in self.agent.peers:
            msg = Message(
                msg_id=f"msg_b_{self.agent.agent_id}_{r}_{peer}_{uuid.uuid4().hex[:6]}",
                kind=MessageKind.DATA,
                sender=self.agent.agent_id,
                receiver=peer,
                task_id=self.task_id,
                run_id=self.run_id,
                round=r,
                payload=payload,
                attempt=1,
            )
            self.channel.send(msg)

    def _on_barrier_timeout(self, r: int) -> None:
        if self.is_finished or r != self.current_round:
            return

        # Record timeout event
        silent_peers = [p for p in self.agent.peers if p not in self.received_for_round.get(r, set())]
        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "TIMEOUT",
            "agent_id": self.agent.agent_id,
            "payload": {
                "round": r,
                "silent_peers": silent_peers,
                "reason": "Round barrier expired; proceeding with last known states",
            },
        })

        # Advance round with degraded/partial knowledge
        self._advance_round()

    def handle_message(self, message: Message) -> None:
        if message.kind != MessageKind.DATA:
            return

        r = message.round
        # Last arrival wins: apply node colors directly without version check
        node_states = message.payload.get("node_states", {})
        for node_str, state_val in node_states.items():
            node_id = int(node_str)
            color = state_val[0] if isinstance(state_val, (list, tuple)) else state_val
            self.agent.neighbor_states[node_id] = (color, 1)

        if r not in self.received_for_round:
            self.received_for_round[r] = set()
        self.received_for_round[r].add(message.sender)

        # If barrier satisfied before timeout, cancel barrier timeout and advance
        if r == self.current_round and len(self.received_for_round[r]) >= len(self.agent.peers):
            if self.current_timeout_event_id:
                self.scheduler.cancel(self.current_timeout_event_id)
                self.current_timeout_event_id = None
            self._advance_round()

    def _advance_round(self) -> None:
        if self.current_timeout_event_id:
            self.scheduler.cancel(self.current_timeout_event_id)
            self.current_timeout_event_id = None

        self.agent.make_decision(self.current_round)
        next_r = self.current_round + 1
        if next_r < self.round_budget:
            self._begin_round(next_r)
        else:
            self.is_finished = True
            self.agent.finished = True
