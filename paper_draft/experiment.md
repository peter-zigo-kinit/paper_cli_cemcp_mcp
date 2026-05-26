# Experiment Plan (Review Version) — Three-Cell Controlled Benchmark Extension

> Companion to `references/review/draft_paper.md`.
> **Scope:** 3 cells — MCP-client / CLI-wrapper / CE-MCP. CE-CLI dropped (rationale: paper §3.4).
> **Frame:** controlled benchmark extension on MCP-Universe + MCP-Bench. NOT a 2×2 decomposition.
> **Evidence base:** 21-paper corpus in `workflows/reference-collecting-project-update/output/`; threat papers ingested 2026-05-20.

---

## 1. Purpose & What We Measure

We extend two established peer-reviewed MCP benchmarks with two additional agent paths over the same MCP servers and tasks, and run the first controlled three-way comparison.

|  | **In-context (ReAct)** | **Code execution (sandboxed)** |
|---|---|---|
| **MCP surface** | `MCP-client` (instrumented Cline; baseline) | `CE-MCP` (per 2602.15945 protocol) |
| **CLI surface** | `CLI-wrapper` (Smithery CLI / mcptools) | — *deferred, see paper §3.4* |

For every cell × task we record **four jointly-reported outcomes**:

1. **Token consumption** — input + output + total tokens (API-reported; cross-checked with `tiktoken` cl100k_base on the transcript). Input/output broken out separately because the surface effect lives mostly in input; the orchestration effect in both.
2. **Latency** — wall-clock per task incl. subprocess / sandbox spin-up; **P50 and P95** (CE-MCP shows fat tails per 2602.15945).
3. **Tool-call reliability** — per-call outcome classified as `ok | schema/parse-error | execution-error | wrong-tool | sandbox-fail | timeout`; reliability = `ok / total`. CE-MCP additionally logs **write-run-debug iteration count**.
4. **Task accuracy** — binary pass/fail, scored by **execution-based evaluators** (MCP-Universe format/static/dynamic checks). **Never LLM-as-judge.**

> **Joint reading is mandatory.** A cell that is cheapest and fastest but fails the task is *worse*, not better. The output is a developer-decision matrix on (token × latency × reliability × accuracy) × (cell × model-tier × complexity), not a single winner.

Maps to paper RQs: **RQ1** (CLI vs MCP), **RQ2** (CE-MCP vs MCP), **RQ3** (model-capability moderation → §4), **RQ4** (task-complexity moderation → §3).

---

## 2. Experiment 1 — Core three-cell comparison (headline)

**Design:** `3 cells × 3 model tiers × N balanced tasks × R repeats`. Single agent. Tasks balanced across complexity tiers so the table averages out complexity (which is the variable in Experiment 2).

- **Cells:** MCP-client, CLI-wrapper, CE-MCP (all three).
- **Model tiers:** see §4.
- **Tasks:** N = 60 balanced across the MCP-Universe domains and step-count distribution.
- **Repeats:** R = 3 with `temperature = 0` and pinned MCP server versions.
- **Run count:** 3 × 3 × 60 × 3 = **1,620 runs** + Tier-0 manipulation check (§7.4).

**Output: four result tables** (rows = cell, columns = model tier; cell = mean ± 95% bootstrap CI):

**Table 1 — Token consumption**

| Cell | Frontier (in/out/total) | Mid (in/out/total) | Local (in/out/total) |
|---|---|---|---|
| MCP-client | | | |
| CLI-wrapper | | | |
| CE-MCP | | | |

**Table 2 — Latency**

| Cell | Frontier P50 / P95 | Mid P50 / P95 | Local P50 / P95 |
|---|---|---|---|
| MCP-client | | | |
| CLI-wrapper | | | |
| CE-MCP | | | |

**Table 3 — Tool-call reliability** (success %, error-class breakdown in footnote)

| Cell | Frontier success% | Mid success% | Local success% |
|---|---|---|---|
| MCP-client | | | |
| CLI-wrapper | | | |
| CE-MCP | | | |

