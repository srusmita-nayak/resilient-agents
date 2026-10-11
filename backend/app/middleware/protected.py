import uuid
from collections import deque
from typing import Dict, Set, Optional, Tuple, Any, List
from app.middleware.base import BaseMiddleware
from app.core.messages import Message, MessageKind

class ProtectedMiddleware(BaseMiddleware):
    """Mode C: Full resilient protocol state machine with ACKs, bounded retries, duplicate suppression,
    version-based monotonic consistency, authoritative snapshots, and degraded recovery."""
    def __init__(
        self,
        *args,
        ack_timeout: float = 3.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        round_barrier_timeout: float = 12.0,
        max_recoordination_attempts: int = 2,
        max_seen_history: int = 1000,
        # Ablation toggles
        enable_retransmission: bool = True,
        enable_version_filter: bool = True,
        enable_sync_recoordination: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.ack_timeout = ack_timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.round_barrier_timeout = round_barrier_timeout
        self.max_recoordination_attempts = max_recoordination_attempts
        self.max_seen_history = max_seen_history

        # Ablation toggles
        self.enable_retransmission = enable_retransmission
        self.enable_version_filter = enable_version_filter
        self.enable_sync_recoordination = enable_sync_recoordination

        # Protocol state machine tracking
        # pending_data_acks: msg_id -> {message, receiver, attempt, timer_id, sent_at}
        self.pending_data_acks: Dict[str, Dict[str, Any]] = {}
        # seen_msg_ids: bounded FIFO
        self.seen_msg_ids: Set[str] = set()
        self.seen_queue: deque = deque()

        # Barrier & round tracking
        self.received_for_round: Dict[int, Set[str]] = {}
        self.barrier_timer_id: Optional[str] = None
        self.recoordination_attempts_for_round: Dict[int, int] = {}
        self.degraded_peers: Set[str] = set()

    def start(self) -> None:
        self._begin_round(0)

    def _mark_seen(self, msg_id: str) -> bool:
        """Returns True if already seen (duplicate), False if newly seen."""
        if msg_id in self.seen_msg_ids:
            return True
        self.seen_msg_ids.add(msg_id)
        self.seen_queue.append(msg_id)
        if len(self.seen_queue) > self.max_seen_history:
            oldest = self.seen_queue.popleft()
            self.seen_msg_ids.discard(oldest)
        return False

    def _begin_round(self, r: int) -> None:
        if r >= self.round_budget:
            self.is_finished = True
            self.agent.finished = True
            return

        self.current_round = r
        self.agent.current_round = r
        if r not in self.received_for_round:
            self.received_for_round[r] = set()
        self.recoordination_attempts_for_round[r] = 0

        # Schedule round barrier timeout
        ev_id = f"protected_barrier_{self.agent.agent_id}_{r}"
        self.barrier_timer_id = self.scheduler.schedule(
            delay=self.round_barrier_timeout,
            callback=lambda round_idx=r: self._on_barrier_timeout(round_idx),
            description=f"Protected barrier timeout for {self.agent.agent_id} round {r}",
            event_id=ev_id,
        )

        # Broadcast state
        payload = {
            "node_states": {str(k): (v[0], v[1]) for k, v in self.agent.node_states.items()}
        }
        for peer in self.agent.peers:
            msg_id = f"c_{self.agent.agent_id}_{r}_{peer}_{uuid.uuid4().hex[:6]}"
            msg = Message(
                msg_id=msg_id,
                kind=MessageKind.DATA,
                sender=self.agent.agent_id,
                receiver=peer,
                task_id=self.task_id,
                run_id=self.run_id,
                round=r,
                payload=payload,
                attempt=1,
            )
            self._send_data_with_ack_tracking(msg)

    def _send_data_with_ack_tracking(self, msg: Message) -> None:
        self.channel.send(msg)

        if not self.enable_retransmission:
            return

        # Schedule ACK timeout timer
        timer_id = f"ack_timer_{msg.msg_id}_{msg.attempt}"
        self.pending_data_acks[msg.msg_id] = {
            "message": msg,
            "receiver": msg.receiver,
            "attempt": msg.attempt,
            "timer_id": timer_id,
            "sent_at": self.scheduler.now,
        }

        self.scheduler.schedule(
            delay=self.ack_timeout,
            callback=lambda m_id=msg.msg_id, att=msg.attempt: self._on_ack_timeout(m_id, att),
            description=f"ACK timeout for {msg.msg_id} attempt {msg.attempt}",
            event_id=timer_id,
        )

    def _on_ack_timeout(self, msg_id: str, attempt: int) -> None:
        if msg_id not in self.pending_data_acks:
            return  # Already ACKed

        entry = self.pending_data_acks[msg_id]
        if entry["attempt"] != attempt:
            return

        msg: Message = entry["message"]
        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "TIMEOUT",
            "agent_id": self.agent.agent_id,
            "target_agent_id": msg.receiver,
            "msg_id": msg_id,
            "payload": {"attempt": attempt, "max_retries": self.max_retries},
        })

        if attempt < self.max_retries:
            next_attempt = attempt + 1
            delay = self.ack_timeout * (self.backoff_factor ** (attempt - 1))
            msg.attempt = next_attempt
            
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "RETRY",
                "agent_id": self.agent.agent_id,
                "target_agent_id": msg.receiver,
                "msg_id": msg_id,
                "payload": {"attempt": next_attempt, "backoff_delay": delay},
            })

            # Retransmit
            self.channel.send(msg)

            # Re-schedule ACK timer
            timer_id = f"ack_timer_{msg_id}_{next_attempt}"
            entry["attempt"] = next_attempt
            entry["timer_id"] = timer_id
            self.scheduler.schedule(
                delay=delay,
                callback=lambda m_id=msg_id, att=next_attempt: self._on_ack_timeout(m_id, att),
                description=f"ACK timeout for {msg_id} attempt {next_attempt}",
                event_id=timer_id,
            )
        else:
            # Retries exhausted
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "RETRY_EXHAUSTED",
                "agent_id": self.agent.agent_id,
                "target_agent_id": msg.receiver,
                "msg_id": msg_id,
                "payload": {"attempts_made": attempt},
            })
            self.degraded_peers.add(msg.receiver)
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "DEGRADED_PEER",
                "agent_id": self.agent.agent_id,
                "target_agent_id": msg.receiver,
                "payload": {"reason": "Retries exhausted without receiving ACK"},
            })
            del self.pending_data_acks[msg_id]

    def _on_barrier_timeout(self, r: int) -> None:
        if self.is_finished or r != self.current_round:
            return

        silent_peers = [p for p in self.agent.peers if p not in self.received_for_round.get(r, set())]
        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "TIMEOUT",
            "agent_id": self.agent.agent_id,
            "payload": {
                "round": r,
                "silent_peers": silent_peers,
                "reason": "Round barrier expired",
            },
        })

        recoords = self.recoordination_attempts_for_round.get(r, 0)
        if self.enable_sync_recoordination and recoords < self.max_recoordination_attempts and silent_peers:
            # Issue SYNC_REQ to silent peers
            self.recoordination_attempts_for_round[r] = recoords + 1
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "RECOORD_ATTEMPT",
                "agent_id": self.agent.agent_id,
                "payload": {
                    "round": r,
                    "attempt": recoords + 1,
                    "target_peers": silent_peers,
                },
            })

            for peer in silent_peers:
                sync_msg = Message(
                    msg_id=f"sync_req_{self.agent.agent_id}_{r}_{peer}_{uuid.uuid4().hex[:6]}",
                    kind=MessageKind.SYNC_REQ,
                    sender=self.agent.agent_id,
                    receiver=peer,
                    task_id=self.task_id,
                    run_id=self.run_id,
                    round=r,
                    payload={"requested_round": r},
                )
                self.channel.send(sync_msg)

            # Re-arm barrier timer with shorter sync wait
            sync_wait = 4.0
            ev_id = f"recoord_barrier_{self.agent.agent_id}_{r}_{recoords + 1}"
            self.barrier_timer_id = self.scheduler.schedule(
                delay=sync_wait,
                callback=lambda round_idx=r: self._on_barrier_timeout(round_idx),
                description=f"Sync wait barrier for {self.agent.agent_id} round {r}",
                event_id=ev_id,
            )
        else:
            # Proceed in degraded mode
            self._advance_round()

    def handle_message(self, message: Message) -> None:
        # 1. Schema / Type Validation
        if not isinstance(message, Message):
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "INVALID_REJECTED",
                "agent_id": self.agent.agent_id,
                "payload": {"reason": "Message is not an instance of Message model"},
            })
            return

        # Handle ACKs
        if message.kind == MessageKind.ACK:
            self._handle_ack(message)
            return

        # Handle SYNC_REQ
        if message.kind == MessageKind.SYNC_REQ:
            self._handle_sync_req(message)
            return

        # Handle SYNC_RESP
        if message.kind == MessageKind.SYNC_RESP:
            self._handle_sync_resp(message)
            return

        # Handle DATA
        if message.kind == MessageKind.DATA:
            self._handle_data(message)

    def _handle_ack(self, ack_msg: Message) -> None:
        corr_id = ack_msg.corr_id
        if not corr_id or corr_id not in self.pending_data_acks:
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "ACK_UNMATCHED",
                "agent_id": self.agent.agent_id,
                "target_agent_id": ack_msg.sender,
                "payload": {"corr_id": corr_id, "reason": "No matching pending request or duplicate ACK"},
            })
            return

        entry = self.pending_data_acks[corr_id]
        if ack_msg.sender != entry["receiver"]:
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "ACK_UNMATCHED",
                "agent_id": self.agent.agent_id,
                "target_agent_id": ack_msg.sender,
                "payload": {"corr_id": corr_id, "reason": "Sender did not match expected receiver"},
            })
            return

        # Valid ACK matched! Cancel retry timer
        self.scheduler.cancel(entry["timer_id"])
        latency = self.scheduler.now - entry["sent_at"]
        attempts = entry["attempt"]
        del self.pending_data_acks[corr_id]
        self.degraded_peers.discard(ack_msg.sender)

        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "ACK_RECEIVED",
            "agent_id": self.agent.agent_id,
            "target_agent_id": ack_msg.sender,
            "msg_id": corr_id,
            "payload": {
                "round": ack_msg.round,
                "recovery_latency": latency,
                "attempts_required": attempts,
            },
        })

    def _handle_data(self, message: Message) -> None:
        # Always send ACK back to sender so they can stop retrying
        ack = Message(
            msg_id=f"ack_{uuid.uuid4().hex[:8]}",
            kind=MessageKind.ACK,
            sender=self.agent.agent_id,
            receiver=message.sender,
            task_id=self.task_id,
            run_id=self.run_id,
            round=message.round,
            corr_id=message.msg_id,
        )
        self.channel.send(ack)

        # Duplicate suppression check
        is_duplicate = self._mark_seen(message.msg_id)
        if is_duplicate:
            self.on_event({
                "sim_time": self.scheduler.now,
                "type": "DUP_SUPPRESSED",
                "agent_id": self.agent.agent_id,
                "target_agent_id": message.sender,
                "msg_id": message.msg_id,
                "payload": {"round": message.round},
            })
            return

        # Apply node states with version checks
        self._apply_payload_states(message.payload, message.sender)

        r = message.round
        if r not in self.received_for_round:
            self.received_for_round[r] = set()
        self.received_for_round[r].add(message.sender)

        # Check if barrier reached
        if r == self.current_round and len(self.received_for_round[r]) >= len(self.agent.peers):
            self._advance_round()

    def _apply_payload_states(self, payload: Dict[str, Any], sender_id: str) -> None:
        node_states = payload.get("node_states", {})
        for node_str, state_val in node_states.items():
            node_id = int(node_str)
            if isinstance(state_val, (list, tuple)):
                color, version = state_val[0], state_val[1]
            else:
                color, version = state_val, 1

            if self.enable_version_filter:
                accepted = self.agent.update_neighbor_state(node_id, color, version)
                if not accepted:
                    curr_v = self.agent.neighbor_states[node_id][1]
                    self.on_event({
                        "sim_time": self.scheduler.now,
                        "type": "STALE_REJECTED",
                        "agent_id": self.agent.agent_id,
                        "target_agent_id": sender_id,
                        "payload": {
                            "node_id": node_id,
                            "incoming_version": version,
                            "current_version": curr_v,
                        },
                    })
            else:
                # Without version filter (ablation mode): last arrival overwrites
                self.agent.neighbor_states[node_id] = (color, version)

    def _handle_sync_req(self, message: Message) -> None:
        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "SYNC_REQ",
            "agent_id": self.agent.agent_id,
            "target_agent_id": message.sender,
            "msg_id": message.msg_id,
            "payload": {"requested_by": message.sender, "round": message.round},
        })

        # Respond with authoritative snapshots of all owned nodes
        resp_payload = {
            "node_states": {str(k): (v[0], v[1]) for k, v in self.agent.node_states.items()},
            "current_round": self.current_round,
        }
        resp = Message(
            msg_id=f"sync_resp_{uuid.uuid4().hex[:8]}",
            kind=MessageKind.SYNC_RESP,
            sender=self.agent.agent_id,
            receiver=message.sender,
            task_id=self.task_id,
            run_id=self.run_id,
            round=self.current_round,
            corr_id=message.msg_id,
            payload=resp_payload,
        )
        self.channel.send(resp)

    def _handle_sync_resp(self, message: Message) -> None:
        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "SYNC_RESP",
            "agent_id": self.agent.agent_id,
            "target_agent_id": message.sender,
            "msg_id": message.msg_id,
            "payload": {"round": message.round},
        })

        # Apply snapshot states
        self._apply_payload_states(message.payload, message.sender)

        self.on_event({
            "sim_time": self.scheduler.now,
            "type": "SYNC_APPLIED",
            "agent_id": self.agent.agent_id,
            "target_agent_id": message.sender,
            "payload": {"nodes_reconciled": list(message.payload.get("node_states", {}).keys())},
        })

        r = self.current_round
        if r not in self.received_for_round:
            self.received_for_round[r] = set()
        self.received_for_round[r].add(message.sender)

        if len(self.received_for_round[r]) >= len(self.agent.peers):
            self._advance_round()

    def _advance_round(self) -> None:
        if self.barrier_timer_id:
            self.scheduler.cancel(self.barrier_timer_id)
            self.barrier_timer_id = None

        self.agent.make_decision(self.current_round)
        next_r = self.current_round + 1
        if next_r < self.round_budget:
            self._begin_round(next_r)
        else:
            self.is_finished = True
            self.agent.finished = True
