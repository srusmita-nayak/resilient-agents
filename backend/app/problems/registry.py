from typing import Any, Dict
from app.problems.graph_coloring import generate_graph_coloring_instance, DIFFICULTY_PRESETS

class ProblemRegistry:
    @staticmethod
    def get_presets() -> Dict[str, Any]:
        return {
            "graph_coloring": DIFFICULTY_PRESETS,
        }

    @staticmethod
    def create_instance(problem_type: str, task_id: str, seed: int, **params: Any) -> Any:
        if problem_type == "graph_coloring":
            return generate_graph_coloring_instance(task_id=task_id, seed=seed, **params)
        raise ValueError(f"Unknown problem type: {problem_type}")
