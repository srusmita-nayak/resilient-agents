import pytest
from app.core.clock import DiscreteEventScheduler
from app.core.faults import FaultConfig, FaultInjector, PartitionWindow
from app.core.channel import VirtualChannel
from app.core.messages import Message, MessageKind

def test_discrete_event_scheduler_ordering_and_cancellation():
    scheduler = DiscreteEventScheduler()
    log = []

    scheduler.schedule(5.0, lambda: log.append("event_5"), description="ev5")
    scheduler.schedule(2.0, lambda: log.append("event_2"), description="ev2")
    ev3_id = scheduler.schedule(3.0, lambda: log.append("event_3"), description="ev3")
    scheduler.schedule(1.0, lambda: log.append("event_1"), description="ev1")

    # Cancel event at 3.0
    cancelled = scheduler.cancel(ev3_id)
    assert cancelled is True

    # Process all
    while scheduler.step():
        pass

    assert log == ["event_1", "event_2", "event_5"]
    assert scheduler.now == 5.0
    assert scheduler.events_processed == 3

def test_fault_injector_reproducibility():
    cfg = FaultConfig(loss_rate=0.3, min_latency=1.0, max_latency=3.0, jitter=0.5, reorder_rate=0.2)
    inj1 = FaultInjector(cfg, seed=123)
    inj2 = FaultInjector(cfg, seed=123)
    inj3 = FaultInjector(cfg, seed=999)

    seq1 = [inj1.should_drop("a0", "a1", 0.0)[0] for _ in range(50)]
    seq2 = [inj2.should_drop("a0", "a1", 0.0)[0] for _ in range(50)]
    seq3 = [inj3.should_drop("a0", "a1", 0.0)[0] for _ in range(50)]

    assert seq1 == seq2, "Identical seeds must yield identical drop decisions"
    assert seq1 != seq3, "Different seeds must yield different drop decisions"

def test_partition_window_fault():
    cfg = FaultConfig(
        partitions=[PartitionWindow(start_time=10.0, duration=20.0, isolated_agents=["agent_1"])]
    )
    inj = FaultInjector(cfg, seed=42)

    # Before partition
    drop, _ = inj.should_drop("agent_0", "agent_1", 5.0)
    assert drop is False

    # During partition affecting agent_1
    drop, reason = inj.should_drop("agent_0", "agent_1", 15.0)
    assert drop is True
    assert reason == "partition"

    # Traffic between unpartitioned agents
    drop_unrelated, _ = inj.should_drop("agent_0", "agent_2", 15.0)
    assert drop_unrelated is False

    # After partition
    drop_after, _ = inj.should_drop("agent_0", "agent_1", 35.0)
    assert drop_after is False

def test_channel_delivery_event_sequence():
    scheduler = DiscreteEventScheduler()
    cfg = FaultConfig(loss_rate=0.0, min_latency=2.0, max_latency=2.0, jitter=0.0)
    inj = FaultInjector(cfg, seed=42)
    events = []

    channel = VirtualChannel(scheduler, inj, on_event=lambda ev: events.append(ev))
    received = []
    channel.register_receiver("agent_1", lambda msg: received.append(msg))

    msg = Message(
        msg_id="m_test",
        kind=MessageKind.DATA,
        sender="agent_0",
        receiver="agent_1",
        task_id="t1",
        run_id="r1",
        round=0,
    )
    channel.send(msg)

    assert len(events) == 1
    assert events[0]["type"] == "SEND"

    # Step to delivery
    scheduler.step()
    assert len(received) == 1
    assert received[0].msg_id == "m_test"
    assert len(events) == 2
    assert events[1]["type"] == "DELIVER"
    assert scheduler.now == 2.0