**Table 4 — Task accuracy** (execution-based; the primary outcome that gates Tables 1–3)

| Cell | Frontier success% | Mid success% | Local success% |
|---|---|---|---|
| MCP-client | | | |
| CLI-wrapper | | | |
| CE-MCP | | | |

Tables 1–3 are interpretable only jointly with Table 4: a cell with low tokens but collapsed accuracy is a failure, not a win.

**Hypotheses (paper §4):** total tokens `CE-MCP ≤ CLI-wrapper ≤ MCP-client` on multi-step tasks; latency `MCP-client < CLI-wrapper < CE-MCP` per-call but `CE-MCP < CLI-wrapper < MCP-client` cumulative for high-complexity; reliability comparable on frontier, diverging on local tier; accuracy comparable on frontier, CE-MCP degrades sharply on local tier (the H3 capability-threshold finding).

---

## 3. Experiment 2 — Complexity × cell (separate experiment, RQ4)

Same three cells and three model tiers; tasks **stratified by complexity** instead of balanced.

**Complexity tiers** (by number of tool calls required by the ground-truth solution, derived post-hoc from a dry MCP-client run):

| Tier | Calls to solve | Intent |
|---|---|---|
| **Simple** | 1–2 | manipulation / floor — cells should barely differ |
| **Medium** | 3–6 | realistic operating range |
| **Complex** | 7+ multi-hop | where CE-MCP and CLI batching should separate most |

**Design:** `3 cells × 3 model tiers × 3 complexity tiers × 20 tasks/tier × 3 repeats` = **1,620 runs**.

