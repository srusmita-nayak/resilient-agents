import random
from typing import Dict, List, Set, Tuple
from pydantic import BaseModel, Field

class GraphColoringInstance(BaseModel):
    task_id: str
    num_agents: int
    num_nodes: int
    num_colors: int
    edges: List[Tuple[int, int]]
    agent_nodes: Dict[str, List[int]]  # agent_id -> list of node_ids
    planted_solution: Dict[int, int]   # node_id -> valid color
    boundary_edges: List[Tuple[int, int]] # edges crossing agent boundaries
    round_budget: int

def generate_graph_coloring_instance(
    task_id: str,
    num_agents: int = 3,
    num_nodes: int = 15,
    num_colors: int = 3,
    edge_density: float = 0.3,
    round_budget: int = 30,
    seed: int = 42,
) -> GraphColoringInstance:
    """Generates a distributed graph coloring instance with a guaranteed planted valid solution."""
    rng = random.Random(seed)
    
    # 1. Generate planted solution (ensures the instance is always mathematically solvable)
    planted: Dict[int, int] = {node_id: rng.randint(0, num_colors - 1) for node_id in range(num_nodes)}
    
    # Ensure all colors are represented if possible
    for c in range(min(num_colors, num_nodes)):
        planted[c] = c

    # 2. Assign nodes evenly to agents
    agent_ids = [f"agent_{i}" for i in range(num_agents)]
    agent_nodes: Dict[str, List[int]] = {aid: [] for aid in agent_ids}
    for node_id in range(num_nodes):
        target_agent = agent_ids[node_id % num_agents]
        agent_nodes[target_agent].append(node_id)

    # Invert mapping: node_id -> agent_id
    node_to_agent: Dict[int, str] = {}
    for aid, nodes in agent_nodes.items():
        for n in nodes:
            node_to_agent[n] = aid

    # 3. Generate candidate edges consistent with the planted solution (no edges between same planted color)
    edges: List[Tuple[int, int]] = []
    boundary_edges: List[Tuple[int, int]] = []
    
    all_pairs = []
    for u in range(num_nodes):
        for v in range(u + 1, num_nodes):
            if planted[u] != planted[v]:  # Only add edges that respect planted coloring
                all_pairs.append((u, v))

    rng.shuffle(all_pairs)
    target_edge_count = int(len(all_pairs) * edge_density)
    # Ensure graph is connected enough by taking at least a spanning set if possible
    selected_edges = all_pairs[:max(target_edge_count, num_nodes)]

    for u, v in selected_edges:
        edges.append((u, v))
        if node_to_agent[u] != node_to_agent[v]:
            boundary_edges.append((u, v))

    return GraphColoringInstance(
        task_id=task_id,
        num_agents=num_agents,
        num_nodes=num_nodes,
        num_colors=num_colors,
        edges=edges,
        agent_nodes=agent_nodes,
        planted_solution=planted,
        boundary_edges=boundary_edges,
        round_budget=round_budget,
    )

DIFFICULTY_PRESETS = {
    "easy": {
        "num_agents": 3,
        "num_nodes": 12,
        "num_colors": 3,
        "edge_density": 0.25,
        "round_budget": 25,
    },
    "medium": {
        "num_agents": 4,
        "num_nodes": 20,
        "num_colors": 3,
        "edge_density": 0.35,
        "round_budget": 35,
    },
    "hard": {
        "num_agents": 5,
        "num_nodes": 35,
        "num_colors": 3,
        "edge_density": 0.50,
        "round_budget": 40,
    },
}
