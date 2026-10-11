import random
from typing import List, Optional, Tuple, Set
from pydantic import BaseModel, Field

class PartitionWindow(BaseModel):
    start_time: float = Field(description="Simulated start time of network partition")
    duration: float = Field(description="Duration in simulated time")
    isolated_agents: Optional[List[str]] = Field(default=None, description="If None, global partition across all agents; else specific isolated agent IDs")

class FaultConfig(BaseModel):
    loss_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Packet loss probability")
    min_latency: float = Field(default=1.0, ge=0.0, description="Minimum transmission latency in simulated units")
    max_latency: float = Field(default=1.0, ge=0.0, description="Maximum transmission latency in simulated units")
    jitter: float = Field(default=0.0, ge=0.0, description="Random jitter added/subtracted from latency")
    duplicate_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of duplicate packet generation")
    reorder_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of injecting extra delay causing packet reordering")
    reorder_extra_delay: float = Field(default=5.0, ge=0.0, description="Extra delay added when reordering occurs")
    partitions: List[PartitionWindow] = Field(default_factory=list, description="Scheduled network partition windows")

class FaultInjector:
    """Evaluates and injects network faults deterministically using a seeded PRNG."""
    def __init__(self, config: FaultConfig, seed: int):
        self.config = config
        self.seed = seed
        self.rng = random.Random(seed)

    def is_in_partition(self, sender: str, receiver: str, current_time: float) -> bool:
        for p in self.config.partitions:
            if p.start_time <= current_time < (p.start_time + p.duration):
                if p.isolated_agents is None:
                    # Global partition: all inter-agent traffic blocked
                    return True
                # Specific partition: either sender or receiver is in isolated group
                if sender in p.isolated_agents or receiver in p.isolated_agents:
                    return True
        return False

    def should_drop(self, sender: str, receiver: str, current_time: float) -> Tuple[bool, str]:
        if self.is_in_partition(sender, receiver, current_time):
            return True, "partition"
        if self.config.loss_rate > 0.0 and self.rng.random() < self.config.loss_rate:
            return True, "loss"
        return False, ""

    def calculate_latency(self) -> float:
        base = self.rng.uniform(self.config.min_latency, self.config.max_latency)
        if self.config.jitter > 0:
            j = self.rng.uniform(-self.config.jitter, self.config.jitter)
            base = max(0.1, base + j)
        return max(0.1, base)

    def should_reorder(self) -> Tuple[bool, float]:
        if self.config.reorder_rate > 0.0 and self.rng.random() < self.config.reorder_rate:
            return True, self.config.reorder_extra_delay
        return False, 0.0

    def should_duplicate(self) -> bool:
        return self.config.duplicate_rate > 0.0 and self.rng.random() < self.config.duplicate_rate
