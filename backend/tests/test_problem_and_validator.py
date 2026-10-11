import pytest
from app.problems.graph_coloring import generate_graph_coloring_instance
from app.problems.validator import validate_coloring

def test_planted_solution_validity():
    instance = generate_graph_coloring_instance(
        task_id="test_planted",
        num_agents=3,
        num_nodes=15,
        num_colors=3,
        edge_density=0.4,
        seed=101,
    )
    # Validate the planted solution directly
    report = validate_coloring(
        coloring=instance.planted_solution,
        edges=instance.edges,
        total_nodes=instance.num_nodes,
        num_colors=instance.num_colors,
    )
    assert report.is_valid is True
    assert report.violation_count == 0
    assert len(report.uncolored_nodes) == 0

def test_independent_validator_detects_conflicts():
    # Graph with edge (0, 1) and (1, 2)
    edges = [(0, 1), (1, 2)]
    # Adversarial coloring where 0 and 1 have the same color
    bad_coloring = {0: 1, 1: 1, 2: 0}
    report = validate_coloring(
        coloring=bad_coloring,
        edges=edges,
        total_nodes=3,
        num_colors=3,
    )
    assert report.is_valid is False
    assert report.violation_count == 1
    assert (0, 1) in report.conflicting_edges

def test_independent_validator_detects_uncolored_and_out_of_range():
    edges = [(0, 1)]
    # Node 1 is uncolored, node 2 has color 5 (while num_colors=3)
    flawed_coloring = {0: 1, 2: 5}
    report = validate_coloring(
        coloring=flawed_coloring,
        edges=edges,
        total_nodes=3,
        num_colors=3,
    )
    assert report.is_valid is False
    assert 1 in report.uncolored_nodes
    assert 2 in report.invalid_range_nodes
