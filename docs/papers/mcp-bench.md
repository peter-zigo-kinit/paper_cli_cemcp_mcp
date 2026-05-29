# MCP-Bench (Wang et al., arXiv 2508.20453)

*"MCP-Bench: Benchmarking Tool-Using LLM Agents with Complex Real-World Tasks via MCP Servers"* — Wang, Chang, Patel, Biju, Wu, Liu, Ding, Rezazadeh, Shah, Bao, Siow.

This is a paper-level summary. The vendored implementation lives in [[mcp-bench-vendored-harness]]; this doc covers what the paper itself claims, with quotes and table extracts.

> **Reading source.** All quotes were extracted from `ar5iv.labs.arxiv.org/html/2508.20453` via WebFetch. Specific numbers (Table 7 CV, Table 3 sub-scores) carry moderate, not high, confidence — see `docs/mcp-bench-vendored-harness.md` §1 caveats. Re-read from a local PDF before quoting in [[draft_paper]].

---

## 1. One-paragraph summary

MCP-Bench evaluates LLM agents on **complex, multi-step, real-world tasks** that require tool-using behavior across the Model Context Protocol. It connects 28 live MCP servers (~250 tools) covering finance, travel, scientific computing, academic search, etc., synthesizes 104 dependency-chain tasks (56 single-server + 30 two-server + 18 three-server) with an LLM + human-review pipeline, and scores 20 LLMs on a mix of rule-based tool-correctness metrics and a multi-axis LLM judge. **Headline finding: schema-level tool-use has converged across strong models, but planning effectiveness (dependency awareness + parallelism) remains the frontier capability** — even GPT-5 scores only 0.339 on parallelism-and-efficiency while hitting 100% schema compliance.

---

## 2. What the benchmark measures (Section 3)

Three capability levels evaluated together:

