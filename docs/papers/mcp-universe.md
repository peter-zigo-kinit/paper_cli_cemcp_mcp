# MCP-Universe (arXiv 2508.14704)

*"MCP-Universe"* — large, **manually-curated** MCP benchmark with execution-based per-task evaluators. The planned later layer for our project's accuracy story.

> **Reading source.** Quotes from `ar5iv.labs.arxiv.org/html/2508.14704` via WebFetch.

---

## 1. One-paragraph summary

MCP-Universe builds **231 hand-designed MCP tasks across 6 domains** (Location Navigation, Web Searching, Browser Automation, 3D Design, Financial Analysis, Repository Management) backed by **11 real MCP servers and 133 tools**, and scores them with **84 per-task hand-built evaluators** in three styles: format, static (manually collected gold answers), and dynamic (live API queries at evaluation time). It **explicitly rejects LLM-as-judge** on the grounds that judge knowledge is static while the benchmark uses real-time data. **Headline finding: even GPT-5 reaches only 43.72% overall success rate** — the ceiling is much lower than MCP-Bench's normalized scores, and the benchmark has measurable headroom for years.

---

## 2. Task design philosophy (Section 3)

### 2.1 Manual curation — not LLM-synthesized
> *"Since MCP is a new concept and there is a lack of high-quality usage examples, we manually designed challenging MCP tasks to reflect real use cases."*

This is the sharpest contrast with MCP-Bench. Where MCP-Bench produces 104 tasks by LLM (o4-mini) and filters them for solvability, MCP-Universe produces 231 tasks by human authors.

### 2.2 Difficulty floor
> *"If a task can be easily completed by LLMs without using MCP servers, or can be consistently solved with MCP servers within five retries, we consider it a simple task and brainstorm a new one."*

The difficulty floor is explicit: anything an LLM can do without tool calling, or solve reliably in ≤5 retries, gets rewritten. The result is a benchmark calibrated to *current* model capability — by construction it's near the frontier.

### 2.3 Scale
| Statistic | Value |
|---|---|
| Total tasks | 231 |
| Domains | 6 |
| MCP servers | 11 |
| Tools across servers | 133 |
| Total evaluators | 84 |

**Domain distribution** (% of tasks):
- Web Searching 23.8%
- Location Navigation 19.5%
- Financial Analysis 17.3%
- Browser Automation 16.9%
- Repository Management 14.3%
- 3D Designing 8.2%

---

## 3. Evaluators — the core methodological contribution (Section 3)

Three types, each built **per-task**, **cross-checked between authors**:

> *"After the evaluator creation, each evaluator[ ] will be cross-checked by the other authors for feasibility, ambiguity, and correctness."*

### 3.1 Format evaluators — 4 (4.8%)
> *"The first type evaluates whether agents strictly follow format requirements."*

Cheap regex / structural checks. Smallest category.

### 3.2 Static evaluators — 32 (38.1%)
> *"The second type assesses correctness for tasks whose answers do not change over time, such as the number of cities in route planning tasks… we manually collect the correct answers and write evaluators to check whether the model's outputs meet the requirements."*

Author-collected ground-truth answers; the evaluator checks the agent's output against them. The work-intensive layer.

### 3.3 Dynamic evaluators — 48 (57.1%)
> *"For the third type, the correct answer of the task needs to be updated with real-time data… we design automatic evaluators to obtain real-time correct answers and verify task completion, which can provide stable evaluation results across different timestamps."*

Examples: *"the price of a flight on a future date for the travel booking tasks, the weather of a place in the place-finding tasks, and the number of GitHub issues in the issue tracking tasks."* The evaluator queries the same underlying APIs at evaluation time and compares.

### 3.4 Why this matters: live-state robustness *without* rewriting tasks
> *"This… can provide stable evaluation results across different timestamps."*

Tasks themselves aren't rewritten as the world changes; the evaluators query live APIs. This is the only way MCP-Universe can stay valid against MCP servers like GitHub, Google Maps, Yahoo Finance, Playwright over months/years.

---

## 4. LLM-as-judge: explicitly rejected (Section 3)

