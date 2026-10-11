import pytest
from app.metrics.statistics import (
    wilson_score_interval,
    mcnemar_exact_test,
    calculate_median_and_iqr,
    bootstrap_confidence_interval,
)

def test_wilson_score_interval_properties():
    # 0 successes out of 10
    p, low, high = wilson_score_interval(0, 10)
    assert p == 0.0
    assert low == 0.0
    assert 0.0 < high < 0.35

    # 10 successes out of 10
    p, low, high = wilson_score_interval(10, 10)
    assert p == 1.0
    assert 0.65 < low < 1.0
    assert high == 1.0

    # 50 out of 100
    p, low, high = wilson_score_interval(50, 100)
    assert p == 0.5
    assert 0.39 < low < 0.41
    assert 0.59 < high < 0.61

def test_mcnemar_exact_test():
    # Synthetic paired outcomes: Mode A fails while Mode B succeeds on 10 pairs; concordant on others
    pairs = [(False, True)] * 10 + [(True, True)] * 15 + [(False, False)] * 5
    res = mcnemar_exact_test(pairs)
    assert res["total_pairs"] == 30
    assert res["contingency_table"]["b_only_A"] == 0
    assert res["contingency_table"]["c_only_B"] == 10
    # Exact binomial p-value for (0, 10) with p=0.5 is 2 * (0.5^10) ~ 0.00195 < 0.05
    assert res["is_significant_05"] is True
    assert res["p_value"] < 0.01

def test_median_and_iqr():
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    med, q25, q75 = calculate_median_and_iqr(vals)
    assert med == 30.0
    assert q25 == 20.0
    assert q75 == 40.0

def test_bootstrap_confidence_interval():
    vals = [10.0, 12.0, 11.0, 10.5, 11.5]
    mean_val, low, high = bootstrap_confidence_interval(vals, num_samples=500, seed=42)
    assert 10.5 < mean_val < 11.5
    assert low <= mean_val <= high
