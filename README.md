# agentbench-local

A local benchmark harness for evaluating LLM-based coding agents. Define tasks in YAML, spin up sandboxed workspaces, run agents against them, and collect scored results.

## Directory overview

```
agentbench/          Core library (agent orchestration, tasks, tools, etc.)
tasks/               YAML task definitions (one file per task)
workspaces/          Ephemeral sandboxes created per run
results/             Scored output written after each run
run.py               CLI entry-point
```
