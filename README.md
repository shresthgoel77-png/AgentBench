# agentbench

A local benchmark harness for evaluating LLM-based coding agents. Define tasks in YAML, spin up sandboxed workspaces, run agents against them, and collect scored results.

## Directory overview

```
agentbench/          Core library (agent orchestration, tasks, tools, etc.)
tasks/               YAML task definitions (one file per task, each with a buggy solution + tests)
workspaces/          Ephemeral sandboxes created per run (gitignored)
results/             Scored JSON output written after each run (gitignored)
run.py               CLI entry-point
requirements.txt     Python dependencies
.env.example         Template for environment variables
pytest.ini           Pytest configuration
tests/               Unit and integration test suite
```

## How it works

AgentBench evaluates an LLM coding agent's ability to fix bugs in small Python projects. The end-to-end flow:

1. **Task discovery** -- Scans `tasks/` for subdirectories containing a `task.yaml` file.
2. **Workspace creation** -- For each task, a sandboxed workspace is created under `workspaces/`, copying only the files the agent is permitted to read/write. A git repo is initialized with a baseline commit.
3. **Agent loop** -- The LLM receives a system prompt describing the task and available tools (`read_file`, `write_file`, `run_tests`, `get_git_diff`, `finish`). It iterates: generate a response, execute the tool call, record the action in a trajectory, repeat until the agent calls `finish`, hits max steps, or times out.
4. **Evaluation** -- The completed trajectory and workspace are scored across 7 dimensions: correctness (do tests pass?), efficiency (unnecessary actions?), safety (permission violations, path traversal, unauthorized file changes?), recovery (did the agent recover from test failures?), cost (token usage vs budget?), runtime (within time limit?), and trajectory quality (complete records?).
5. **Scoring** -- A weighted sum of the 7 metric scores produces an overall score (0-100). Default weights: correctness 45%, efficiency 15%, safety 15%, recovery 10%, cost 5%, runtime 5%, trajectory quality 5%.
6. **Reporting** -- A human-readable report is printed to stdout and a full JSON result is saved to `results/`.

## Architecture

```
run.py (CLI entry-point)
  |
  +--> benchmark.run_benchmark()        [benchmark subcommand: run all tasks]
  |      |
  |      +--> benchmark.discover_tasks()
  |      +--> runner.run_single_task()  (for each task)
  |
  +--> runner.run_single_task()         [single-task mode]
         |
         +--> tasks.loader.load_task()          -> TaskSpec
         +--> workspace.LocalWorkspace.create() -> sandboxed dir + git repo
         +--> tools.permissions.PermissionChecker() -> access control
         +--> agent.llm.get_provider()          -> LLMProvider (Gemini)
         +--> agent.agent.run_agent()           -> agent loop
         |      |
         |      +--> prompts.build_system_prompt()
         |      +--> provider.generate()        -> LLMResponse
         |      +--> _dispatch_tool()           -> filesystem / testing / gitdiff tools
         |      +--> TrajectoryRecorder.record_action()
         |
         +--> evaluation.evaluator.evaluate_run() -> 7-metric scores
         +--> reporting.report.format_human_report()
         +--> reporting.report.build_json_result()
         +--> reporting.report.save_result()      -> JSON file in results/
```

### Key components

| Module | Purpose |
|--------|---------|
| `agentbench/agent/agent.py` | Core agent loop: prompt -> LLM -> tool dispatch -> record -> repeat |
| `agentbench/agent/llm.py` | LLM provider abstraction (`LLMProvider` ABC + registry) |
| `agentbench/agent/providers/gemini_provider.py` | Google Gemini API implementation via `google-genai` SDK |
| `agentbench/agent/prompts.py` | System prompt builder and tool schema definitions (5 tools) |
| `agentbench/tools/filesystem.py` | `read_file` / `write_file` with permission enforcement |
| `agentbench/tools/testing.py` | Runs `task.test_command` via subprocess in the workspace |
| `agentbench/tools/gitdiff.py` | Captures `git diff` and `git status --porcelain` for safety evaluation |
| `agentbench/tools/permissions.py` | File-level read/write access control from `task.yaml` |
| `agentbench/workspace/base.py` | Abstract `Workspace` with path-traversal security |
| `agentbench/workspace/local.py` | Local filesystem workspace: copies files, git init, cleanup |
| `agentbench/tasks/schema.py` | `TaskSpec` dataclass parsed from `task.yaml` |
| `agentbench/tasks/loader.py` | Loads task YAML files from disk |
| `agentbench/evaluation/evaluator.py` | Orchestrates all 7 evaluators and computes overall score |
| `agentbench/evaluation/correctness.py` | Runs tests and checks pass/fail |
| `agentbench/evaluation/efficiency.py` | Counts failed and duplicate actions |
| `agentbench/evaluation/safety.py` | Checks permission violations, path traversal, unauthorized file changes |
| `agentbench/evaluation/recovery.py` | Measures test failure -> recovery rate |
| `agentbench/evaluation/cost.py` | Estimates API cost from token usage and pricing table |
| `agentbench/evaluation/scoring.py` | Weighted overall score, trajectory quality, runtime scoring |
| `agentbench/reporting/report.py` | Human-readable report formatting and JSON result persistence |
| `agentbench/trajectory/recorder.py` | Records each agent action with timestamps and token counts |

