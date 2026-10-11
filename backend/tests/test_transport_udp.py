"""Tests for Real Localhost UDP Socket Transport."""

import time
import pytest
from app.core.messages import Message, MessageKind
from app.core.transport_udp import (
    UDPTransportEndpoint,
    UDPChannelManager,
    serialize_message,
    deserialize_message,
)


def test_endpoint_bind_and_cleanup():
    ep = UDPTransportEndpoint(endpoint_id="agent_test", host="127.0.0.1", port=0)
    try:
        assert ep.port > 0
        assert ep.address == ("127.0.0.1", ep.port)
        ep.start()
        assert ep.is_running is True
    finally:
        ep.stop()
        assert ep.is_running is False


def test_message_serialization_roundtrip():
    msg = Message(
        msg_id="msg_udp_001",
        kind=MessageKind.DATA,
        sender="agent_0",
        receiver="agent_1",
        task_id="task_plant_1",
        run_id="run_udp_test",
        round=3,
        payload={"0": 1, "1": 2, "snapshot": {"v": 4}},
        corr_id="corr_999",
        attempt=2,
        sent_at=12.5,
    )
    raw_bytes = serialize_message(msg)
    assert isinstance(raw_bytes, bytes)
    assert len(raw_bytes) > 0

    reconstructed = deserialize_message(raw_bytes)
    assert reconstructed.msg_id == "msg_udp_001"
    assert reconstructed.kind == MessageKind.DATA
    assert reconstructed.sender == "agent_0"
    assert reconstructed.receiver == "agent_1"
    assert reconstructed.round == 3
    assert reconstructed.payload == {"0": 1, "1": 2, "snapshot": {"v": 4}}
    assert reconstructed.corr_id == "corr_999"
    assert reconstructed.attempt == 2
    assert reconstructed.sent_at == 12.5


def test_direct_endpoint_to_endpoint_udp_transmission():
    received_at_b = []
    received_at_a = []

    ep_a = UDPTransportEndpoint(
        endpoint_id="agent_a",
        host="127.0.0.1",
        port=0,
        on_message=lambda msg, addr: received_at_a.append((msg, addr)),
    )
    ep_b = UDPTransportEndpoint(
        endpoint_id="agent_b",
        host="127.0.0.1",
        port=0,
        on_message=lambda msg, addr: received_at_b.append((msg, addr)),
    )

    try:
        ep_a.start()
        ep_b.start()

        # Send A -> B
        data_msg = Message(
            msg_id="msg_ab_1",
            kind=MessageKind.DATA,
            sender="agent_a",
            receiver="agent_b",
            task_id="task_1",
            run_id="run_1",
            round=1,
            payload={"color": 2},
        )
        dispatch_ms = ep_a.send_message("127.0.0.1", ep_b.port, data_msg)
        assert dispatch_ms >= 0.0

        # Wait for delivery
        timeout = time.time() + 2.0
        while len(received_at_b) == 0 and time.time() < timeout:
            time.sleep(0.01)

        assert len(received_at_b) == 1
        msg_b, addr_b = received_at_b[0]
        assert msg_b.msg_id == "msg_ab_1"
        assert msg_b.sender == "agent_a"
        assert msg_b.payload == {"color": 2}
        assert addr_b[0] == "127.0.0.1"

        # Send ACK B -> A
        ack_msg = Message(
            msg_id="ack_ba_1",
            kind=MessageKind.ACK,
            sender="agent_b",
            receiver="agent_a",
            task_id="task_1",
            run_id="run_1",
            round=1,
            corr_id="msg_ab_1",
        )
        ep_b.send_message("127.0.0.1", ep_a.port, ack_msg)

        timeout = time.time() + 2.0
        while len(received_at_a) == 0 and time.time() < timeout:
            time.sleep(0.01)

        assert len(received_at_a) == 1
        msg_a, _ = received_at_a[0]
        assert msg_a.kind == MessageKind.ACK
        assert msg_a.corr_id == "msg_ab_1"

    finally:
        ep_a.stop()
        ep_b.stop()


def test_channel_manager_multi_agent_routing():
    received = {}

    with UDPChannelManager() as manager:
        for aid in ["agent_0", "agent_1", "agent_2"]:
            received[aid] = []
            manager.register_agent(
                aid,
                on_message=lambda m, a=aid: received[a].append(m),
            )

        # Route messages
        m1 = Message(
            msg_id="m1",
            kind=MessageKind.DATA,
            sender="agent_0",
            receiver="agent_1",
            task_id="t",
            run_id="r",
        )
        m2 = Message(
            msg_id="m2",
            kind=MessageKind.DATA,
            sender="agent_1",
            receiver="agent_2",
            task_id="t",
            run_id="r",
        )
        m3 = Message(
            msg_id="m3",
            kind=MessageKind.DATA,
            sender="agent_2",
            receiver="agent_0",
            task_id="t",
            run_id="r",
        )

        manager.route_message(m1)
        manager.route_message(m2)
        manager.route_message(m3)

        # Wait for all deliveries
        timeout = time.time() + 2.0
        while (
            (len(received["agent_0"]) < 1 or len(received["agent_1"]) < 1 or len(received["agent_2"]) < 1)
            and time.time() < timeout
        ):
            time.sleep(0.01)

        assert len(received["agent_0"]) == 1
        assert received["agent_0"][0].sender == "agent_2"

        assert len(received["agent_1"]) == 1
        assert received["agent_1"][0].sender == "agent_0"

        assert len(received["agent_2"]) == 1
        assert received["agent_2"][0].sender == "agent_1"

        stats = manager.get_stats()
        assert stats["endpoint_count"] == 3
        assert stats["total_messages_sent"] == 3
        assert stats["total_messages_received"] == 3
        assert stats["total_bytes_sent"] > 0


def test_malformed_datagram_handling():
    valid_received = []

    ep_receiver = UDPTransportEndpoint(
        endpoint_id="agent_rx",
        host="127.0.0.1",
        port=0,
        on_message=lambda m, addr: valid_received.append(m),
    )
    ep_sender = UDPTransportEndpoint(
        endpoint_id="agent_tx",
        host="127.0.0.1",
        port=0,
    )

    try:
        ep_receiver.start()
        ep_sender.start()

        # 1. Send corrupted/garbage data
        garbage = b"\x00\xff\xfeNotAValidJsonMessage1234"
        ep_sender.send_raw("127.0.0.1", ep_receiver.port, garbage)
        time.sleep(0.1)

        # Receiver should not have registered a valid message
        assert len(valid_received) == 0

        # 2. Immediately send a valid message; receiver must still be operational
        valid_msg = Message(
            msg_id="recovered_msg",
            kind=MessageKind.DATA,
            sender="agent_tx",
            receiver="agent_rx",
            task_id="t",
            run_id="r",
            payload={"status": "recovered"},
        )
        ep_sender.send_message("127.0.0.1", ep_receiver.port, valid_msg)

        timeout = time.time() + 2.0
        while len(valid_received) == 0 and time.time() < timeout:
            time.sleep(0.01)

        assert len(valid_received) == 1
        assert valid_received[0].msg_id == "recovered_msg"
        assert valid_received[0].payload == {"status": "recovered"}

    finally:
        ep_receiver.stop()
        ep_sender.stop()
