import pytest
from app.agents.policies import DeterministicPolicy, MockLLMPolicy
from app.agents.llm_adapter import GeminiLLMPolicy

def test_mock_llm_policy_valid_proposal():
    det = DeterministicPolicy(seed=42)
    mock_policy = MockLLMPolicy(deterministic_fallback=det, mode="valid")

    res = mock_policy.decide(
        agent_id="agent_0",
        owned_nodes=[0, 1],
        current_colors={0: 0, 1: 0},
        neighbor_colors={2: 0},
        internal_edges=[(0, 1)],
        boundary_edges=[(1, 2)],
        num_colors=3,
        round_num=1,
    )
    assert res.is_fallback is False
    assert 0 in res.new_colors
    assert 1 in res.new_colors
    assert res.tokens_used > 0

def test_mock_llm_rate_limit_fallback():
    det = DeterministicPolicy(seed=42)
    mock_policy = MockLLMPolicy(deterministic_fallback=det, mode="rate_limit")

    res = mock_policy.decide(
        agent_id="agent_0",
        owned_nodes=[0],
        current_colors={0: 0},
        neighbor_colors={1: 0},
        internal_edges=[],
        boundary_edges=[(0, 1)],
        num_colors=3,
        round_num=1,
    )
    assert res.is_fallback is True
    assert "RateLimitExceeded" in res.fallback_reason
    assert res.error_class == "RateLimitError"
    # Deterministic fallback produced a valid color
    assert res.new_colors[0] in [0, 1, 2]

def test_mock_llm_malformed_json_fallback():
    det = DeterministicPolicy(seed=42)
    mock_policy = MockLLMPolicy(deterministic_fallback=det, mode="malformed_json")

    res = mock_policy.decide(
        agent_id="agent_0",
        owned_nodes=[0],
        current_colors={0: 0},
        neighbor_colors={},
        internal_edges=[],
        boundary_edges=[],
        num_colors=3,
        round_num=1,
    )
    assert res.is_fallback is True
    assert "JSONDecodeError" in res.fallback_reason
    assert res.error_class == "MalformedOutputError"

def test_gemini_adapter_budget_exhaustion():
    det = DeterministicPolicy(seed=42)
    # Budget of 2 calls
    gemini_policy = GeminiLLMPolicy(
        api_key="fake_key_for_budget_test",
        model_name="gemini-2.5-flash",
        call_budget=2,
        deterministic_fallback=det,
    )
    # Manually set calls made to 2
    gemini_policy.calls_made = 2

    res = gemini_policy.decide(
        agent_id="agent_0",
        owned_nodes=[0],
        current_colors={0: 0},
        neighbor_colors={},
        internal_edges=[],
        boundary_edges=[],
        num_colors=3,
        round_num=3,
    )
    assert res.is_fallback is True
    assert "CallBudgetExhausted" in res.fallback_reason
    assert res.error_class == "BudgetExhaustedError"
