# MCP-Bench: task generation & evaluation (vendored project reference)

How the vendored MCP-Bench harness at `cemcpsec-C1F2/Performance Evaluation/mcp-bench/` produces tasks and scores agent runs. Written for a downstream agent who has *not* read the paper or the code yet.

Paper-side names use the [[CONTEXT.md]] glossary (MCP-client / CLI-wrapper / CE-MCP cells); vendored-project labels are flagged inline so an agent doesn't conflate them.

---

## 1. The paper at a glance

**Reference:** Wang et al., *MCP-Bench: Benchmarking Tool-Using LLM Agents with Complex Real-World Tasks via MCP Servers* (arXiv [2508.20453](https://arxiv.org/abs/2508.20453)).

**What it is.** A benchmark for LLM agents that drives **28 live MCP servers / ~250 tools** across finance, travel, scientific computing, academic search, etc. The paper evaluates agents on three things at once: tool-schema understanding, trajectory-level planning, and end-task completion.

**Why it matters for this project.** MCP-Bench is the **primary benchmark** for the three-cell comparison. Two reasons:

1. **CE-MCP replication parity.** Felendler et al. (2602.15945) evaluated CE-MCP on MCP-Bench using its LLM judge (3 GPT-4o judges, averaged). Replicating their token/turn/latency findings requires the same evaluation harness — anything else makes the cross-study replication non-comparable.
2. **The vendored harness IS MCP-Bench** — it already implements the MCP-client cell (vendored label: *Traditional Agent*, in `agent/executor.py`) and the CE-MCP cell (vendored label: *Code Execution Agent*, in `agent/code_execution_executor.py`). Only the CLI-wrapper cell is missing and must be built.

MCP-Universe (2508.14704) is the *later* layer: stricter accuracy ceiling (GPT-5 = 43.72% binary success vs MCP-Bench's 0.749 normalized axis score), execution-based per-task evaluators (Format / Static / Dynamic — 84 hand-built checkers), and human-curated tasks. Adding MCP-Universe gives the paper a non-LLM-judge accuracy signal but loses CE-MCP replication. The current plan is **MCP-Bench first, MCP-Universe later** — opposite of what `draft_paper.md` §5.2 says. That ordering needs an ADR.

**Judge validation evidence in MCP-Bench (Table 7).** The LLM judge is not unvalidated. The paper reports: 3 human annotators rated judge outputs on a 3-point agreement scale (0/1/2); the 5-pass prompt-shuffle reduces coefficient of variation from 16.8% → 15.1% and raises human agreement from 1.24/2 → 1.43/2. Thin (n=3 annotators, subset of tasks, no held-out human gold set), but enough to defend within-study cross-cell comparison.

**What the paper does NOT contain** that we still need from elsewhere: model-tier sweep, statistical CIs across repeats, CLI-wrapper arm, latency P50/P95 reporting.

---

## 2. Task generation

Pipeline lives in `mcp-bench/synthesis/`. Entry point: `synthesis/generate_benchmark_tasks.py`. Core class: `TaskSynthesizer` in `synthesis/task_synthesis.py:163`.

### 2.1 Three task tiers (by # of servers)

Tasks are partitioned by how many *required* MCP servers a single task needs:

| Tier | File | Combinations | Tasks/combo (default) |
|---|---|---|---|
| Single-server | `tasks/mcpbench_tasks_single_runner_format.json` | 9 (subset shipped) | 2 |
| Multi-server (2) | `tasks/mcpbench_tasks_multi_2server_runner_format.json` | 8 | 2 |
| Multi-server (3) | `tasks/mcpbench_tasks_multi_3server_runner_format.json` | 2 | 2 |

In the original paper: 56 single-server, 30 two-server, 18 three-server combinations (Table 10). The vendored copy ships fewer combinations.

> ⚠️ The `total_tasks` field in the runner-format JSONs is `0` in the vendored bundle — count via `sum(len(c['tasks']) for c in d['server_tasks'])` instead.

### 2.2 The synthesis stages

For each (server or server-combination) the synthesizer loops until it has `num_tasks` accepted tasks (max 5 retries per slot, max `num_tasks * 10` total attempts):

1. **Generate detailed task** (`_generate_single_detailed_task`).
   - LLM is shown formatted tool descriptions (up to 30 tools) for the active server(s).
   - Prompt asks the model to *first* write a `dependency_analysis` (inherent + scenario-based dependencies, decision branches, parallel groups, cross-server links) and *then* design ONE task that maximally exercises those dependencies. Hard requirements: self-contained (no external URLs, files, "user-specified" placeholders), concrete values for all inputs, relative dates.
   - Output: `{ task_id, task_description, dependency_analysis }`.

2. **Generate fuzzy version** (`_generate_fuzzy_version`).
   - Second LLM call rewrites the detailed task as a **conversational user request** — first-person, contractions, no tool names, no step lists, no platform names.
   - Specific numeric values, IDs, named entities, and units MUST survive the rewrite (a `calculation_requirements` block is injected for math/converter/scientific servers).
   - Output sanity-checked for an evidence-requirement phrase; if missing, a fixed evidence sentence is appended.

3. **Quality filter** (`TaskQualityEvaluator.evaluate_task_quality`, `task_synthesis.py:25`).
   - LLM scores the candidate on **Solvability** (1–10, threshold ≥ **9.0**) and **Utility** (1–10, threshold ≥ **5.0**). Below threshold → discard and regenerate. The bar on Solvability is intentionally strict; Utility is permissive.

4. **Distraction servers** (`_select_distraction_servers`).
   - Each task is decorated with **10 distraction servers** randomly drawn from a 22-server pool, excluding any server in the task's `server_name`. At benchmark runtime the runner can connect to required + resident + distraction servers so the agent sees a noisier tool catalog (the paper's tool-selection difficulty).

### 2.3 Task record shape (runner format)

Each task in the runner-format JSON:

```json
{
  "task_id": "unit_converter_000",
  "task_description":  "<concrete task — used by judge as 'concrete reference', NOT shown to agent>",
  "fuzzy_description": "<conversational rewrite — this is what the agent sees>",
  "dependency_analysis": "<reference for the judge only>",
  "distraction_servers": ["Car Price Evaluator", "FruityVice", ...]
}
```

Servers/combination metadata live one level up:

```json
{ "server_name": "Unit Converter",
  "tasks": [ ... ],
  "servers": ["Unit Converter"],
  "combination_name": "Single Server: Unit Converter",
  "combination_type": "single_server" }
```

### 2.4 Why fuzzy descriptions matter for our comparison

The agent never sees the concrete description, the dependency analysis, or the tool list before planning — only the fuzzy text. This is load-bearing for two of our research questions:

- It tests **tool retrieval from fuzzy instructions** (RQ1 in the paper) — the surface representation (MCP-JSON-RPC vs CLI help) directly determines how token-cheap that retrieval is.
- It is what makes distraction servers more than ornament: the model has to *choose* which servers to engage based on conversational text, not server names.

If we drop the fuzzy layer (e.g. for debugging), we silently kill the variance the paper was designed to measure.

---

## 3. Evaluation

Two parallel scoring pipelines combined in `benchmark/evaluator.py:TaskEvaluator.evaluate` (`evaluator.py:978`).

### 3.1 Rule-based metrics (`_calculate_tool_accuracy_metrics`, `evaluator.py:1038`)

Computed deterministically from the recorded execution trace. Per task:

| Metric | Definition | Notes |
|---|---|---|
| `valid_tool_name_rate` | `valid_tool_calls / total_calls` | "valid" = tool name appears in `available_tools` for the task |
| `input_schema_compliance` | `schema_compliant / valid_tool_calls` | `jsonschema.validate(parameters, input_schema)` — `True` if no schema present |
| `execution_success_rate` | `successful / total_calls` | `success` flag on each result record |
| `valid_call_failure_rate` | `valid_call_failures / valid_tool_calls` | infrastructure failures on otherwise-valid calls |
| `planning_json_compliance` | passed in from executor | did the agent emit valid planning JSON each round |
| `server_utilization_metrics` | `{server_count, cross_server_coordination, server_distribution}` | how many distinct servers were touched |

These are the **closest thing in MCP-Bench to execution-based evaluation** — but they only check *interface* correctness, not whether the answer is right. The "is the answer right" judgment is the LLM-judge.

### 3.2 LLM-as-judge (`LLMJudge`, `evaluator.py:57`)

The paper's primary completion metric. **Six sub-dimensions** grouped into three axes, each scored **1–10**:

| Axis | Sub-dimension | What it scores |
|---|---|---|
| Task Completion | Task Fulfillment | fraction of concrete-task requirements perfectly met |
| Task Completion | Grounding | fraction of claims supported by actual tool output |
| Tool Usage | Tool Appropriateness | fraction of tools optimally selected for each subtask |
| Tool Usage | Parameter Accuracy | fraction of tool calls with perfectly accurate, complete parameters |
| Planning Effectiveness & Efficiency | Dependency Awareness | fraction of dependency chains correctly executed |
| Planning Effectiveness & Efficiency | Parallelism & Efficiency | redundancy + parallel-fraction-when-possible |

Rubrics are stored as a `{ "1-3", "4-6", "7-8", "9-10" }` band table in `LLMJudge.evaluation_dimensions` (`evaluator.py:84`).

### 3.3 What the judge sees (and what it doesn't)

Passed to the judge prompt (`_generate_randomized_prompt`, `evaluator.py:129`):

- The **fuzzy task** the agent saw.
- The **concrete task description** — marked "*agent did NOT see this*"; used as the rubric reference.
- The **dependency analysis** — marked "*agent did NOT see this*"; used to score dependency awareness.
- The agent's `final_solution`.
- `total_rounds`.
- A compressed execution summary (auto-compressed to ~10k tokens if a token-limit error fires; `compress_for_judge` at `evaluator.py:461`).
- The full available-tools catalog with descriptions, grouped by server.

### 3.4 Robustness: prompt shuffling

`_generate_randomized_prompt` randomly permutes (a) the order of the three top-level axes, (b) the order of sub-dimensions inside each axis, and (c) the order of the band descriptors inside each rubric — without changing wording. With `enable_judge_stability: true` and `evaluation.judge_stability_runs` repeats (default 2, paper uses 5), the judge is invoked once per shuffle and the six sub-scores are averaged across runs (`_calculate_average_scores`, `evaluator.py:341`). This is meant to take a chunk out of position bias.

### 3.5 Strict-scoring guidelines baked into the prompt

The judge prompt explicitly tells the model:

- Use a **percentage-based defect-rate** mapping (0–10% defects → 9–10; 70–100% → 0–3).
- "Perfectly executed" requires ALL of: optimal tool, ideal parameters, zero redundancy, graceful error recovery, parallel when possible, concise output. ANY missing item → that portion counts as 0% perfect.
- Default to 4–5 unless strong evidence for higher; "*Most real-world executions should score 4–6. Scores of 8+ should be EXCEPTIONAL.*"

This deliberate negative-bias has implications for our hypotheses: absolute MCP-Bench scores are not comparable across studies; they are comparable *within* our three-cell ablation under a fixed judge prompt and judge model.

### 3.6 Aggregate scores

`_calculate_average_scores` derives three axis aggregates from the six sub-scores:

- `task_completion_score = mean(task_fulfillment, grounding)`
- `tool_selection_score = mean(tool_appropriateness, parameter_accuracy)`
- `planning_effectiveness_and_efficiency_score = mean(dependency_awareness, parallelism_and_efficiency)`

No single "MCP-Bench score" is produced; the paper reports the three axes plus the rule-based block separately.

---

## 4. How the runner ties it together

`benchmark/runner.py:BenchmarkRunner` (and `global_runner.py` for both-agent comparisons):

1. Load task file → for each task, resolve required servers + resident servers (`Time MCP` is always-on, `benchmark_config.yaml:81`) + 10 distraction servers (sampled per the task's `distraction_servers` list).
2. Connect to all of those over MCP. For the CE-MCP cell (`_execute_with_code_execution_agent`, `runner.py:1022`) only required servers are connected — no distractions — because tool discovery is via source-file scanning (`agent/dynamic_tool_discovery.py`), not MCP listing.
3. Hand the **fuzzy_description** to the executor (`agent/executor.py:TaskExecutor` for MCP-client, `agent/code_execution_executor.py:CodeExecutionTaskExecutor` for CE-MCP). Both record per-call results + token usage.
4. Pass the execution trace + final answer + concrete task + dependency analysis + tool catalog to `TaskEvaluator.evaluate`.
5. Write CSV + JSON results under `results/`.

Per-task knobs live in `config/benchmark_config.yaml`:
- `execution.max_execution_rounds: 7` — both executors get up to 7 turns.
- `execution.task_timeout: 5000` seconds.
- `benchmark.use_fuzzy_descriptions: true` — flip to false to bypass §2.4; do not do this casually.
- `benchmark.enable_concrete_description_ref_for_eval: true`, `enable_dependency_analysis_ref_for_eval: true` — what the judge sees per §3.3.
- `evaluation.judge_stability_runs: 2`.
- `execution.problematic_tools` — pre-blocklisted tools (Paper Search semantic/IACR, BioMCP AlphaGenome, OSINT overview) that crash or rate-limit.

---

## 5. Translation table (vendored project → paper / [[CONTEXT.md]])

| Vendored project label | Paper / our domain name | Where in code |
|---|---|---|
| Traditional Agent / Traditional MCP Agent | **MCP-client** cell | `agent/executor.py` |
| Code Execution Agent / CE Agent | **CE-MCP** cell | `agent/code_execution_executor.py`, `agent/dynamic_tool_discovery.py` |
| "Token usage" (single number) | **input + output + total**, broken out | per-cell metrics need to be split — vendored sum loses the surface-vs-orchestration distinction |
| `task_description` | *concrete task* (judge-only reference) | runner-format JSON |
| `fuzzy_description` | *fuzzy task* (what the agent sees) | runner-format JSON |
| Single-server / 2-server / 3-server | **server-count tier**, not [[draft_paper]] complexity tiers (1–2 / 3–6 / 7+) | task file split |

**The complexity tiers in `draft_paper.md` are not the same as the server-count tiers above.** Our complexity tiers are derived from observed step count in a dry MCP-client run, not from how many servers a task spans. A single-server task with deep dependency chains can be Complex; a 3-server task with three independent lookups can be Medium. Don't conflate the two when stratifying.

---

## 6. Gaps a downstream agent should be aware of

- **No execution-based evaluators in MCP-Bench.** All completion-quality judgments are LLM-judge — this is what we use, and what CE-MCP used, so cross-study replication works. The defensibility argument lives in §1's mention of Table 7 (prompt-shuffling + 3-annotator agreement study). If a reviewer pushes back, the planned mitigation is to layer MCP-Universe execution-based scores on top as a follow-up; **not** to abandon the LLM judge.
- **CLI-wrapper cell is unbuilt.** Adding it means: a CLI surface over the same 28 MCP servers (Smithery CLI or `mcptools`); a third executor parallel to `executor.py` / `code_execution_executor.py`; runner branching identical to the existing `_execute_with_code_execution_agent` path.
- **Distraction-server asymmetry across cells.** `runner.py:644` short-circuits distractor attachment for the CE-MCP cell ("only connect to the required server(s) — no distraction servers") because CE-MCP discovers tools by **source-file scanning** (`agent/dynamic_tool_discovery.py`), not by listing connected servers. This means the MCP-client and CE-MCP cells run against *different tool catalogs* — a confound for any tool-selection metric. The implementation-parity protocol in [[draft_paper]] §5.6 needs an explicit decision here; the simplest fix is to also restrict the MCP-client cell to required servers when running comparison experiments, accepting that we then diverge from the paper's distractor setup.
- **Vendored task corpus is smaller than the paper's.** 9 + 8 + 2 = 19 combinations shipped vs paper's 56 + 30 + 18 = 104. If we need parity with the paper's numbers, regenerate via `synthesis/generate_benchmark_tasks.py --mode all`.
- **`Paper Search` server is blocklisted at the tool level** (`problematic_tools` in config) — don't expect academic-search tasks to actually exercise that server end-to-end without unblocking specific tools.
- **No statistical inference** in the harness — results CSV has raw scores; CIs / bootstrap need to be added downstream. The paper itself ships no per-task repeats, so even simple within-task variance is unmeasured.
- **Judge model lock-in.** The vendored harness uses whichever model is configured for the judge (Azure OpenAI per `docs/adr/0002-azure-pin-and-judge-config.md`). CE-MCP used GPT-4o × 3 averaged. To replicate exactly we need the judge model pinned to GPT-4o-class; to compare *only* our cells, judge consistency within a study is what matters, not match with the CE-MCP paper.

---

## 7. Quick file map

```
mcp-bench/
├── synthesis/
│   ├── task_synthesis.py            # TaskSynthesizer + TaskQualityEvaluator (§2.2)
│   ├── benchmark_generator.py       # orchestrates per-server / per-combination synthesis
│   └── generate_benchmark_tasks.py  # CLI entrypoint for §2
├── tasks/                           # shipped runner-format JSONs (§2.3)
├── agent/
│   ├── executor.py                  # MCP-client cell (vendored label: "Traditional Agent")
│   ├── code_execution_executor.py   # CE-MCP cell (vendored label: "Code Execution Agent")
│   └── dynamic_tool_discovery.py    # source-file scanning for CE-MCP discovery
├── benchmark/
│   ├── evaluator.py                 # TaskEvaluator + LLMJudge (§3)
│   └── runner.py                    # BenchmarkRunner (§4)
├── global_runner.py                 # runs both agents per task and compares
├── config/benchmark_config.yaml     # all knobs (§4)
└── mcp_servers/                     # 28 server implementations (see commands.json)
```

See also: [[CONTEXT.md]] for paper-side glossary, [[draft_paper]] for what we're using MCP-Bench *for*, `docs/adr/0001-headline-framing-and-incremental-build.md` for the three-cell framing decision, `docs/development.md` for the per-project venv setup needed to run any of this.
