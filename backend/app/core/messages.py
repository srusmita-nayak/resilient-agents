from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class MessageKind(str, Enum):
    DATA = "DATA"
    ACK = "ACK"
    SYNC_REQ = "SYNC_REQ"
    SYNC_RESP = "SYNC_RESP"
    HEARTBEAT = "HEARTBEAT"

class Message(BaseModel):
    msg_id: str = Field(description="Unique message identifier; preserved across retransmissions")
    kind: MessageKind = Field(description="Protocol message type")
    sender: str = Field(description="Agent identifier of sender")
    receiver: str = Field(description="Agent identifier of target receiver")
    task_id: str = Field(description="Task / problem instance ID")
    run_id: str = Field(description="Experiment run execution ID")
    round: int = Field(default=0, description="Round or epoch number")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Payload data, e.g. node color and version snapshots")
    corr_id: Optional[str] = Field(default=None, description="Correlation ID matching a request msg_id for ACK or SYNC_RESP")
    attempt: int = Field(default=1, description="Transmission attempt counter (1 for first try)")
    sent_at: float = Field(default=0.0, description="Simulated virtual time when message was dispatched")
    schema_version: str = "1.0"

    class Config:
        frozen = False