**Output:** Tables 1–4 from §2, each gaining a complexity panel. Headline plots: `tokens vs complexity` and `accuracy vs complexity`, one line per cell per model tier (the slopes are the RQ4 answer and reveal whether a cell's efficiency advantage decays into accuracy loss as complexity rises).

**Cost-saving option:** Experiment 2's per-tier runs aggregated *can* serve as Experiment 1 if the balanced set is built by sampling proportionally from the three tiers. Recommend building **one** stratified task set and deriving Experiment 1 as the balanced marginal → halves total runs (≈1,620 + pilot instead of ≈3,240). Flagged in §10 decision 2.

---

## 4. Model-capability tiers (the RQ3 axis)

Three tiers chosen to bracket code-generation capability, because the CE-MCP cell has a code-gen dependency the in-context cells do not (CodeAct 2402.01030 — the code-action advantage widens with backbone strength).

| Tier | Role | Primary | Replication (if budget) | Notes |
|---|---|---|---|---|
| **Frontier** | strong code-gen ceiling | Claude Opus 4.x | GPT-5.x | one primary, one replication |
| **Mid** | mid-weight / mid-cost | Claude Haiku 4.5 | GPT-4o-mini · Llama-3.3-70B (open-weight, runnable locally) | open-weight option lets us cut cost |
| **Local-GPU** | consumer hardware | Gemma 3 4B | Qwen2.5-Coder-7B | code-capable comparison; near-zero marginal cost |

The RQ3 deliverable is the **capability threshold**: where does CE-MCP become counterproductive vs MCP-client / CLI-wrapper because the model cannot reliably emit runnable code? CLI-wrapper is expected to be the *robust* choice below the threshold.

---

## 5. Metrics & instrumentation (exact definitions)

- **Tokens:** read from API response usage fields per call; sum input+output across all calls in a task; cross-check total with `tiktoken` cl100k_base on the serialized transcript. Report input/output/total separately.
- **Latency:** wall-clock from task start to terminal state, including sandbox container spin-up and subprocess launch for CE-MCP / CLI-wrapper. Report P50 and P95.
- **Tool-call reliability:** per individual tool invocation, classify outcome → `ok | schema/parse-error | execution-error | wrong-tool | sandbox-fail | timeout`. Tool-call success rate = `ok / total`. Also count write-run-debug iterations for the CE-MCP cell.
- **Task accuracy:** binary, scored by MCP-Universe execution-based evaluators only; never LLM-as-judge.
- **Defense-overhead-adjusted tokens (CE-MCP cell):** report CE-MCP tokens *with* and *without* the mandatory sandbox / semantic-gating overhead from 2602.15945 (otherwise the CE-MCP saving is overstated; corpus gap G6). At minimum log it even if defenses are stubbed in v1.

All runs logged to per-task JSON (tool calls, timestamps, token counts, outcome) → CSV or Weights & Biases; reproducibility = fixed `temperature=0`, pinned MCP server versions, seeded sampling.

---

## 6. Datasets — primary and audit

| Dataset | Source | Why | Built-in complexity signal | Constraint |
|---|---|---|---|---|
| **MCP-Universe** | 2508.14704 (on disk) | 231 tasks, 11 real servers, **execution-based evaluators**; direct-MCP arm already established → reuse as the `MCP-client` cell baseline | avg-steps lets us stratify post-hoc into Simple / Medium / Complex | needs live API keys (Google Maps, GitHub, Yahoo Finance, Blender, Playwright); dynamic evaluators auto-fetch real-time ground truth → not replayable offline; est. **$50–200 per 1k-run batch** |
| **MCP-Bench** | 2508.20453 (on disk; used by CE-MCP 2602.15945) | explicit single / two / three-server task structure = ready-made complexity ladder; lets us replicate the CE-MCP cell against its origin | server-count = complexity proxy (1/2/3) | anonymous repo; CE-MCP reports relative figures only — usable for *replication of the CE-MCP cell*, not for absolute cross-paper numbers |
| APIBank L1 / M3ToolEval | CodeAct 2402.01030 (open) | controlled, small tool counts; clean CodeAct-comparable code-execution cell; fully offline | M3ToolEval = multi-tool multi-turn (Medium/Complex); APIBank L1 = atomic (Simple) | not MCP-native — would need MCP/CLI wrapping; keep as fallback / sanity set |

**Dataset audit (Phase 0 — must complete before anything is built):**

1. Pull MCP-Universe task list; compute the **distribution of required tool calls per task** (from the published `AS` field or re-derived by a dry MCP-client run). Confirm there are ≥20 tasks each in the 1–2, 3–6, 7+ buckets. If the 7+ bucket is thin, MCP-Universe alone is insufficient for Experiment 2.
2. Pull MCP-Bench; map single / two / three-server → Simple / Medium / Complex; count tasks per bucket.
3. Decide primary set: **MCP-Universe primary** (real servers + execution evaluators), **MCP-Bench secondary** (CE-MCP replication + a denser complex tier if MCP-Universe's 7+ bucket is thin).
4. Record per-task: server set, expected tool-call count, evaluator type, API-key requirement, est. cost. Output → `experiment/dataset-audit.md`.

---

## 7. Harness & implementation-parity protocol (the build work)

One agent loop, held constant; an **interface switch** sets the cell (MCP-client / CLI-wrapper / CE-MCP).

### 7.1 MCP-client cell

- **Reuse Ding et al.'s instrumented Cline v3.14.0** (artifacts available on author request, 2511.07426). This ensures our absolute MCP numbers are directly comparable to their published baseline.
- OpenRouter as model gateway so all 9+ models are addressable through one stateless interface.
- Same comprehensive API-interaction logging schema as Ding et al.

### 7.2 CLI-wrapper cell

- **Smithery CLI** ([github.com/smithery-ai/cli](https://github.com/smithery-ai/cli)) as primary CLI surface. Commands: `smithery tool list`, `smithery tool describe <conn> <tool>`, `smithery tool call <conn> <tool> [args]`.
- **`f/mcptools`** ([github.com/f/mcptools](https://github.com/f/mcptools)) as cross-check on a sub-sample to confirm results are not Smithery-specific.
- Agent issues one CLI command per ReAct turn; stdout (truncated/paginated per a *documented, pre-registered* policy) returns to context.

### 7.3 CE-MCP cell

- Four-phase protocol per 2602.15945: post-query lazy tool discovery → code generation → sandbox execution → result return / regenerate.
- Auto-generate Python callable stubs around each MCP tool at task start.
- **Docker sandbox** with resource and time limits; identical Python env across cells.
- Pre-registered code-gen prompts and few-shots (per SkillsBench evidence in Jiang et al. 2602.20867 — curated +16.2pp, self-generated −1.3pp).

### 7.4 Implementation-parity protocol (first-class — the paper's validity rests here)

Under black-box three-way comparison, the result is only as fair as the weakest implemented cell. Therefore:

1. **All three cells use community-standard tooling.** No bespoke adapters.
2. **Same model and hardware** for every run across all three cells.
3. **Same task set** per benchmark; no per-cell task curation.
4. **Same step budget, retry policy, timeout** across all three cells.
5. **Discovery held constant.** All three cells use lazy / on-demand discovery (MCP-Zero-style for MCP and CE-MCP via `<tool_assistant>`-style request; `tool list` + `tool describe` for CLI). Comparing "eager MCP vs lazy CLI" would be a strawman.
6. **Tier-0 manipulation check.** A single 1-call task that *must* show no inter-cell difference. If it does, fix the harness before any production run.
7. **Pre-registered CE-MCP code-gen prompts** committed to the repo before any final run.
8. **Documented prompt translation** between MCP and CLI surfaces — minimal, mechanical, reviewed, no per-task tuning.
9. **Adversarial self-audit:** "we tried to make each losing cell win" documented per cell.

---

## 8. Statistical analysis

- **Per-task pairing.** The same task is run through all three cells → use **paired Wilcoxon signed-rank** on per-task token counts and latency (non-parametric; token distributions heavy-tailed, SMAS 2510.26585). Paper §5.7 D6 retained.
- **Pairwise comparisons** between the three cells: 3 pairs × {tokens, latency, reliability, accuracy} = 12 hypothesis tests. **Bonferroni correction** at α = 0.05/12.
- **Moderation tests:** two-way ANOVA `cell × model-tier` (for RQ3) and `cell × complexity` (for RQ4 in Experiment 2). Report main effects + interaction term.
- **Effect sizes + 95% bootstrap CIs**, not just p-values.
- **Per-domain breakdowns** in supplementary tables (MCP-Universe has 6 domains; reporting per-domain matches MCP-Universe's published table format).

### 8.1 Result presentation (chart recommendation)

Always plot efficiency *against* quality (a trade-off scatter), never on a dual-axis bar over interface categories. Chart catalog:

- **A** — cost–quality Pareto scatter: tokens/task (x) vs task accuracy % (y), one point per cell, "better" = up-and-left, 95% CI error bars.
- **B** — A repeated as small multiples by model tier (Frontier | Mid | Local) — shows the RQ3 capability threshold.
- **C** — A's axes with each cell drawn as a Simple→Medium→Complex trajectory (arrowheads) — the RQ4 complexity story.
- **D** — "tokens per *solved* task" bar (= total tokens ÷ tasks actually solved), grouped by model tier — the one-number summary that can't be gamed by failing cheaply.

**Recommendation:** A as the main result figure; B for the RQ3 section; C for Experiment 2; D as the teaser/abstract figure. Tool-call reliability and latency get their own A-style scatters (vs accuracy) so every efficiency metric is always shown against quality, never alone.

---

## 9. Decisions to confirm (before Phase 1)

1. **Cline source-fork access:** confirm with Ding et al. (zd75@rutgers.edu) that we can reuse their instrumented Cline. Fallback: re-instrument Cline ourselves from upstream v3.14.0 per their Section 3.3 description.
2. **Single stratified set vs two experiments:** recommend building a single complexity-stratified task set and deriving Experiment 1 as the balanced marginal (halves cost ~$2k vs ~$4k). Confirm or keep them fully separate.
3. **Model picks:** confirm Frontier (Opus 4.x primary, GPT-5 replication), Mid (Haiku 4.5 + GPT-4o-mini + Llama-3.3-70B), Local-GPU (Gemma 3 4B + Qwen2.5-Coder-7B).
4. **Primary dataset:** MCP-Universe primary + MCP-Bench secondary — confirm after the §6 audit shows the 7+ complexity bucket is populated.
5. **Budget ceiling:** target ~$2–4k API; local-tier runs ~free on owned GPU. Confirm cap.

---

## 10. Execution plan (ordered)

- [ ] **Phase 0 — Decisions & dataset audit.** Resolve §9. Run the §6 dataset audit → `experiment/dataset-audit.md`. Confirm ≥20 tasks per complexity tier.
- [ ] **Phase 1 — Harness build.** Stand up instrumented Cline (MCP-client cell). Wire Smithery CLI / `mcptools` adapter for CLI-wrapper cell. Build CE-MCP Docker sandbox + four-phase wrapper per 2602.15945. Implement unified instrumentation across cells.
- [ ] **Phase 2 — Pilot & manipulation check.** Tier-0 task across all three cells with one frontier model — must show no inter-cell difference on tokens/latency/accuracy. Then 5 tasks × 3 cells × frontier model end-to-end. Fix biases before scaling.
- [ ] **Phase 3 — Experiment 1 (balanced).** Full run: 3 × 3 × 60 × 3 ≈ 1,620 runs. Produce Tables 1–4.
- [ ] **Phase 4 — Experiment 2 (complexity-stratified).** 3 × 3 × 3 × 20 × 3 ≈ 1,620 runs (or share with Exp 1 if §9 decision 2 is "one set"). Produce per-complexity Tables 1–4 + the tokens-vs-complexity and accuracy-vs-complexity line plots.
- [ ] **Phase 5 — Analysis & write-up.** Paired Wilcoxon + Bonferroni; cell × model-tier and cell × complexity ANOVA; bootstrap CIs; per-domain breakdowns; charts A–D; fold results into paper §5, §6; write the RQ3 capability-threshold finding; deliver the developer-decision matrix.

---

## 11. Risks

| Risk | From corpus | Mitigation |
|---|---|---|
| **Implementation-parity is the single point of failure under black-box comparison** | section-internal | §7.4 protocol; pre-registered prompts/templates; adversarial self-audit; Tier-0 manipulation check is non-negotiable |
| **CE-MCP arm under-implemented vs CLI / MCP** (SkillsBench: self-generated −1.3pp) | SoK 2602.20867 | pre-registered prompts; reproduce CE-MCP 2602.15945 published numbers on MCP-Bench as a sanity check |
| MCP-Universe 7+ complexity bucket too thin | 2508.14704 reports avg steps ~5–8 | use MCP-Bench three-server tasks as the dense complex tier; or compose multi-hop tasks |
| Local model can't emit runnable code → CE-MCP near-0 success | CodeAct 2402.01030 (advantage scales with capability) | this is the **RQ3 finding**, not a failure — still log tokens/latency/errors |
| CLI agents need prompt-tuning to match MCP coverage → unfair | feasibility | use *community-standard wrappers* (Smithery CLI / mcptools), no hand-tuning; Tier-0 guards bias |
| Live-API cost / non-replayability | 2508.14704 dynamic evaluators | cache static-evaluator tasks; reserve dynamic-evaluator tasks for final runs only; cap batch size |
| CE-MCP fat-tail latency dominates | 2602.15945 latency outliers | report P50 and P95; set per-task wall-clock cap |
| **Error-loop token runaway** in MCP-client cell | 2511.07426 Figure 7 | implement loop detector / max-step-with-no-progress abort; copy Ding et al.'s threshold |
| **Scoop risk: 8+ gray-lit benchmarks; new academic MCP benchmarks every quarter** | §1.2 + §2.1 | lead with RQ3 (least scoopable); release artifacts on acceptance |
| **C2 "conceptual novelty" obsoleted by Jiang et al. SoK** | 2602.20867 | reframe to "first controlled *measurement* of these named patterns under identical conditions" — done in paper §1.4 |