> *"For simplicity, many recent works choose to follow the LLM-as-a-judge paradigm. However, we argue that this paradigm is not well-suited for our MCP-Universe scenario, since some tasks are designed to use real-time data, while the knowledge of the LLM judge is static."*

The argument is narrower and more technical than "LLM judges are unreliable in general." Walking through it:

### 4.1 The mechanism

An LLM judge has a **frozen knowledge cutoff**. Its weights were trained on data up to some date, and from that point forward its world-model of factual reality stops updating.

Many MCP-Universe tasks are deliberately tied to **real-time facts** — facts that change *after* the judge's training cutoff. The paper's own examples: *"the price of a flight on a future date for the travel booking tasks, the weather of a place in the place-finding tasks, and the number of GitHub issues in the issue tracking tasks."*

When the agent answers *"the flight is $342"*, an LLM judge being asked *"is this answer correct?"* has three options, none of which work:

1. **Guess from training data** → almost certainly wrong, because flight prices have moved.
2. **Trust the agent's answer** → the judge is no longer judging, just echoing.
3. **Decline to score** → useless.

So the judge has **no anchor of truth** to compare against. It can score *plausibility* (*"does $342 seem like a flight price?"*) but not *correctness*.

### 4.2 MCP-Universe's fix — dynamic evaluators

A separate per-task evaluator that **hits the same live API at evaluation time** and compares the agent's answer to whatever the API returns *now*. The agent and evaluator both read from the same authoritative live source — the evaluator never has to "know" the answer, it fetches it. This is what the 48 dynamic evaluators (57% of total, §3.3) do.

The paper calls this *"stable evaluation results across different timestamps"* — the task stays valid as the world changes, because the evaluator moves with the world.

### 4.3 Why this argument doesn't kill LLM-as-judge in general

The rejection is **specific to time-sensitive factual correctness**. It does NOT apply when:

- The judgment is about **process quality**, not factual correctness — *"did the agent pick the right tool?"*, *"are parameters well-typed?"*, *"is the trajectory efficient?"*
- The judgment is about **reasoning quality grounded in the visible trace** — *"is the agent's final claim supported by the tool outputs it just saw?"* The judge compares claim-to-trace, not claim-to-world.
- The task itself doesn't depend on volatile data (math, unit conversion, deterministic computation).

### 4.4 Why MCP-Bench's LLM-judge choice survives this objection

Every MCP-Bench rubric is grounded in artifacts the judge can see, not in external real-world facts:

| MCP-Bench sub-dim | Needs real-time ground truth? |
|---|---|
| Task Fulfillment | No — compares solution to the *concrete task description shown to the judge* |
| Information Grounding | No — compares claims to the *execution trace shown to the judge* |
| Tool Appropriateness | No — inspects tool choice against the available-tools list |
| Parameter Accuracy | No — inspects parameter dicts against schemas |
| Dependency Awareness | No — compares trajectory to the *dependency analysis shown to the judge* |
| Parallelism & Efficiency | No — counts redundancy and parallel groups |

If the agent says *"AAPL closed at $187 yesterday"*, MCP-Bench's judge does **not** ask *"is $187 correct?"* — it asks *"did the agent invoke the AAPL price tool, did that tool return $187, and is the agent's claim grounded in the tool output?"* Whether $187 was actually right is the MCP server's problem, not the judge's. That's why the MCP-Universe objection doesn't impeach MCP-Bench: they score different things.

### 4.5 What's not shipped with MCP-Universe

- **No reference traces** / expected tool-call sequences. The evaluator only knows the right answer (static) or how to fetch it (dynamic). It cannot tell whether the agent took an efficient path, only whether the final answer is right.
- **No completion-quality sub-scoring.** Tasks are essentially binary pass/fail at the evaluator level.

### 4.6 Implication for our project

This is why [[evaluation-strategy]] treats MCP-Universe's objection as **containable**:

