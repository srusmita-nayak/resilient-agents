import random
import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional

class DecisionResult:
    def __init__(
        self,
        new_colors: Dict[int, int],
        is_fallback: bool = False,
        fallback_reason: Optional[str] = None,
        llm_latency_ms: float = 0.0,
        tokens_used: int = 0,
        prompt_hash: str = "",
        error_class: Optional[str] = None,
    ):
        self.new_colors = new_colors
        self.is_fallback = is_fallback
        self.fallback_reason = fallback_reason
        self.llm_latency_ms = llm_latency_ms
        self.tokens_used = tokens_used
        self.prompt_hash = prompt_hash
        self.error_class = error_class

class AgentPolicy(ABC):
    @abstractmethod
    def decide(
        self,
        agent_id: str,
        owned_nodes: List[int],
        current_colors: Dict[int, int],
        neighbor_colors: Dict[int, int],
        internal_edges: List[Tuple[int, int]],
        boundary_edges: List[Tuple[int, int]],
        num_colors: int,
        round_num: int,
    ) -> DecisionResult:
        pass

class DeterministicPolicy(AgentPolicy):
    """Min-conflict / Distributed Stochastic Algorithm (DSA-B) with seeded PRNG."""
    def __init__(self, seed: int, move_probability: float = 0.8):
        self.rng = random.Random(seed)
        self.move_probability = move_probability

    def decide(
        self,
        agent_id: str,
        owned_nodes: List[int],
        current_colors: Dict[int, int],
        neighbor_colors: Dict[int, int],
        internal_edges: List[Tuple[int, int]],
        boundary_edges: List[Tuple[int, int]],
        num_colors: int,
        round_num: int,
    ) -> DecisionResult:
        new_colors = dict(current_colors)

        # Build adjacency for owned nodes
        adj: Dict[int, List[int]] = {n: [] for n in owned_nodes}
        for u, v in internal_edges:
            if u in adj:
                adj[u].append(v)
            if v in adj:
                adj[v].append(u)
        for u, v in boundary_edges:
            if u in adj:
                adj[u].append(v)
            if v in adj:
                adj[v].append(u)

        for node in owned_nodes:
            curr_c = new_colors.get(node, 0)
            # Count current conflicts
            current_conflicts = 0
            for nbr in adj[node]:
                nbr_c = new_colors.get(nbr) if nbr in new_colors else neighbor_colors.get(nbr)
                if nbr_c is not None and nbr_c == curr_c:
                    current_conflicts += 1

            # If no conflicts, keep current color
            if current_conflicts == 0:
                continue

            # Evaluate conflicts for all candidate colors
            best_conflicts = current_conflicts
            candidates = []
            for c in range(num_colors):
                conflicts = 0
                for nbr in adj[node]:
                    nbr_c = new_colors.get(nbr) if nbr in new_colors else neighbor_colors.get(nbr)
                    if nbr_c is not None and nbr_c == c:
                        conflicts += 1
                if conflicts < best_conflicts:
                    best_conflicts = conflicts
                    candidates = [c]
                elif conflicts == best_conflicts and conflicts < current_conflicts:
                    candidates.append(c)

            # If a strictly better color exists, change with move_probability
            if candidates and self.rng.random() < self.move_probability:
                chosen = self.rng.choice(candidates)
                new_colors[node] = chosen

        return DecisionResult(new_colors=new_colors)

class MockLLMPolicy(AgentPolicy):
    """Scriptable mock LLM policy for automated test suites."""
    def __init__(
        self,
        deterministic_fallback: DeterministicPolicy,
        mode: str = "valid",  # "valid", "rate_limit", "timeout", "malformed_json", "out_of_range"
    ):
        self.fallback = deterministic_fallback
        self.mode = mode

    def decide(
        self,
        agent_id: str,
        owned_nodes: List[int],
        current_colors: Dict[int, int],
        neighbor_colors: Dict[int, int],
        internal_edges: List[Tuple[int, int]],
        boundary_edges: List[Tuple[int, int]],
        num_colors: int,
        round_num: int,
    ) -> DecisionResult:
        prompt_str = f"agent={agent_id},round={round_num},owned={owned_nodes}"
        p_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:12]

        if self.mode == "rate_limit":
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason="RateLimitExceeded: 429 quota exhausted",
                llm_latency_ms=12.0,
                tokens_used=15,
                prompt_hash=p_hash,
                error_class="RateLimitError",
            )
        elif self.mode == "timeout":
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason="Timeout: call exceeded 10.0s deadline",
                llm_latency_ms=10000.0,
                tokens_used=0,
                prompt_hash=p_hash,
                error_class="TimeoutError",
            )
        elif self.mode == "malformed_json":
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason="JSONDecodeError: Unparseable LLM output",
                llm_latency_ms=45.0,
                tokens_used=30,
                prompt_hash=p_hash,
                error_class="MalformedOutputError",
            )
        elif self.mode == "out_of_range":
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason="ConstraintViolation: Proposed color 99 exceeds num_colors",
                llm_latency_ms=50.0,
                tokens_used=28,
                prompt_hash=p_hash,
                error_class="InvalidColorError",
            )
        else: # "valid"
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=False,
                llm_latency_ms=65.0,
                tokens_used=42,
                prompt_hash=p_hash,
            )
