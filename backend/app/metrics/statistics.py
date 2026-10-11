import math
import random
from typing import List, Tuple, Dict, Any, Optional

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """Calculates Wilson score interval for a binomial proportion.
    Returns: (point_estimate, ci_lower, ci_upper)
    """
    if total <= 0:
        return 0.0, 0.0, 0.0

    p = successes / total
    # z-value for 95% confidence is ~1.95996
    z = 1.95996 if abs(confidence - 0.95) < 0.01 else 1.96
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p * (1.0 - p) / total) + (z2 / (4.0 * total * total)))

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return p, lower, upper

def binomial_exact_two_sided_pvalue(b: int, c: int) -> float:
    """Exact two-sided binomial test p-value for discordant pairs b and c (McNemar exact test)."""
    n = b + c
    if n == 0:
        return 1.0

    k = min(b, c)
    # Sum of binomial probabilities for X <= k with p=0.5
    prob_sum = 0.0
    for i in range(k + 1):
        prob_sum += math.comb(n, i) * (0.5 ** n)
    p_val = min(1.0, 2.0 * prob_sum)
    return p_val

def mcnemar_exact_test(
    pairs: List[Tuple[bool, bool]] # (mode_A_success, mode_B_success) for same seeds
) -> Dict[str, Any]:
    """Computes McNemar's exact test on paired binary outcomes.
    Contingency table:
      a: both True
      b: Mode A True, Mode B False
      c: Mode A False, Mode B True
      d: both False
    """
    a = b = c = d = 0
    for outcome_a, outcome_b in pairs:
        if outcome_a and outcome_b:
            a += 1
        elif outcome_a and not outcome_b:
            b += 1
        elif not outcome_a and outcome_b:
            c += 1
        else:
            d += 1

    total = len(pairs)
    p_val = binomial_exact_two_sided_pvalue(b, c)
    rate_a = (a + b) / total if total > 0 else 0.0
    rate_b = (a + c) / total if total > 0 else 0.0
    diff = rate_a - rate_b

    return {
        "total_pairs": total,
        "contingency_table": {"a_both_success": a, "b_only_A": b, "c_only_B": c, "d_both_fail": d},
        "rate_A": rate_a,
        "rate_B": rate_b,
        "difference": diff,
        "p_value": p_val,
        "is_significant_05": p_val < 0.05,
    }

def calculate_median_and_iqr(values: List[float]) -> Tuple[float, float, float]:
    """Returns (median, q25, q75)."""
    if not values:
        return 0.0, 0.0, 0.0
    s = sorted(values)
    n = len(s)

    def _percentile(p: float) -> float:
        idx = p * (n - 1)
        low = int(math.floor(idx))
        high = int(math.ceil(idx))
        if low == high:
            return s[low]
        weight = idx - low
        return s[low] * (1.0 - weight) + s[high] * weight

    return _percentile(0.5), _percentile(0.25), _percentile(0.75)

def bootstrap_confidence_interval(
    values: List[float],
    num_samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Calculates non-parametric bootstrap confidence interval for the mean.
    Returns: (mean, ci_lower, ci_upper)
    """
    if not values:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0], values[0]

    rng = random.Random(seed)
    n = len(values)
    mean_val = sum(values) / n
    boot_means = []

    for _ in range(num_samples):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    alpha = (1.0 - confidence) / 2.0
    low_idx = int(alpha * num_samples)
    high_idx = int((1.0 - alpha) * num_samples)
    ci_lower = boot_means[max(0, low_idx)]
    ci_upper = boot_means[min(num_samples - 1, high_idx)]

    return mean_val, ci_lower, ci_upper
