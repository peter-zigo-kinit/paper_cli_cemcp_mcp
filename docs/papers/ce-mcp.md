# CE-MCP (Felendler et al., arXiv 2602.15945)

*Code Execution with MCP — "cemcpsec"* by Felendler et al.

The paper our project directly extends. Defines the CE-MCP architecture (one of our three cells) and provides the empirical baseline our replication must reproduce.

> **Reading source.** Quotes extracted from `ar5iv.labs.arxiv.org/html/2602.15945`. The paper's vendored artifact is the `cemcpsec-C1F2/` tree in this repo (anonymized `anonymous.4open.science/r/cemcpsec-C1F2/` link in the paper).

---

## 1. One-paragraph summary

CE-MCP is a **code-execution-based alternative to the standard in-context ReAct MCP agent**. Instead of injecting tool schemas into model context and emitting one JSON-RPC call per turn, the model writes a single Python program that imports generated wrappers for the relevant MCP tools, runs the program in a sandbox, and only the *final result* returns to context. The paper evaluates CE-MCP vs a "traditional MCP" (MCP-client) baseline on a 16-task subset of MCP-Bench with three GPT models, using MCP-Bench's own LLM-judge framework. **Headline finding: substantial token / turn / latency reductions, increasing with task complexity, but with comparable or slightly degraded task fulfillment on three-server and text-synthesis tasks.**

---

## 2. The four-phase CE-MCP protocol (Section 3)

### Phase 1 — Post-query tool discovery
> *"Once the query arrives, the agent determines which MCP servers are actually relevant (such as file-system, database, or analytics servers) by exploring the servers' filesystem and loading only the tool definitions required to complete the task."*

