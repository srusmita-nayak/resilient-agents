# Metrics & Measurement Formulations

This document specifies the exact mathematical and operational definitions of all metrics computed across simulation runs.

---

## 1. Run Outcome Classification

Every run concludes with an immutable status and outcome:

- **Valid Solution (`valid`):** The final global node coloring is evaluated by the independent validator (`app/problems/validator.py`). All nodes must be colored within valid bounds $[0, num\_colors - 1]$ and all graph edges $(u, v) \in E$ must satisfy $color(u) \ne color(v)$ (violation count = 0).
- **Invalid Solution (`invalid`):** The simulation completed its round budget, but the independent validator detected at least one conflicting edge violation.
- **Deadlock / Coordination Stall (`deadlock` / `stall`):**
  - **Deadlock:** The discrete-event queue has no remaining scheduled events, but at least one agent has not reached `round_budget` or completed coordination.
  - **Coordination Stall:** The simulation exceeded `max_events` or `max_sim_time` without all agents finishing.
- **Cancelled / Interrupted (`cancelled` / `interrupted`):** Simulation halted by user cancellation request or server restart.

---

## 2. Temporal Metrics

The platform distinguishes three separate measures of time:

1. **Virtual Simulated Time ($t_{sim}$):** Normalized discrete virtual clock units tracked by the priority queue scheduler. Independent of host CPU performance.
2. **Physical Wall-Clock Runtime ($t_{wall}$):** Measured in milliseconds via `time.perf_counter()`. Reflects the real CPU execution time on the Windows host.
3. **Network Transport Latency:** Real measured socket transmission time for optional UDP transport experiments.

---

## 3. Communication & Resilience Formulations

### Message Overhead Ratio
Measures the bandwidth cost of resilience mechanisms relative to baseline:
$$\text{Overhead Ratio} = \frac{\bar{M}_{\text{Mode C}}}{\bar{M}_{\text{Mode A}}}$$
where $\bar{M}$ is the sample mean of total messages dispatched per seed.

### Recovery Success Rate
Measures the effectiveness of exponential backoff retries and snapshot sync in salvaging dropped or unacknowledged messages:
$$\text{Recovery Rate} = \frac{|\mathcal{M}_{recovered}|}{|\mathcal{M}_{needing\_recovery}|}$$
- $\mathcal{M}_{needing\_recovery}$: Set of message IDs that experienced a `DROP` or `TIMEOUT` event.
- $\mathcal{M}_{recovered}$: Subset of $\mathcal{M}_{needing\_recovery}$ that ultimately received a correlated `ACK_RECEIVED` or `SYNC_APPLIED`.

### Mean Recovery Latency
The average virtual simulation delay between the initial dispatch of a message that suffered a fault and the arrival of its correlated acknowledgment:
$$\bar{\tau}_{rec} = \frac{1}{|\mathcal{M}_{recovered}|} \sum_{m \in \mathcal{M}_{recovered}} (t_{ack}(m) - t_{first\_send}(m))$$

---

## 4. Aggregate Statistical Formulations

- **Point Estimate of Valid Rate:** $\hat{p} = \frac{k}{n}$, where $k$ is the count of independently validated runs and $n$ is total runs.
- **Wilson 95% Confidence Interval:** Asymmetric binomial interval accounting for edge cases near $0$ and $1$.
- **Median & Interquartile Range (IQR):** $Q_{50}$ with $\text{IQR} = Q_{75} - Q_{25}$, providing non-parametric summaries of skewed simulation times.
- **Discordant Pairs ($b, c$):** Number of seeds where Mode A succeeds and Mode C fails ($b$), versus where Mode A fails and Mode C succeeds ($c$).