1. **Tool-level**: schema understanding (can the model produce parameter dicts that validate against the tool's input schema?) and tool-name validity.
2. **Trajectory-level**: planning (does the model respect cross-tool dependencies and exploit parallelism?).
3. **Task-level**: end-to-end task completion (does the final answer actually fulfill the user's request, grounded in evidence from tool outputs?).

The novelty vs prior MCP benchmarks: tasks are constructed from **dependency chains** — sequences where each tool's output flows into the next tool's input — so the benchmark explicitly tests trajectory-level planning, not just one-shot tool selection.

---

## 3. Task synthesis pipeline (Section 4)

Three stages, all run by **o4-mini** as the task-synthesis LLM, plus a human pass:

### 3.1 Dependency chain discovery
> *"We start the task synthesis by analyzing dependency chains among the provided tools: sequences where each tool's outputs naturally flow into the next tool's inputs. These chains serve as structural scaffolds for task generation."*

Chains can be linear, parallel (independent calls combined later), or hybrid. For multi-server tasks, **cross-server** dependencies are required.

### 3.2 Automatic quality filtering (Appendix A.3)
Two-dimensional 1–10 scoring on each candidate task:
- **Solvability** — can the task be completed with the available tools? Threshold: **≥ 9.0**.
- **Practical utility** — does it address a genuine user need? Threshold: **≥ 5.0**.

> *"Tasks failing the quality threshold (solvability: 9.0/10, utility: 5.0/10) are discarded."*

### 3.3 Task description fuzzing (Section 4.2)
The concrete task description is rewritten as a **conversational user request** — no tool names, no platform names, no step lists, no enumerations. Numeric values, IDs, and named entities are preserved (especially for calculation tasks).

> *"State high-level goals without explicit operational details… preserving all numerical values and concrete parameters."*

The agent only ever sees the fuzzy form. The concrete form, dependency analysis, and tool list are kept for the judge.

### 3.4 Human review
> *"Besides the task synthesis pipeline, the tasks in MCP-Bench also undergo human inspection to ensure their realism, executability, and the reasonability of the dependency chain analysis."*

(Number of human reviewers, agreement rate, and rejection rate are not reported in the body.)

### 3.5 Task counts
| Tier | Count |
|---|---|
| Single-server | 56 |
| Two-server combinations | 30 |
| Three-server combinations | 18 |
| **Total** | **104** |

---

## 4. Evaluation framework (Section 5)

Two parallel scoring pipelines combined per task.

### 4.1 Rule-based metrics (Section 5.1)

Computed deterministically from the execution trace `E` of tool invocations `e`:

| Metric | Formula | What it tests |
|---|---|---|
| **Tool Name Validity Rate** | `R_valid = |{e ∈ E: tool(e) ∈ T_available}| / |E|` | Hallucinated tool names |
| **Schema Compliance Rate** | `C_schema = |{e: valid_tool(e) ∧ valid_schema(e)}| / |{e: valid_tool(e)}|` | Parameter-dict validates against tool's input schema |
| **Execution Success Rate** | `R_success = |{e ∈ E: success(e)}| / |E|` | Calls return successfully |

> *"This metric penalizes hallucinations or invalid tool references."* (on Tool Name Validity)

### 4.2 LLM-as-judge (Section 5.2)

Six sub-dimensions grouped into three axes; each sub-dimension scored 1–10; sub-scores averaged within an axis; the axis score is normalized to [0, 1].

| Axis | Sub-dimension | Quote |
|---|---|---|
| Task Completion Quality | Task Fulfillment | *"how well the task goal is fulfilled"* |
| Task Completion Quality | Information Grounding | *"whether all necessary subtasks are covered and supported by evidence"* |
| Tool Usage Quality | Tool Appropriateness | *"suitability of chosen tools for each subtask"* |
| Tool Usage Quality | Parameter Accuracy | *"correctness and completeness of parameters provided to these tools"* |
| Planning Effectiveness | Dependency Awareness | *"whether inter-tool constraints are respected"* |
| Planning Effectiveness | Parallelism and Efficiency | *"whether the agent minimizes redundancy and exploits opportunities for parallel execution"* |

The judge receives: the fuzzy task (what the agent saw), the concrete task description (judge-only), the dependency analysis (judge-only), the final solution, the total rounds, a compressed execution trace, and the tool catalog.

### 4.3 Judge robustness — prompt shuffling (Section 5.2, Section 6.4, Table 7)

> *"We adopt a prompt shuffling strategy that randomly permutes the order of major evaluation axes (e.g., Task Completion, Tool Selection, Planning Efficiency) as well as the sub-dimensions within each axis."*

Default: **five independent shufflings per task**; the six sub-scores are averaged across runs. The paper validates this against three human annotators on a subset:

| Method | Coefficient of Variation | Human agreement (0/1/2 scale) |
|---|---|---|
| Without shuffling | 16.8% | 1.24 / 2 |
| With shuffling | 15.1% | 1.43 / 2 |

> *"Three human annotators independently reviewed scores in different dimensions produced by each judge pipeline and rated their agreement on a 3-point scale: 0 for disagreement, 1 for partial agreement, and 2 for full agreement."*

This is the paper's only judge-validation evidence. It's thin (n=3 annotators, subset of tasks, no held-out gold set), but enough to defend prompt-shuffling as a robustness improvement; not enough to defend an absolute-score interpretation.

---

## 5. Main results (Section 6.1, Table 3)

**20 models evaluated**, from llama-3-1-8b-instruct up to GPT-5.

Example row (GPT-5, top performer):

| Metric | GPT-5 |
|---|---|
| Valid Tool Name Rate | 100.0% |
| Schema Compliance | 99.3% |
| Execution Success | 99.1% |
| Task Fulfillment | 0.677 |
| Information Grounding | 0.828 |
| Tool Appropriateness | 0.767 |
| Parameter Accuracy | 0.749 |
| Dependency Awareness | 0.649 |
| Parallelism & Efficiency | **0.339** |
| **Overall Score** | **0.749** |

Top three overall: gpt-5 (0.749), o3 (0.715), gpt-oss-120b (0.692).

### Headline interpretation (paper's own framing)

> *"Schema understanding capabilities remain consistently high… However, substantial differences emerge in higher-level reasoning. The sharpest disparities appear in planning effectiveness… smaller models rarely exceed 0.30 on either dimension, underscoring planning as the most significant frontier capability."*

Two things worth noting for our project:
- **The ceiling on rule-based metrics is essentially saturated** for strong models (100% / 99.3% / 99.1% for GPT-5). The signal-to-noise on the surface representation (MCP-JSON-RPC vs CLI help) on these metrics will be small among frontier models; we expect the surface effect to show up in token cost, not in schema compliance.
- **The planning sub-axis (0.339 for GPT-5) is where headroom lives.** This is exactly the axis where CE-MCP's "write the whole plan as one program" pitch should pay off — or fail.

---

## 6. What MCP-Bench does *not* do

- **No execution-based correctness check** beyond schema validation. Whether the final answer is *factually right* is left to the LLM judge.
- **No statistical inference** in reported results — single run per task per model; the only repeats are the 5 judge-prompt shuffles, which is a judge-stability measure, not a per-task-variance measure.
- **No latency / token-cost focus** — token cost appears only in passing; the paper's main axis is task-quality scoring, not efficiency.
- **No comparison across surface representations or orchestration loci.** The benchmark only tests the MCP-client cell — which is exactly the gap our project fills.

---

## 7. Why this paper is the project's primary benchmark

See [[evaluation-strategy]] for the full argument. The short version:

1. **CE-MCP (2602.15945) was evaluated on MCP-Bench**, using this exact LLM-judge framework with 3 GPT-4o judges averaged. Replicating their findings requires the same harness.
2. **The vendored harness IS MCP-Bench** — `cemcpsec-C1F2/Performance Evaluation/mcp-bench/` already implements the MCP-client + CE-MCP cells. See [[mcp-bench-vendored-harness]] for the codebase tour.
3. **MCP-Universe is the planned later layer** for execution-based accuracy — it complements MCP-Bench, not replaces it.

Related: [[ce-mcp]], [[mcp-universe]], [[evaluation-strategy]].
