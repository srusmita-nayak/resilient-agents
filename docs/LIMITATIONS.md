# Platform Limitations & Threats to Validity

In adherence to Non-Negotiable Research Integrity Rules, this document explicitly records the engineering limitations, theoretical assumptions, and threats to scientific validity of the Resilient Agents platform.

---

## 1. Physical vs. Software-Emulated Networks
- **Limitation:** All primary experiments execute inside a deterministic discrete-event simulation scheduler running within a single Python process on Windows.
- **Threat to Validity:** Software fault injection (loss, jitter, reordering, partition) models ideal mathematical distributions and does not capture physical Ethernet cable degradation, OS kernel socket buffer exhaustion, network interface card (NIC) drops, or physical router queue contention.
- **Labeling Standard:** All benchmark figures and exports in this platform are labeled as **"software-emulated faults"**.

---

## 2. Deterministic vs. LLM Agent Findings
- **Limitation:** Deterministic min-conflict agents and LLM agents utilize distinct decision policies.
- **Threat to Validity:** Experimental results obtained with deterministic agents demonstrate the impact of communication protocols (ACKs, retries, versioning) on distributed constraint coordination. They **cannot** be cited as evidence of LLM-specific reasoning improvements or prompt robustness.
- **Labeling Standard:** Every run and chart row is labeled with its explicit `agent_type` (`deterministic` or `llm`).

---

## 3. Benchmark Problem Domain
- **Limitation:** The core benchmark is Distributed Graph Coloring (DCR) with planted solvable solutions.
- **Threat to Validity:** While graph coloring is a standard NP-complete benchmark for distributed constraint optimization, real-world multi-agent workflows often involve open-ended multi-turn dialogue, continuous parameter optimization, or heterogeneous tool-use pipelines. The findings here primarily apply to discrete distributed constraint satisfaction.

---

## 4. Agent Scale and Network Topologies
- **Limitation:** Tested configurations range from 3 to 10 agents with 12 to 100 graph nodes.
- **Threat to Validity:** The current communication layer models all-to-all boundary connectivity. Scalability to hundreds or thousands of decentralized agents would require hierarchical routing or gossip protocols (e.g., PlumTree, Kademlia).

---

## 5. Untested & Partial Modules
- **Real Localhost UDP Transport (`transport_udp`):** While virtual channel discrete simulation is fully tested and verified across 32 unit tests and 5 suites, multi-process physical UDP socket transport across distinct physical machines is marked **UNTESTED** in the current prototype.
