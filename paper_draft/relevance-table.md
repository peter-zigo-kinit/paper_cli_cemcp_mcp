# Relevance Table: Ranked Paper List
> Generated: 2026-05-14
> Source: Phase 2 synthesis of 8 paper summaries

---

## Ranked Table

| Rank | Title | Year | Priority Score | RQ Coverage | Must-Read | Uniqueness | Pairs Well With | Reason |
|------|-------|------|----------------|-------------|-----------|------------|-----------------|--------|
| 1 | From Tool Orchestration to Code Execution: A Study of MCP Design Choices | 2026 | **5.0** | RQ1 ✓✓ RQ2 ✓✓ RQ3 ~ RQ4 ✓ | YES (rel=5, rqw=11) | **HIGH** — only controlled empirical CE-MCP vs. MCP comparison on real servers with full security analysis | 2402.01030 (CodeAct precursor), 2508.14704 (benchmark baselines) | Core paradigm comparison paper; highest overall coverage across all RQs |
| 2 | Executable Code Actions Elicit Better LLM Agents (CodeAct) | 2024 | **4.45** | RQ1 ✓✓ RQ2 ✓✓ RQ4 ✓ | YES (rel=5, rqw=8) | **LOW** — core findings extended by 2602.15945 in MCP context; adds foundational/historical depth | 2602.15945 (MCP extension of same paradigm) | ICML-2024 peer-reviewed foundation; 17-LLM comparison; essential for establishing CE-MCP intellectual lineage |
| 3 | Building Effective AI Coding Agents for the Terminal | 2026 | **4.40** | RQ1 ~ RQ2 ~ RQ3 ✓✓ RQ4 ✓✓ | YES (rel=4, rqw=11) | **HIGH** — only CLI-paradigm paper with engineering ground truth; planner-executor safety architecture not covered elsewhere | 2604.21816 (lazy loading; complements with CLI evidence), 2510.26585 (multi-agent) | Only paper addressing CLI design principles with production data; essential for RQ4 and RQ3 |
| 4 | MCP-Universe: Benchmarking LLMs with Real-World MCP Servers | 2025 | **4.40** | RQ1 ✓✓ RQ2 ✓✓ RQ3 ~ RQ4 ~ | YES (rel=4, rqw=11) | **LOW** — benchmark contribution unique; RQ2/token-scaling findings confirmed by other papers; essential as empirical ground | 2602.15945 (paradigm comparison baselines), 2510.26585 (MAS complexity) | Provides broadest direct-MCP baseline performance across 17 models and 6 domains; ground truth for RQ1/RQ2 |
| 5 | Tool Attention Is All You Need | 2026 | **3.31** | RQ1 ~ RQ4 ✓✓ | YES (rel=4, rqw=5) | **MEDIUM** — unique MCP Tax formalization + stateful gating; overlaps with MCP-Zero on lazy loading goal | 2506.01056 (active discovery), 2603.05344 (CLI lazy loading comparison) | Quantifies MCP Tax precisely; ablation isolates lazy loading as primary contributor; bridges RQ4 → RQ1 token gap |
| 6 | MCP-Zero: Active Tool Discovery for Autonomous LLM Agents | 2025 | **3.31** | RQ1 ~ RQ4 ✓✓ | YES (rel=4, rqw=5) | **MEDIUM** — active request generation mechanism unique; overlaps with Tool Attention on token reduction goal | 2604.21816 (complementary mechanism), 2510.14537 (taxonomy alternative) | Best live-system token reduction numbers (98%); active request paradigm as a novel design principle |
| 7 | Stop Wasting Your Tokens: Efficient Runtime Multi-Agent Systems | 2025 | **2.89** | RQ2 ~ RQ3 ✓✓ | YES (rqw=6) | **MEDIUM** — only peer-reviewed MAS token efficiency paper with LLM-free supervisor; unique cross-framework validation | 2603.05344 (planner-executor complement), 2508.14704 (GAIA benchmark) | Best evidence for RQ3; ICLR 2026 peer-reviewed; 29.68% token reduction in multi-agent setting |
| 8 | JSPLIT: Taxonomy-based Solution for Prompt Bloating in MCP | 2025 | **2.71** | RQ1 ~ RQ4 ✓✓ | NO (rel=3) | **LOW** — addresses same problem as Tool Attention and MCP-Zero; taxonomy approach inferior in accuracy; adds interpretability angle | 2604.21816, 2506.01056 (stronger embedding-based alternatives) | Skip if time-constrained — read Tool Attention (2604.21816) and MCP-Zero (2506.01056) first |

Notes:
- ✓✓ = direct relevance; ~ = indirect relevance
- Must-Read threshold: relevance_score ≥ 4 OR rq_weight_sum ≥ 4

---

## RQ Narrative

### RQ1 — Core Paradigm Comparison

The literature establishes a clear empirical case that code-execution routing (CE-MCP / CodeAct) reduces token usage and turn count compared to direct MCP tool calling in most settings. **CodeAct (2402.01030)** first demonstrated this at ICML 2024 with a +20 percentage-point success improvement over JSON/text actions on multi-tool tasks. **Felendler et al. (2602.15945)** extended this finding to real MCP servers: CE-MCP substantially reduces token usage and execution time across most workloads, though with a critical caveat — highly iterative, context-sensitive tasks (e.g., Wikipedia lookup, Reddit browsing) favor traditional MCP because CE-MCP cannot adjust its pre-written program mid-execution. The consensus is that no paradigm is universally superior: task type determines the winner. **MCP-Universe (2508.14704)** provides the most complete picture of direct MCP baseline performance across 17 models, with GPT-5 achieving only 43.72% success on real-world tasks — suggesting the entire paradigm space has significant room for improvement. A critical gap: no peer-reviewed paper directly compares CLI agents against CE-MCP or direct MCP in a controlled experiment.

