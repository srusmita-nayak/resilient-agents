from typing import Dict, List, Tuple
from pydantic import BaseModel

class ValidationReport(BaseModel):
    is_valid: bool
    total_nodes: int
    colored_nodes: int
    uncolored_nodes: List[int]
    invalid_range_nodes: List[int]
    total_edges: int
    violation_count: int
    conflicting_edges: List[Tuple[int, int]]

def validate_coloring(
    coloring: Dict[int, int],
    edges: List[Tuple[int, int]],
    total_nodes: int,
    num_colors: int,
) -> ValidationReport:
    """Independent validator checking the mathematical validity of a graph coloring."""
    uncolored = []
    invalid_range = []

    for node in range(total_nodes):
        if node not in coloring or coloring[node] is None:
            uncolored.append(node)
        elif not (0 <= coloring[node] < num_colors):
            invalid_range.append(node)

    conflicting_edges: List[Tuple[int, int]] = []
    for u, v in edges:
        col_u = coloring.get(u)
        col_v = coloring.get(v)
        if col_u is not None and col_v is not None and col_u == col_v:
            conflicting_edges.append((u, v))

    is_valid = (len(uncolored) == 0) and (len(invalid_range) == 0) and (len(conflicting_edges) == 0)

    return ValidationReport(
        is_valid=is_valid,
        total_nodes=total_nodes,
        colored_nodes=len(coloring) - len(uncolored),
        uncolored_nodes=uncolored,
        invalid_range_nodes=invalid_range,
        total_edges=len(edges),
        violation_count=len(conflicting_edges),
        conflicting_edges=conflicting_edges,
    )