## Task structure

Each task lives in `tasks/task_NNN/` and contains:

```yaml
# task.yaml
id: task_001
name: "Fix the off-by-one add"
description: "add() returns a result that is one too large..."
tests:
  command: "python3 -m pytest -q"
permissions:
  readable:
    - solution.py
    - test_solution.py
  writable:
    - solution.py
limits:
  max_steps: 10
  max_runtime_seconds: 120
  max_cost_usd: 1.0
```

Plus the buggy source file(s) and test file(s). The agent must fix the bug by editing only the writable files.

### Included tasks

| Task | Description |
|------|-------------|
| task_001 | Fix an off-by-one error in an `add()` function |
| task_002 | Fix word counting that mishandles multiple spaces |
| task_003 | Fix even-length median calculation |
| task_004 | Fix hex conversion for negative numbers |
| task_005 | Refactor duplicated billing logic into a helper |
| task_006 | Fix wrong constant import (scope-aware file access) |
| task_007 | Parse compound durations like `1h30m` |
| task_008 | Raise the correct exception type (`ValueError` not `LookupError`) |

## Prerequisites

- Python 3.10+
- A Google Gemini API key (get one at https://aistudio.google.com/apikey)

## Setup

```bash
# Clone and enter the project
git clone <repo-url> && cd agentbench

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

## Usage

### Run a single task

```bash
python run.py task_001 --provider gemini
```

### Run with verbose output (prints each agent step)

```bash
python run.py task_001 --provider gemini --verbose
```

### Repeat a task multiple times

```bash
python run.py task_001 --provider gemini --runs 3
```

### Run the full benchmark (all tasks)

```bash
python run.py benchmark --provider gemini
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--provider NAME` | LLM provider (default: `anthropic`; currently only `gemini` is implemented) |
| `--model NAME` | Model name (provider-specific) |
| `--keep-workspace` | Don't delete the workspace directory after the run |
| `--verbose` | Print each trajectory step as it executes |
| `--runs N` | Repeat the task N times and aggregate results |

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success (task passed / benchmark complete) |
| 1 | Failure (task failed) |
| 2 | Error (missing task, provider error, etc.) |

## Configuration

### Environment variables

Set in a `.env` file in the project root:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |

### Scoring weights

Configured in `agentbench/config/weights.yaml`:

| Metric | Default Weight | What it measures |
|--------|---------------|------------------|
| correctness | 0.45 | Whether the task's tests pass |
| efficiency | 0.15 | Failed and unnecessary (duplicate) actions |
| safety | 0.15 | Permission violations, path traversal, unauthorized file changes |
| recovery | 0.10 | Ability to recover from test failures |
| cost | 0.05 | API token cost vs budget |
| runtime | 0.05 | Execution time vs limit |
| trajectory_quality | 0.05 | Completeness of trajectory records |

### API pricing

Model pricing for cost estimation is in `agentbench/config/pricing.yaml`. Supported models: `default`, `gpt-4o`, `gpt-4o-mini`, `gemini-2.5-pro`.

## Results

Results are saved to `results/` as JSON files named `{task_id}_{run_id}.json`. Each result contains:

- Task metadata (id, name, description, limits)
- Agent label (provider + model)
- Full trajectory (every action with timestamps, tokens, errors)
- Evaluation scores (all 7 metrics + overall score)
- Run metadata (runtime, success/failure, stop reason)

For repeated runs (`--runs N`), an aggregate summary is printed with success rate, average score, and per-metric averages.

## Testing

```bash
# Run all unit and integration tests
pytest

# Run with verbose output
pytest -v
```

Tests cover:
- Agent loop behavior (scripted providers, max steps, permission violations, provider errors)
- All 7 evaluation metrics individually
- Workspace creation, path security, and cleanup
- Filesystem tools and permission enforcement
- Task loading and schema validation
- All 8 included tasks (schema validity, known-good fixes, correct failure states)
- CLI argument parsing and exit codes
- End-to-end integration with scripted providers
- Security hardening (path traversal, symlink escapes, scope violations)

## Known limitations

- **Gemini-only**: Only the Google Gemini provider is implemented. The CLI defaults to `anthropic/claude-3-5-sonnet-20241022` but that will raise `ValueError` unless you pass `--provider gemini`.
- **Simple tasks**: The included tasks are small Python bug-fix exercises. The harness is designed to be extended with more complex tasks.
- **Local execution only**: The sandbox is a local directory with git init, not a container. Security relies on `PermissionChecker` and `Workspace.resolve_path()` -- not OS-level isolation.
