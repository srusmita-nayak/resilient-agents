import hashlib
import json
import time
from typing import Dict, List, Tuple, Optional
from app.agents.policies import AgentPolicy, DecisionResult, DeterministicPolicy
from app.config import settings

class GeminiLLMPolicy(AgentPolicy):
    """Adapter for Google Gemini LLM with structured output, budget enforcement, and deterministic fallback."""
    def __init__(
        self,
        api_key: str,
        model_name: str,
        call_budget: int,
        deterministic_fallback: DeterministicPolicy,
        timeout_seconds: float = 10.0,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.call_budget = call_budget
        self.calls_made = 0
        self.fallback = deterministic_fallback
        self.timeout_seconds = timeout_seconds
        self._cache: Dict[str, Dict[int, int]] = {}

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
        # 1. Budget enforcement
        if self.calls_made >= self.call_budget:
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason="CallBudgetExhausted: Max configured LLM calls reached",
                prompt_hash="budget_exhausted",
                error_class="BudgetExhaustedError",
            )

        # 2. Check API key presence
        if not self.api_key or self.api_key.strip() == "":
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason="MissingApiKey: No GEMINI_API_KEY provided",
                prompt_hash="no_key",
                error_class="MissingApiKeyError",
            )

        # 3. Construct prompt
        prompt_payload = {
            "task": "distributed_graph_coloring",
            "agent_id": agent_id,
            "owned_nodes": owned_nodes,
            "current_colors": {str(k): v for k, v in current_colors.items() if k in owned_nodes},
            "neighbor_colors": {str(k): v for k, v in neighbor_colors.items()},
            "internal_edges": [[u, v] for u, v in internal_edges],
            "boundary_edges": [[u, v] for u, v in boundary_edges],
            "num_colors": num_colors,
            "rules": f"Assign each owned node an integer color from 0 to {num_colors - 1} that minimizes conflicts with neighbors.",
        }
        prompt_str = json.dumps(prompt_payload, sort_keys=True)
        prompt_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:16]

        # Check replay cache
        if prompt_hash in self._cache:
            return DecisionResult(
                new_colors=self._cache[prompt_hash],
                is_fallback=False,
                llm_latency_ms=1.0,
                tokens_used=0,
                prompt_hash=prompt_hash,
            )

        self.calls_made += 1
        t_start = time.perf_counter()

        try:
            # Import google-genai or use httpx to Gemini REST API
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            sys_instruction = (
                "You are an agent solving distributed graph coloring. Output strictly a JSON object "
                "with a 'coloring' key mapping node ID (as string) to integer color. Example: {\"coloring\": {\"0\": 1, \"1\": 2}}"
            )
            req_body = {
                "contents": [{"parts": [{"text": f"{sys_instruction}\nProblem input:\n{prompt_str}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2,
                },
            }

            resp = httpx.post(url, json=req_body, timeout=self.timeout_seconds)
            latency_ms = (time.perf_counter() - t_start) * 1000.0

            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:120]}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Empty response candidates from Gemini")

            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            parsed = json.loads(content_text)
            raw_coloring = parsed.get("coloring", {})

            # Validate and clamp output
            validated_colors = dict(current_colors)
            for node in owned_nodes:
                val = raw_coloring.get(str(node))
                if isinstance(val, int) and 0 <= val < num_colors:
                    validated_colors[node] = val
                else:
                    raise ValueError(f"Invalid color {val} proposed for node {node}")

            self._cache[prompt_hash] = validated_colors
            tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 50)

            return DecisionResult(
                new_colors=validated_colors,
                is_fallback=False,
                llm_latency_ms=latency_ms,
                tokens_used=tokens_used,
                prompt_hash=prompt_hash,
            )

        except Exception as ex:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            error_class = type(ex).__name__
            # Fall back to deterministic policy
            res = self.fallback.decide(agent_id, owned_nodes, current_colors, neighbor_colors, internal_edges, boundary_edges, num_colors, round_num)
            return DecisionResult(
                new_colors=res.new_colors,
                is_fallback=True,
                fallback_reason=f"{error_class}: {str(ex)[:100]}",
                llm_latency_ms=latency_ms,
                tokens_used=0,
                prompt_hash=prompt_hash,
                error_class=error_class,
            )
