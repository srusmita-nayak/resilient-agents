# Contributing to Resilient Agents Research Platform

Thank you for contributing to the Resilient Agents research platform. We adhere to rigorous scientific integrity, reproducible methodology, and clean software engineering practices.

## Research Integrity Guidelines

1. **Zero Fabrication Policy:** Never fabricate results, metrics, execution traces, or statistical p-values. All numbers reported must originate from real executions stored in the SQLite database.
2. **Honest Labeling:** Clearly designate agent execution policies as `deterministic` or `llm`. Never present deterministic outcomes as LLM evaluations.
3. **Software-Emulated Transport:** Label all simulated network fault experiments as "software-emulated faults" or "virtual discrete-event transport".
4. **Fair Baselines:** Never tune or weaken baselines to flatter the protected mode. Deadlocks, stalls, and timeouts must always be counted as failures in intention-to-treat analysis.
5. **Secret Redaction:** Never commit, log, return over the API, or expose in exports any API keys or credentials.

## Development Workflow

1. Fork or branch from `main`.
2. Ensure you have Python 3.12+ and Node 20+ installed on Windows.
3. Run `.\scripts\setup.ps1` to configure virtual environments and install pinned dependencies.
4. Run `.\scripts\run-tests.ps1` to verify both backend pytest and frontend vitest suites pass before committing.
5. Document any architectural modifications in `docs/DECISIONS.md`.
