# Experimental Methodology & Statistical Framework

## 1. Research Questions & Falsifiable Hypotheses

### Primary Research Question
*How do acknowledgment-based retransmission, monotonic versioning, and snapshot reconciliation mitigate coordination failure and deadlock in multi-agent constraint reasoning over unreliable communication channels, and what is the exact bandwidth overhead incurred?*

### Falsifiable Hypotheses
- **Hypothesis 1 (H1 - Task Success):** Under non-zero packet loss ($p_{loss} \ge 0.25$), Mode C (Protected Middleware) achieves a statistically significantly higher valid solution rate than Mode A (Synchronous Baseline), as evaluated by McNemar's exact test ($p < 0.05$).
- **Hypothesis 2 (H2 - Deadlock Freedom):** Mode A experiences catastrophic deadlocks when communication packets are lost, whereas Mode C and Mode B maintain a 0.0% deadlock rate by utilizing bounded timers and degraded progress mechanisms.
- **Hypothesis 3 (H3 - Communication Overhead):** The resilience guarantees of Mode C require an empirical message overhead of at least $2.0\times$ relative to baseline communication due to explicit point-to-point acknowledgments and retransmissions.

*Note: Results may contradict hypotheses. For instance, in low-to-moderate loss settings ($p_{loss} \le 0.25$), heuristic local search in Mode B can occasionally find valid colorings without waiting for retransmitted boundary updates, matching or slightly exceeding Mode C due to rapid round progression.*

---

## 2. Experimental Design

### 2.1 Paired Within-Subject Structure
To eliminate graph instance difficulty as a confounding variable, every experimental cell evaluates all modes against identical pseudo-random seeds ($S \in \{42, \dots, 71\}$, $n=30$ seeds per cell):
- Identical planted graph topology.
- Identical initial node color assignments.
- Identical sequence of pseudo-random network fault occurrences.

### 2.2 Fault-Free Reference Calibration
Each seed is also executed under an ideal, fault-free channel ($p_{loss} = 0$, fixed latency). This establishes whether any observed failure at the end of the round budget is due to the inherent difficulty of the graph instance or actual communication fault damage.

### 2.3 Intention-to-Treat (ITT) Accounting
Runs that stall, time out, or fail to converge within the allotted virtual time budget are **never** discarded from the dataset. They are preserved in SQLite and strictly categorized as task failures (`validation_valid = 0`).

---

## 3. Statistical Analysis Methods

### 3.1 Proportions: Wilson Score Confidence Interval
For task success rates and deadlock rates ($p = k / n$), we compute the asymmetric Wilson score interval at 95% confidence:
$$CI = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
where $z = 1.95996$.

### 3.2 Paired Binary Comparison: McNemar's Exact Test
When comparing Mode A or Mode B against Mode C across paired seeds, we construct a $2 \times 2$ contingency table of discordant outcomes:
- $b$: Seed where Mode A succeeded and Mode C failed.
- $c$: Seed where Mode A failed and Mode C succeeded.
The exact two-sided p-value is computed from the binomial distribution under null hypothesis $p = 0.5$:
$$p\text{-value} = 2 \sum_{i=0}^{\min(b, c)} \binom{b + c}{i} 0.5^{b+c}$$

### 3.3 Continuous Measures: Seeded Non-Parametric Bootstrap
For continuous metrics (simulated time duration, messages dispatched), we compute 95% empirical bootstrap confidence intervals using 1000 resamples with replacement and a fixed seed (42). We additionally report medians and Interquartile Ranges (IQR).
