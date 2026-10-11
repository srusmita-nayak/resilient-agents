import uuid
from typing import Dict, Set
from app.middleware.base import BaseMiddleware
from app.core.messages import Message, MessageKind

class BaselineMiddleware(BaseMiddleware):
    """Mode A: Strict synchronous round barrier. Waits for all peers; no timeouts, ACKs, or retries."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_for_round: Dict[int, Set[str]] = {}

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

        # Broadcast current state to all peers
        payload = {
            "node_states": {str(k): (v[0], v[1]) for k, v in self.agent.node_states.items()}
        }
        for peer in self.agent.peers:
            msg = Message(
                msg_id=f"msg_{self.agent.agent_id}_{r}_{peer}_{uuid.uuid4().hex[:6]}",
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

    def handle_message(self, message: Message) -> None:
        if message.kind != MessageKind.DATA:
            return

        r = message.round
        # In baseline, last-arrival-wins: apply node colors directly without version check
        node_states = message.payload.get("node_states", {})
        for node_str, state_val in node_states.items():
            node_id = int(node_str)
            color = state_val[0] if isinstance(state_val, (list, tuple)) else state_val
            # Directly overwrite neighbor state
            self.agent.neighbor_states[node_id] = (color, 1)

        if r not in self.received_for_round:
            self.received_for_round[r] = set()
        self.received_for_round[r].add(message.sender)

        # Check if barrier satisfied for current round
        if r == self.current_round and len(self.received_for_round[r]) >= len(self.agent.peers):
            self._advance_round()

    def _advance_round(self) -> None:
        # Run decision policy
        self.agent.make_decision(self.current_round)
        next_r = self.current_round + 1
        if next_r < self.round_budget:
            self._begin_round(next_r)
        else:
            self.is_finished = True
            self.agent.finished = True
