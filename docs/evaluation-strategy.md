# Evaluation strategy: MCP-Bench vs MCP-Universe and the project plan

What we evaluate on, why, and what gets built. References the paper-level summaries in `docs/papers/` and the vendored harness tour in [[mcp-bench-vendored-harness]].

> This doc is **plan-flavoured**, not committed yet. Items below that crystallise into hard, hard-to-reverse decisions should be promoted into `docs/adr/`. Today's status of each decision is annotated **[settled]** / **[deferred]** / **[open]**.

---

## 1. The two benchmarks side by side

| | **MCP-Bench** ([[mcp-bench]]) | **MCP-Universe** ([[mcp-universe]]) |
|---|---|---|
| **Task origin** | LLM-synthesized (o4-mini) + human review | **Manually authored** by paper authors |
| **# tasks** | 104 (56 single + 30 two-server + 18 three-server) | 231 across 6 domains |
| **# MCP servers** | 28 | 11 |
| **# tools** | ~250 | 133 |
| **Completion scoring** | LLM-as-judge, 6 sub-dims × 1–10 → [0,1] | 84 hand-built per-task evaluators (4 format / 32 static / 48 dynamic) |
| **Rule-based scoring** | Tool Name Validity / Schema Compliance / Execution Success (3 rates) | Folded into per-task evaluators; no separate rule-based layer |
| **Reference traces?** | ❌ | ❌ (only answer-checkers, no expected tool sequences) |
| **LLM-judge stance** | Yes — primary completion metric | **Explicitly rejected** (reason: real-time data + static judge knowledge) |
| **Judge validation evidence** | 5-shuffle averaging; n=3 annotators on subset; CV 16.8% → 15.1%; agreement 1.24 → 1.43 (of 2) | N/A |
| **Distractor mechanism** | 10 distractor servers attached per task at runtime | Separate ablation: +7 servers cuts Claude perf 22%→11% |
| **Per-task repeats / CIs** | Single run; no CIs | Single run rates |
| **Top-model headline** | GPT-5 = 0.749 (axis-normalized) | GPT-5 = **43.72%** (binary success) |
| **CE-MCP replication possible?** | **Yes** (it's what 2602.15945 used) | No |
| **Already vendored in this repo?** | **Yes** (`cemcpsec-C1F2/Performance Evaluation/mcp-bench/`) | No |

**One-line difference:** MCP-Bench scores *how well an agent did, on many fine-grained axes*; MCP-Universe scores *whether the agent succeeded, end-to-end*.

---

## 2. Which benchmark serves which question

Mapping the [[draft_paper]] RQs to evaluation choice:

| RQ | Question | Primary signal we need | Best fit |
|---|---|---|---|
| RQ1 | CLI-wrapper vs MCP-client on tokens/latency/reliability/accuracy | **Token + 6-axis completion + rule-based reliability** all in one harness | MCP-Bench |
| RQ2 | CE-MCP vs MCP-client (replicate Felendler et al.) | Must use **same harness + judge framework** as 2602.15945 | MCP-Bench (mandatory) |
| RQ3 | Capability-tier moderation (frontier / mid / local-GPU) | Fine-grained sub-axes diagnose *where* weaker models break (parameter accuracy vs planning vs grounding) | MCP-Bench (fine-grained); MCP-Universe gives binary cross-check |
| RQ4 | Task-complexity moderation | Need complexity stratification + a complexity metric that survives across cells | MCP-Bench tasks already have dependency-chain depth metadata; MCP-Universe doesn't expose complexity explicitly |

**All four RQs land first on MCP-Bench.** MCP-Universe adds an execution-based-accuracy cross-check; it doesn't substitute.

---

## 3. The decision: MCP-Bench first, MCP-Universe later **[settled]**

> This reverses the ordering currently stated in `paper_draft/draft_paper.md` §5.2 ("MCP-Universe primary, MCP-Bench secondary"). The draft needs to be updated. Logging here so the next agent knows what's settled and what's still in the draft as legacy text.

**Reasoning:**

1. **CE-MCP replication parity is non-negotiable.** Felendler et al. evaluated on MCP-Bench's judge framework. Replicating their findings is the first sanity check on our harness; using a different judge silently changes the comparison. → MCP-Bench first.
2. **The vendored harness IS MCP-Bench.** Two of three cells are already implemented (MCP-client = "Traditional Agent", CE-MCP = "Code Execution Agent"). Switching to MCP-Universe means writing a new harness from scratch *and* building a CLI-wrapper. Doing both in parallel multiplies the failure surface. → start where we have working code.
3. **MCP-Bench's fine-grained signal is more diagnostically useful** while we're tuning cell implementations. If the CLI-wrapper cell is broken, "task fulfillment = 0.42, parameter accuracy = 0.85, dependency awareness = 0.31" tells us where to look; "binary fail" doesn't.
4. **MCP-Universe's defensibility argument (no LLM judge) is real but containable.** The judge-validation evidence in MCP-Bench Table 7 (prompt shuffling, n=3 annotator study) is enough to defend within-study cross-cell comparison. We additionally pin the judge model and report shuffle-averaged scores. If a reviewer pushes back, the planned remediation is to **layer MCP-Universe execution-based scores on top** as a follow-up table — not to re-run everything.

**Reframing for the paper:** MCP-Bench is the *primary* benchmark for the three-cell comparison (RQ1–RQ4). MCP-Universe is the *secondary* layer added later for execution-based-accuracy validation. The "developer decision matrix" headline lives on MCP-Bench; the "yes, it generalizes to a stricter benchmark" follow-up lives on MCP-Universe.

---

## 4. What we use from the vendored harness as-is

From [[mcp-bench-vendored-harness]]:

- **Task corpus.** The 19 combinations shipped in `tasks/*.json` for smoke / iteration. Regenerate to paper-scale (104 combinations) via `synthesis/generate_benchmark_tasks.py --mode all` before headline experiments.
- **Synthesis pipeline.** Don't touch. If we need new tasks, regenerate; don't hand-author.
- **MCP-client cell.** `agent/executor.py` — the "Traditional Agent". Translates 1:1 to our paper's MCP-client cell. No code changes needed for measurement; the harness already breaks out input/output tokens correctly at the executor level (the single "token usage" number is a display-layer collapse, fixable in `results_formatter.py` if needed).
- **CE-MCP cell.** `agent/code_execution_executor.py` + `agent/dynamic_tool_discovery.py`. Translates 1:1 to our CE-MCP cell.
- **LLM-judge.** `benchmark/evaluator.py:LLMJudge` — prompt-shuffling, 6 sub-dims, axis aggregation. Same framework CE-MCP used.
- **Rule-based metrics.** `benchmark/evaluator.py:TaskEvaluator._calculate_tool_accuracy_metrics` — schema validation via `jsonschema`, all three MCP-Bench rates.

---

## 5. What we need to build / change

### 5.1 CLI-wrapper cell **[open]**

A third executor parallel to `executor.py` / `code_execution_executor.py`. Requirements:

- **CLI surface over the same 28 MCP servers.** Two viable wrappers, both community-standard:
    - **Smithery CLI** (`github.com/smithery-ai/cli`) — production registry + `smithery tool call <conn> <tool> [args]` form.
    - **`f/mcptools`** (`github.com/f/mcptools`) — Go CLI, supports stdio/HTTP/streamable HTTP.
- **ReAct loop emitting one CLI subcommand per turn**, stdout returns to context, max-rounds matched to the other cells (`max_execution_rounds: 7`).
- **Tool discovery via `tool list` + `tool describe`** rather than MCP JSON-RPC schema injection, so the surface representation actually differs from MCP-client.
- **Token-usage instrumentation** that breaks out input/output/total just like the other cells.
- **Runner integration** parallel to `_execute_with_code_execution_agent` in `runner.py:1022` — same task input (fuzzy description), same task selection, same evaluator hook.

### 5.2 Distractor-server asymmetry resolution **[deferred]**

Current state (from [[mcp-bench-vendored-harness]] §6):
- MCP-client gets 10 distractor servers attached at runtime.
- CE-MCP gets only required servers (because dynamic discovery scans source files, not live connections).
- This breaks cell parity.

User decision today: **defer until LangChain / Pydantic reimplementation work.** Reasoning: a cleaner reimplementation may dissolve the asymmetry by giving each cell a uniform tool-catalog injection point. Until then, the comparison numbers carry an asterisk.

Options when we revisit:
- **(a)** Add distractors to CE-MCP's discovery scan.
- **(b)** Strip distractors from MCP-client when running cross-cell comparison.
- **(c)** Run both with-distractors and without; treat distractor presence as a fourth design axis.

### 5.3 Per-task repeats + bootstrap CIs **[open]**

The vendored harness writes raw scores to CSV. Need:
- R ≥ 3 repeats per (task × cell × model) at `temperature = 0` with pinned MCP server versions.
- Bootstrap-CI computation (5,000 resamples, BCa) on mean differences per metric.
- Implementation can live downstream of the CSV; no harness change required.

### 5.4 P50 / P95 latency split **[open]**

Currently latency is recorded per task (wall-clock). Need explicit P50/P95 columns in the output schema; trivial post-processing.

### 5.5 Judge model pinning **[settled]**

Per `docs/adr/0002-azure-pin-and-judge-config.md`. Judge model = Azure OpenAI deployment we control; not the same as Felendler et al.'s 3× GPT-4o averaging, but pinned for within-study consistency. The replication of CE-MCP will be **direction-and-magnitude**, not point-estimate parity.

### 5.6 LangChain / Pydantic reimplementation **[deferred]**

User-flagged future work. Goals (as I understand them):
- Replace the vendored harness's bespoke agent loops with LangChain primitives.
- Use Pydantic for tool I/O typing so schema-compliance checks become language-level rather than `jsonschema.validate`-after-the-fact.
- Single-injection-point for tool catalogs → fixes the distractor asymmetry above.
- More portable across model providers (OpenRouter, Azure, local-GPU).

This is a substantial rewrite. The MCP-Bench-first plan above runs on the existing vendored harness so we have real numbers before the rewrite, then re-runs on the LangChain implementation as a parity check.

### 5.7 MCP-Universe layer **[deferred]**

After the MCP-Bench three-cell paper is in shape:
- Build / fork the MCP-Universe harness against its 11-server pool.
- Map our three cells onto it.
- Add a follow-up table to the paper: *"binary success on MCP-Universe, by cell × model × domain"*.
- Cross-validate the within-MCP-Bench cell ranking against the binary signal.

This is a second, smaller paper-and-a-half of work. Sequenced *after* the MCP-Bench story is published or at least camera-ready.

---

## 6. What this changes in the paper draft

Items in `paper_draft/draft_paper.md` that need to be updated when we revise:

| Draft section | Current text | Needs to become |
|---|---|---|
| §1.4 C1, §5.2 | "MCP-Universe primary, MCP-Bench secondary" | MCP-Bench primary; MCP-Universe as follow-up |
| §5.5 Metrics | *"Task accuracy: binary, execution-based (MCP-Universe evaluators); **never LLM-as-judge**."* | LLM-as-judge via MCP-Bench framework as primary; binary execution-based scores from MCP-Universe added as supplementary validation table |
| §5.6 Implementation-parity protocol | "All three cells use community-standard tooling." | Add distractor-asymmetry resolution (point 9 in the list) |
| §6 Threats | "LLM-as-judge fluency bias — avoided entirely; MCP-Universe execution-based evaluators only" | Replace with: judge-bias mitigated by prompt-shuffling per MCP-Bench Table 7; absolute judge scores not comparable cross-study, within-study cell ranking is the actual claim |

I have **not** made these edits to `draft_paper.md` yet. That should be a separate explicit pass.

---

## 7. Open questions to settle before headline experiments

1. **Judge model.** Pinned per ADR-0002 to Azure deployment. Is the specific model GPT-4o-class to match Felendler et al., or do we accept a divergence and report it as a methodology note?
2. **Repeat count R.** R=3 is in [[draft_paper]]; is that defensible for budget, or do we need R=5?
3. **Task-corpus regeneration.** Use the 19 shipped combinations or regenerate to the paper's 104? (Regeneration costs LLM time + human-review time; the shipped corpus is likely a subset known to be representative.)
4. **CLI-wrapper choice.** Smithery CLI or `mcptools`? Smithery has a richer ecosystem; `mcptools` has thinner overhead. The implementation-parity protocol leans toward whichever gives the most CLI-idiomatic surface — likely Smithery.

Related: [[mcp-bench]], [[ce-mcp]], [[mcp-universe]], [[mcp-bench-vendored-harness]], [[draft_paper]], `docs/adr/0001-headline-framing-and-incremental-build.md`, `docs/adr/0002-azure-pin-and-judge-config.md`.
