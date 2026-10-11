from typing import Dict, List, Tuple, Optional, Any
from app.agents.policies import AgentPolicy, DecisionResult

class Agent:
    """Distributed agent owning a subset of graph nodes with monotonic version tracking."""
    def __init__(
        self,
        agent_id: str,
        role: str,
        owned_nodes: List[int],
        initial_colors: Dict[int, int],
        internal_edges: List[Tuple[int, int]],
        boundary_edges: List[Tuple[int, int]],
        num_colors: int,
        peers: List[str],
        policy: AgentPolicy,
    ):
        self.agent_id = agent_id
        self.role = role
        self.owned_nodes = sorted(owned_nodes)
        self.num_colors = num_colors
        self.peers = peers
        self.policy = policy
        self.current_round = 0
        self.finished = False

        # Monotonic local states: node_id -> (color, version)
        self.node_states: Dict[int, Tuple[int, int]] = {
            node: (initial_colors.get(node, 0), 1) for node in self.owned_nodes
        }
        # Monotonic neighbor states: node_id -> (color, version)
        self.neighbor_states: Dict[int, Tuple[int, int]] = {}

        self.internal_edges = internal_edges
        self.boundary_edges = boundary_edges
        self.llm_decisions: List[DecisionResult] = []

    def get_owned_colors(self) -> Dict[int, int]:
        return {n: self.node_states[n][0] for n in self.owned_nodes}

    def get_owned_versions(self) -> Dict[int, int]:
        return {n: self.node_states[n][1] for n in self.owned_nodes}

    def get_owned_snapshots(self) -> Dict[str, Tuple[int, int]]:
        """Returns string-keyed snapshots for JSON serialization: str(node) -> (color, version)."""
        return {str(n): self.node_states[n] for n in self.owned_nodes}

    def update_neighbor_state(self, node_id: int, color: int, version: int) -> bool:
        """Applies version check for neighbor node. Returns True if accepted, False if stale."""
        current = self.neighbor_states.get(node_id)
        if current is not None:
            curr_c, curr_v = current
            if version <= curr_v:
                return False  # Stale update
        self.neighbor_states[node_id] = (color, version)
        return True

    def make_decision(self, round_num: int) -> DecisionResult:
        """Computes recoloring based on current policy."""
        curr_colors = self.get_owned_colors()
        nbr_colors = {k: v[0] for k, v in self.neighbor_states.items()}
        res = self.policy.decide(
            agent_id=self.agent_id,
            owned_nodes=self.owned_nodes,
            current_colors=curr_colors,
            neighbor_colors=nbr_colors,
            internal_edges=self.internal_edges,
            boundary_edges=self.boundary_edges,
            num_colors=self.num_colors,
            round_num=round_num,
        )
        self.llm_decisions.append(res)
        
        # Apply decisions to local state with monotonically incremented versions
        for node, new_color in res.new_colors.items():
            if node in self.node_states:
                old_color, old_version = self.node_states[node]
                if new_color != old_color:
                    self.node_states[node] = (new_color, old_version + 1)
                else:
                    self.node_states[node] = (new_color, old_version)
        return res