### RQ2 — Complexity × Paradigm Interaction

The literature converges on a strong finding: token cost scales non-linearly with task complexity across all paradigms. **Felendler et al. (2602.15945)** show that CE-MCP's efficiency advantage grows with multi-server task complexity (single-server → two-server → three-server tasks), but also that CE-MCP success degrades on the most complex orchestration tasks. **MCP-Universe (2508.14704)** directly measures exponential token growth with interaction steps for direct MCP, and demonstrates that adding even unrelated MCP servers consistently degrades performance — a 11pp drop for Claude in Location Navigation. There is, however, a **contradiction** on context compression: 2508.14704 shows that summarization helps some domains (+10pp for GPT-4.1 in Location Navigation) but hurts others (−12.5pp for Claude in Financial Analysis); while **SMAS (2510.26585)** shows that *adaptive* (trigger-based) observation purification reliably reduces tokens by 29.68% without accuracy loss. The resolution: unconditional compression is harmful, but adaptive compression triggered at critical junctures is beneficial.

### RQ3 — Multi-Agent Architecture × Paradigm

This is the most thinly covered RQ in the corpus. **SMAS (2510.26585)** provides the strongest evidence: a lightweight supervisor meta-agent (LLM-free adaptive filter) reduces multi-agent token cost by 29.68% on GAIA and up to 50.13% on the most token-intensive tasks, while maintaining or improving task success — a Pareto improvement confirmed across 3 MAS frameworks and 3 backbone LLMs. **OPENDEV (2603.05344)** provides engineering evidence that planner-executor separation with filtered tool access per subagent reduces context pollution and improves focus. Neither paper directly tests interface paradigm (CE-MCP vs. CLI vs. direct MCP) within a multi-agent architecture — this is the primary gap for original research. **MCP-Universe (2508.14704)** shows indirectly that agent framework choice matters significantly: the same o3 model gains +5pp by switching from ReAct to OpenAI Agent SDK, suggesting architecture effects can equal or exceed paradigm effects.

### RQ4 — CLI Design Principles as Independent Variable

The literature provides strong convergent evidence that lazy/on-demand schema loading is the single most impactful CLI design principle applicable to MCP. **Tool Attention (2604.21816)** ablates this precisely: removing lazy loading alone costs 10.3pp of task success; it is the largest single component contribution. **MCP-Zero (2506.01056)** demonstrates that active, agent-generated requests (vs. passive query retrieval) further improve tool selection accuracy by 6–7pp on top of token reduction. **JSPLIT (2510.14537)** shows a taxonomy-based alternative that achieves comparable token reduction (2 orders of magnitude) but with lower accuracy (69% at 1,000 servers vs. ~94% for embedding-based methods). **OPENDEV (2603.05344)** provides the only CLI-native validation: startup context reduces from 40% → <5% of budget with lazy loading, and schema-level gating (making unsafe tools invisible) is more robust than runtime permission checks. Together these papers support the conclusion that lazy loading, minimal schema exposure, and active tool request generation are transferable from CLI to MCP — but the cross-paradigm ablation has not been done empirically.

---

## Agreement / Contradiction Summary

| Topic | Agreement/Contradiction | Papers |
|---|---|---|
| CE-MCP reduces tokens vs. direct MCP | **AGREE** | 2602.15945, 2402.01030 |
| Lazy loading reduces schema overhead by 88–98% | **AGREE** | 2604.21816, 2506.01056, 2603.05344 |
| Token cost scales with task complexity | **AGREE** | 2602.15945, 2508.14704, 2510.26585, 2603.05344 |
| Unconditional context compression helps long-horizon tasks | **CONTRADICT** | 2508.14704 (mixed), 2510.26585 (adaptive only) |
| CE-MCP is universally better than direct MCP | **CONTRADICT** | 2602.15945 (not for iterative tasks), 2402.01030 (not for atomic tasks) |
| Static/manual tool pruning degrades performance | **OPEN** (1 paper, sim-based) | 2604.21816 |
| Planner-executor separation improves multi-agent efficiency | **OPEN** | 2603.05344, 2510.26585 (indirect) |

---

## Reading Order Recommendation

**For a researcher who wants to understand the full paradigm landscape:**

1. **2402.01030** (CodeAct, ICML 2024) — Start here: establishes the code-execution paradigm and provides the cleanest comparison with 17 LLMs and 2 benchmarks.
2. **2602.15945** (CE-MCP vs. MCP) — Read second: extends CodeAct to real MCP servers, adds security analysis, and provides the most current empirical comparison.
3. **2508.14704** (MCP-Universe) — Establishes the direct-MCP baseline performance across 17 models; provides RQ2 complexity evidence.
4. **2604.21816** (Tool Attention) — Quantifies the MCP Tax and ablates design principles; essential for RQ4.
5. **2603.05344** (OPENDEV CLI) — Read before writing any CLI experiment; the only CLI-paradigm ground truth in the corpus.
6. **2506.01056** (MCP-Zero) — Best live token reduction numbers; active request mechanism.
7. **2510.26585** (SMAS) — Multi-agent token efficiency; peer-reviewed; essential for RQ3.
8. **2510.14537** (JSPLIT) — ⚑ Skip if time-constrained: read 2604.21816 and 2506.01056 first; JSPLIT adds interpretable taxonomy alternative but is weaker on accuracy.

**Must-read papers (6/8):** 2602.15945, 2402.01030, 2603.05344, 2508.14704, 2604.21816, 2506.01056

**Skip if time-constrained:** 2510.14537 (JSPLIT), 2510.26585 (SMAS — read summary only unless RQ3 is primary focus)
