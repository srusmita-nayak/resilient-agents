import copy
from typing import Callable, Dict, Any, List, Optional
from app.core.messages import Message
from app.core.clock import DiscreteEventScheduler
from app.core.faults import FaultInjector

class VirtualChannel:
    """Virtual network transport layer applying seeded fault injection over a discrete-event scheduler."""
    def __init__(
        self,
        scheduler: DiscreteEventScheduler,
        fault_injector: FaultInjector,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.scheduler = scheduler
        self.fault_injector = fault_injector
        self.on_event = on_event or (lambda ev: None)
        self._receivers: Dict[str, Callable[[Message], None]] = {}

    def register_receiver(self, agent_id: str, callback: Callable[[Message], None]) -> None:
        self._receivers[agent_id] = callback

    def send(self, message: Message) -> None:
        """Transmits a message from sender to receiver, subject to configured network faults."""
        sim_now = self.scheduler.now
        message.sent_at = sim_now

        # 1. Observable SEND event
        self.on_event({
            "sim_time": sim_now,
            "type": "SEND",
            "agent_id": message.sender,
            "target_agent_id": message.receiver,
            "msg_id": message.msg_id,
            "payload": {
                "kind": message.kind.value,
                "round": message.round,
                "attempt": message.attempt,
                "corr_id": message.corr_id,
            },
        })

        # 2. Check for drop (partition or loss)
        dropped, reason = self.fault_injector.should_drop(message.sender, message.receiver, sim_now)
        if dropped:
            self.on_event({
                "sim_time": sim_now,
                "type": "DROP",
                "agent_id": message.sender,
                "target_agent_id": message.receiver,
                "msg_id": message.msg_id,
                "payload": {
                    "kind": message.kind.value,
                    "reason": reason,
                    "round": message.round,
                    "attempt": message.attempt,
                },
            })
            return

        # 3. Calculate latency & jitter
        latency = self.fault_injector.calculate_latency()

        # 4. Check for reordering
        is_reordered, extra_delay = self.fault_injector.should_reorder()
        if is_reordered:
            latency += extra_delay
            self.on_event({
                "sim_time": sim_now,
                "type": "REORDER",
                "agent_id": message.sender,
                "target_agent_id": message.receiver,
                "msg_id": message.msg_id,
                "payload": {"extra_delay": extra_delay, "total_delay": latency},
            })

        # 5. Check for duplicate
        is_duplicate = self.fault_injector.should_duplicate()
        if is_duplicate:
            dup_delay = latency + 0.5  # slight offset for duplicate arrival
            dup_msg = copy.deepcopy(message)
            self.on_event({
                "sim_time": sim_now,
                "type": "DUPLICATE",
                "agent_id": message.sender,
                "target_agent_id": message.receiver,
                "msg_id": message.msg_id,
                "payload": {"original_latency": latency, "duplicate_delay": dup_delay},
            })
            self.scheduler.schedule(
                delay=dup_delay,
                callback=lambda m=dup_msg: self._deliver(m),
                description=f"Deliver duplicate {dup_msg.msg_id} to {dup_msg.receiver}",
            )

        # 6. Schedule normal delivery
        msg_copy = copy.deepcopy(message)
        self.scheduler.schedule(
            delay=latency,
            callback=lambda m=msg_copy: self._deliver(m),
            description=f"Deliver {msg_copy.msg_id} to {msg_copy.receiver}",
        )

    def _deliver(self, message: Message) -> None:
        sim_now = self.scheduler.now
        self.on_event({
            "sim_time": sim_now,
            "type": "DELIVER",
            "agent_id": message.receiver,
            "target_agent_id": message.sender,
            "msg_id": message.msg_id,
            "payload": {
                "kind": message.kind.value,
                "round": message.round,
                "attempt": message.attempt,
                "corr_id": message.corr_id,
            },
        })

        receiver_fn = self._receivers.get(message.receiver)
        if receiver_fn:
            receiver_fn(message)