- We're scoring **architectures**, not factual correctness of agent answers. Tool selection, parameter accuracy, dependency handling, token cost, latency — none of these need real-time truth.
- The MCP-Bench judge framework was designed for exactly the kind of judgment we need.
- Where we *would* want a stricter real-time-grounded signal (e.g., *"does CE-MCP retrieve correct data, or does it hallucinate plausibly?"*), MCP-Universe enters as the supplementary layer — not because the LLM judge is broken in general, but because the *factual-correctness* slice of our story needs a non-LLM signal.

---

## 5. Main results (Section 4, Tables 3–4)

### 5.1 Overall leaderboard
| Rank | Model | Overall success rate |
|---|---|---|
| 1 | **GPT-5** | **43.72%** |
| 2 | Grok-4 | 33.33% |
| 3 | Claude-4.0-Sonnet | 29.44% |

The ceiling is sharp: top model fails the majority of tasks. Compare to MCP-Bench where GPT-5 scores 0.749 on a normalized [0,1] axis — different scoring system, but the ceiling spread alone suggests MCP-Universe is the harder bar.

### 5.2 GPT-5 by domain
| Domain | Success rate |
|---|---|
| Financial Analysis | 67.50% |
| 3D Designing | 52.63% |
| Web Searching | 45.45% |
| Browser Automation | 35.90% |
| Location Navigation | 33.33% |
| Repository Management | 30.30% |

Repository Management (which would include GitHub-style MCP server calls) is the hardest domain even for the top model.

### 5.3 GPT-5 by evaluator type (Table 4)
| Evaluator type | GPT-5 success rate |
|---|---|
| Format | 88.89% |
| Static | 61.92% |
| Dynamic | 65.96% |

Format checks are easy (as expected). Static and Dynamic are close — the difficulty doesn't come from real-time-vs-static, it comes from the task itself.

---

## 6. Distractor / unrelated-tool experiment (Section 4)

The paper runs a separate ablation adding **7 unrelated MCP servers (94 additional tools)** to the available pool. Result:

> *"performance degrades when 7 unrelated MCP servers (94 tools total) are added, reducing Claude-4.0-Sonnet's Location Navigation score from 22.22% to 11.11%."*

Roughly **50% relative degradation** from tool-catalog noise. Directly relevant to our distractor-asymmetry decision in [[evaluation-strategy]] — even on a benchmark designed to be hard, adding distractors halves performance, so the choice of how to attach distractors across cells is a first-order methodological decision.

---

## 7. Self-identified limitations (Section 5)

The paper flags three:

> *"the number of tokens increases rapidly as the number of interaction steps grows. This demonstrates that long context is one of the key challenges presented by our benchmark."*

> *"LLMs often struggle to correctly use tools provided by the MCP servers, indicating a lack of familiarity with their interfaces and constraints."*

> *"Notably, enterprise-level agents like Cursor cannot achieve better performance than standard ReAct frameworks."*

The first is the most relevant to our project: MCP-Universe surfaces the long-context problem that motivates CE-MCP and CLI-wrapper as design alternatives. The benchmark itself doesn't include token-efficiency variants, leaving that exactly where our paper sits.

---

## 8. Why this paper is our project's *later* benchmark, not the first

See [[evaluation-strategy]] for the full reasoning. Short version:

1. **No CE-MCP replication path.** Felendler et al. used MCP-Bench's judge; we cannot reproduce their numbers on MCP-Universe.
2. **No vendored harness.** MCP-Universe ships a separate codebase (not in this repo today). Adding it means building a second harness, server-config translation, and a CLI-wrapper adapter against a *different* 11-server pool than MCP-Bench's 28-server pool.
3. **Different completion signal.** MCP-Universe gives binary pass/fail per task; MCP-Bench gives 6-axis fine-grained scoring. For diagnosing **where** a cell fails (parameter accuracy vs planning vs grounding) the MCP-Bench signal is more informative. MCP-Universe is the right tool for "**does** the cell succeed end-to-end."

The plan is **add MCP-Universe later** as an execution-based-accuracy supplement, not as a replacement.

Related: [[mcp-bench]], [[ce-mcp]], [[evaluation-strategy]], [[mcp-bench-vendored-harness]].