Discovery is **lazy** (post-query, not at startup) and **filesystem-based** (scans server source files rather than going through MCP's `list_tools`). This is the key efficiency move — schema injection only happens for the tools that survive task-relevance filtering. Implemented as `agent/dynamic_tool_discovery.py` in the vendored harness.

### Phase 2 — Code generation and planning
> *"The LLM generates a single, self-contained program that encompasses the complete execution plan, including tool invocations, control flow, and final result."*

One program covering all rounds. Control flow, retries, data shaping all live in the program — not in the agent's reasoning loop.

### Phase 3 — Code execution
> *"The generated program is executed within a dedicated execution environment that is isolated from the model's context. MCP tools are exposed as directly callable functions within this environment, and all intermediate computations are performed locally during execution."*

Sandbox runtime. The model **never sees intermediate tool outputs in its context** unless the program explicitly returns them. This is what produces the token-saving — tool payloads stay inside the sandbox.

### Phase 4 — Result return and validation
> *"The execution environment returns the final result to the agent. The underlying LLM then verifies whether the output satisfies the original query. If execution fails or the result is unsatisfactory, the model incorporates the error details, generates a revised program, and re-executes it."*

The recovery loop. Implemented as `max_turns = 7` in `code_execution_executor.py`. Each retry costs a new code-generation round plus a sandbox run.

---

## 3. Evaluation setup (Section 4)

### 3.1 Benchmark + task subset
> *"All experiments are conducted using MCP-Bench, a benchmark for the evaluation of tool-using LLM agents that interact with real MCP servers."*

- **10 of MCP-Bench's 28 servers** ("we therefore restrict our evaluation to 10 representative MCP servers")
- **16 tasks total**: 2 single-server + 10 two-server + 4 three-server

### 3.2 Models
**Three GPT models**: GPT-4o, GPT-4.1, GPT-4.1-mini. With two agent architectures → **6 (agent × model) configurations**.

### 3.3 Judge
> *"Task fulfillment, planning effectiveness, tool selection correctness, and parameter accuracy are evaluated using the MCP-Bench judging framework. These metrics were evaluated by three independent GPT-4o-based LLM judges. The final scores are computed as the average across the judges."*

So: **LLM-as-judge via MCP-Bench's prompt + 3 GPT-4o judges averaged**. No execution-based correctness check.

### 3.4 Efficiency metrics
Quoted definitions:

> *"**Number of Turns:** For MCP, each tool invocation and subsequent reasoning step constitutes a turn. For the CE-MCP agent, a turn consists of a single sandboxed code execution encompassing all required tools, followed by reasoning over the result returned."*

> *"**Token Usage:** This captures input, output, and total tokens consumed across all model invocations."*

> *"**Execution Time:** This measures end-to-end time from task input to final output, including model inference, tool execution, and sandbox runtime."*

Note: **input + output + total broken out separately** — matches our project's requirement; the [[CONTEXT.md]] warning about the vendored project's single "token usage" number applies to the *display layer*, not to the underlying measurement.

### 3.5 What's missing methodologically
- **No per-task repeats reported.** Variance across runs is not quantified.
- **No statistical significance testing.** Results presented as distributions in figures.
- **Three-judge averaging is the only inter-rater control.** No human gold standard, no held-out validation.

---

## 4. Main results

### 4.1 Token reduction
> *"The token savings achieved with the CE-MCP are substantial and increase with task complexity, particularly for two- and three-server tasks."*

Exact percentages live in Figure 4 (visual, not numeric in text). Direction: CE-MCP < MCP on tokens, gap widens with server count.

### 4.2 Turns reduction
> *"The MCP often requires dozens of turns due to its reasoning–tool–reasoning loop, whereas the CE-MCP aggregates most tasks into a single execution turn, reflecting a substantial reduction in execution fragmentation."*

### 4.3 Latency
> *"The traditional MCP exhibits higher average latency due to long sequences of tool invocations and repeated retries. In contrast, the CE-MCP concentrates execution into one or two sandboxed program runs, resulting in a lower average latency."*

Note: only **average** latency, not P50/P95. Our project should add P95 because CE-MCP's recovery-loop structure should produce fatter tails.

### 4.4 Task fulfillment
> *"The median task fulfillment scores are similar for single- and two-server tasks with just a small difference. In some single-server settings, the CE-MCP slightly outperforms the MCP, likely due to reduced error accumulation from fewer intermediate reasoning steps."*

So: **on the headline accuracy metric, CE-MCP is comparable** (with small wins on single-server). The token/turn/latency savings are not paid for with accuracy losses on average.

### 4.5 Where CE-MCP loses
Two specific failure modes the paper itself flags:

**Three-server orchestration:**
> *"However, for a subset of three-server tasks, the CE-MCP obtains a lower task fulfillment score. Examination of these cases shows that failures typically arise from incorrect global orchestration decisions made during code synthesis (e.g., missing a conditional branch), which the MCP may recover through incremental reasoning and retries."*

**Iterative / textual synthesis tasks:**
> *"In contrast, MCP is favored for tasks with iterative or semantically adaptive structures (e.g., retry loops, open-ended relevance filtering, or subjective aggregation). The MCP's stepwise reasoning allows it to adapt execution based on intermediate observations, whereas the CE-MCP must encode loop bounds and conditional logic up front."*

> *"Tasks dominated by open-ended textual synthesis (e.g., Wikipedia, Reddit) occasionally benefit from the multi-turn interaction pattern of the traditional MCP. These tasks require iterative reasoning, progressive summarization, and contextual refinement, where additional turns can improve grounding and coherence."*

Direct prediction for our work: when we stratify by task type, the CLI-wrapper cell's behavior on iterative-textual-synthesis tasks is an interesting third data point — does the CLI surface inherit the recovery advantage of in-context ReAct, or lose it to subprocess overhead?

### 4.6 Failure mode consistency across models
> *"The observed success rates were consistent across the models, indicating that the failures arise primarily from architectural semantics rather than model-specific behavior."*

Argues the architectural axis is real and not just a model-quality artifact — but tested only on GPT-class models; the [[draft_paper]] §RQ3 capability-threshold claim is not addressable from this paper alone.

---

## 5. What our project must replicate vs extend

| | CE-MCP paper | Our project's MCP-Bench arm |
|---|---|---|
| Benchmark | MCP-Bench (16-task subset) | MCP-Bench (full corpus or comparable subset; see [[mcp-bench-vendored-harness]]) |
| Cells | 2 (MCP, CE-MCP) | **3** (MCP-client, CLI-wrapper, CE-MCP) — CLI-wrapper is the new arm |
| Models | 3 GPT models | 3 capability tiers (frontier / mid / local-GPU) — [[draft_paper]] §5.3 |
| Judge | MCP-Bench framework, 3× GPT-4o averaged | Same framework, judge model pinned (see `docs/adr/0002-azure-pin-and-judge-config.md`) |
| Repeats | Not specified (likely 1) | R ≥ 3, with CIs |
| Latency | Average | **P50 + P95** |
| Statistics | None | Bootstrap CIs on mean differences |

The point of replicating, even before extending, is to **confirm the harness reproduces direction and rough magnitude** of CE-MCP's token/turn/latency findings before we trust new CLI-wrapper numbers from the same harness. This is the Tier-0 manipulation check in [[draft_paper]] §5.6, applied at study level rather than per-task.

---

## 6. Open questions about CE-MCP this paper leaves on the table

- **Effect of model strength.** Only GPT-class tested. CodeAct (2402.01030) predicts the code-action advantage widens with backbone strength and inverts on weak models — directly relevant to our RQ3.
- **CLI-wrapper comparison.** Not in scope. The paper compares JSON-RPC-in-context vs sandboxed-code; it never compares JSON-RPC-in-context vs CLI-in-context, which is the surface-axis question our project addresses.
- **Distractor robustness.** CE-MCP was evaluated without the distractor servers MCP-Bench attaches by default for the in-context cell (see [[mcp-bench-vendored-harness]] §6). Both cells in their paper were therefore at the same "no distractor" operating point, but the vendored harness as-shipped runs the MCP-client cell *with* distractors. This is the asymmetry our project must resolve before publishing — see [[evaluation-strategy]].
- **Per-task variance.** Single-run-per-task numbers; no within-task variance reported.
- **Sandbox security cost.** The paper introduces 16 attack classes specific to CE-MCP (Section 5+) but doesn't quantify the latency cost of running in a hardened sandbox. Our P95 latency measurement should be done in the sandbox config we'd actually ship, not a permissive one.

Related: [[mcp-bench]], [[mcp-universe]], [[evaluation-strategy]], [[mcp-bench-vendored-harness]].
