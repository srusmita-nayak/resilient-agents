from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class ProblemConfigInput(BaseModel):
    problem_type: str = "graph_coloring"
    preset: Optional[str] = "easy"
    num_agents: int = Field(default=3, ge=3, le=10)
    num_nodes: int = Field(default=12, ge=3, le=100)
    num_colors: int = Field(default=3, ge=2, le=10)
    edge_density: float = Field(default=0.25, ge=0.05, le=0.9)
    round_budget: int = Field(default=25, ge=5, le=100)

class PartitionWindowInput(BaseModel):
    start_time: float = Field(ge=0.0)
    duration: float = Field(gt=0.0)
    isolated_agents: Optional[List[str]] = None

class FaultConfigInput(BaseModel):
    loss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    min_latency: float = Field(default=1.0, ge=0.1, le=50.0)
    max_latency: float = Field(default=1.0, ge=0.1, le=50.0)
    jitter: float = Field(default=0.0, ge=0.0, le=10.0)
    duplicate_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    reorder_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    reorder_extra_delay: float = Field(default=5.0, ge=0.0, le=50.0)
    partitions: List[PartitionWindowInput] = Field(default_factory=list)

class MiddlewareConfigInput(BaseModel):
    ack_timeout: float = Field(default=3.0, ge=0.5, le=30.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_factor: float = Field(default=1.5, ge=1.0, le=5.0)
    barrier_timeout: float = Field(default=8.0, ge=1.0, le=60.0)
    round_barrier_timeout: float = Field(default=10.0, ge=1.0, le=60.0)
    max_recoordination_attempts: int = Field(default=2, ge=0, le=5)
    # Toggles
    enable_retransmission: bool = True
    enable_version_filter: bool = True
    enable_sync_recoordination: bool = True

class LimitsInput(BaseModel):
    max_sim_time: float = Field(default=500.0, ge=50.0, le=5000.0)
    max_events: int = Field(default=5000, ge=100, le=50000)
    max_wall_seconds: float = Field(default=30.0, ge=5.0, le=300.0)

class CreateExperimentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    problem: ProblemConfigInput = Field(default_factory=ProblemConfigInput)
    faults: FaultConfigInput = Field(default_factory=FaultConfigInput)
    middleware: MiddlewareConfigInput = Field(default_factory=MiddlewareConfigInput)
    limits: LimitsInput = Field(default_factory=LimitsInput)
    modes: List[str] = Field(default=["baseline", "timeout_baseline", "protected"])
    seeds: List[int] = Field(default=[42])
    include_fault_free_reference: bool = True
    agent_type: str = Field(default="deterministic")  # "deterministic" or "llm"
    provider_model: Optional[str] = "gemini-2.5-flash"
    llm_call_budget: int = Field(default=50, ge=1, le=200)
    mock_llm_mode: Optional[str] = None
    gemini_api_key: Optional[str] = None

class ConnectionTestRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    provider_model: Optional[str] = "gemini-2.5-flash"
