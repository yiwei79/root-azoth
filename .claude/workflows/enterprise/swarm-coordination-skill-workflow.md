# Swarm coordination — workflow index

**Skill:** `.agents/skills/swarm-coordination/SKILL.md`

| Workflow | Path | Use when |
|----------|------|----------|
| **E2E swarm + eval iteration (0.9, isolated evaluators)** | [`e2e-swarm-eval-loop.md`](./e2e-swarm-eval-loop.md) | Multi-branch delivery, iterate until eval ≥ 0.9 with **no author–evaluator bias** |
| **Queen / worker fan-out** | See skill **Iron Laws** and **Advanced parallelism** | Parallel independent tasks in **one** orchestrator message |

For massively parallel refactors or enterprise topologies, extend waves per `e2e-swarm-eval-loop.md` and keep fan-out ≤ 7 per wave.
