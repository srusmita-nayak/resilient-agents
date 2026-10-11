"""Real Localhost UDP Socket Transport Implementation.

Provides real physical network socket transport over UDP loopback (127.0.0.1)
for multi-agent communication, including datagram serialization, asynchronous
receiver loops, socket latency measurement, and clean lifecycle management.
"""

import socket
import threading
import time
import json
import logging
from typing import Dict, Tuple, Optional, Callable, List, Any
from app.core.messages import Message

logger = logging.getLogger(__name__)


def serialize_message(message: Message) -> bytes:
    """Serializes a Message instance to JSON UTF-8 bytes."""
    if hasattr(message, "model_dump_json"):
        return message.model_dump_json().encode("utf-8")
    return message.json().encode("utf-8")


def deserialize_message(data: bytes) -> Message:
    """Deserializes JSON UTF-8 bytes back into a Message instance."""
    text = data.decode("utf-8")
    if hasattr(Message, "model_validate_json"):
        return Message.model_validate_json(text)
    return Message.parse_raw(text)


class UDPTransportEndpoint:
    """Individual UDP socket transport endpoint bound to a localhost port."""

    def __init__(
        self,
        endpoint_id: str,
        host: str = "127.0.0.1",
        port: int = 0,
        on_message: Optional[Callable[[Message, Tuple[str, int]], None]] = None,
        socket_timeout: float = 0.5,
    ):
        self.endpoint_id = endpoint_id
        self.host = host
        self.requested_port = port
        self.on_message = on_message
        self.socket_timeout = socket_timeout

        self._sock: Optional[socket.socket] = None
        self._bound_port: int = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.bytes_sent = 0
        self.bytes_received = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.latency_samples_ms: List[float] = []

        self._bind()

    def _bind(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.requested_port))
        self._sock.settimeout(self.socket_timeout)
        self._bound_port = self._sock.getsockname()[1]

    @property
    def port(self) -> int:
        return self._bound_port

    @property
    def address(self) -> Tuple[str, int]:
        return (self.host, self._bound_port)

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Starts the background receiver thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._receiver_loop,
            name=f"UDPReceiver-{self.endpoint_id}-{self._bound_port}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stops the receiver thread and releases the socket."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def send_message(self, target_host: str, target_port: int, message: Message) -> float:
        """Transmits a Message to target host/port and measures dispatch time."""
        if not self._sock:
            raise RuntimeError(f"Endpoint {self.endpoint_id} socket is closed.")

        data = serialize_message(message)
        t_start = time.perf_counter()
        sent_bytes = self._sock.sendto(data, (target_host, target_port))
        dispatch_ms = (time.perf_counter() - t_start) * 1000.0

        self.bytes_sent += sent_bytes
        self.messages_sent += 1
        return dispatch_ms

    def send_raw(self, target_host: str, target_port: int, raw_data: bytes) -> int:
        """Sends raw bytes to target host/port (useful for error/fault injection testing)."""
        if not self._sock:
            raise RuntimeError(f"Endpoint {self.endpoint_id} socket is closed.")
        sent_bytes = self._sock.sendto(raw_data, (target_host, target_port))
        self.bytes_sent += sent_bytes
        return sent_bytes

    def _receiver_loop(self) -> None:
        """Background loop reading UDP datagrams."""
        while self._running and self._sock:
            try:
                data, addr = self._sock.recvfrom(65535)
                self.bytes_received += len(data)
                try:
                    msg = deserialize_message(data)
                    self.messages_received += 1
                    if self.on_message:
                        self.on_message(msg, addr)
                except Exception as ex:
                    logger.warning(
                        "Endpoint %s received malformed datagram from %s: %s",
                        self.endpoint_id,
                        addr,
                        ex,
                    )
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as ex:
                if self._running:
                    logger.error("Unexpected error in UDP receiver %s: %s", self.endpoint_id, ex)
                break

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class UDPChannelManager:
    """Coordinates localhost UDP endpoints for multiple agents in an experiment."""

    def __init__(self, host: str = "127.0.0.1"):
        self.host = host
        self.endpoints: Dict[str, UDPTransportEndpoint] = {}
        self._message_handlers: Dict[str, Callable[[Message], None]] = {}

    def register_agent(
        self,
        agent_id: str,
        on_message: Optional[Callable[[Message], None]] = None,
        port: int = 0,
    ) -> UDPTransportEndpoint:
        """Creates and starts a UDP endpoint for an agent on localhost."""
        if agent_id in self.endpoints:
            return self.endpoints[agent_id]

        if on_message:
            self._message_handlers[agent_id] = on_message

        def _dispatch(msg: Message, addr: Tuple[str, int]):
            handler = self._message_handlers.get(msg.receiver)
            if handler:
                handler(msg)

        ep = UDPTransportEndpoint(
            endpoint_id=agent_id,
            host=self.host,
            port=port,
            on_message=_dispatch,
        )
        ep.start()
        self.endpoints[agent_id] = ep
        return ep

    def route_message(self, message: Message) -> float:
        """Routes a Message from sender endpoint to receiver endpoint over physical UDP."""
        sender_ep = self.endpoints.get(message.sender)
        receiver_ep = self.endpoints.get(message.receiver)

        if not sender_ep:
            raise KeyError(f"Sender endpoint '{message.sender}' is not registered.")
        if not receiver_ep:
            raise KeyError(f"Receiver endpoint '{message.receiver}' is not registered.")

        target_host, target_port = receiver_ep.address
        return sender_ep.send_message(target_host, target_port, message)

    def get_stats(self) -> Dict[str, Any]:
        """Returns aggregate transport statistics across all endpoints."""
        total_sent = sum(ep.messages_sent for ep in self.endpoints.values())
        total_recv = sum(ep.messages_received for ep in self.endpoints.values())
        total_bytes_sent = sum(ep.bytes_sent for ep in self.endpoints.values())
        total_bytes_recv = sum(ep.bytes_received for ep in self.endpoints.values())
        return {
            "endpoint_count": len(self.endpoints),
            "total_messages_sent": total_sent,
            "total_messages_received": total_recv,
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_recv,
        }

    def close_all(self) -> None:
        """Stops and closes all registered endpoints."""
        for ep in self.endpoints.values():
            ep.stop()
        self.endpoints.clear()
        self._message_handlers.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
