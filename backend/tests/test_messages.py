import pytest
from pydantic import ValidationError
from app.core.messages import Message, MessageKind

def test_message_creation_and_validation():
    msg = Message(
        msg_id="msg_001",
        kind=MessageKind.DATA,
        sender="agent_0",
        receiver="agent_1",
        task_id="task_1",
        run_id="run_1",
        round=0,
        payload={"node_states": {"0": [1, 1]}},
        attempt=1,
        sent_at=0.0,
    )
    assert msg.msg_id == "msg_001"
    assert msg.kind == MessageKind.DATA
    assert msg.attempt == 1
    assert msg.schema_version == "1.0"

def test_message_missing_fields_validation_error():
    with pytest.raises(ValidationError):
        # Missing required fields
        Message(msg_id="bad_msg")

def test_ack_message_with_corr_id():
    ack = Message(
        msg_id="ack_001",
        kind=MessageKind.ACK,
        sender="agent_1",
        receiver="agent_0",
        task_id="task_1",
        run_id="run_1",
        round=0,
        corr_id="msg_001",
    )
    assert ack.kind == MessageKind.ACK
    assert ack.corr_id == "msg_001"
