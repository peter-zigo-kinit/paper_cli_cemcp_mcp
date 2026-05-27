# Azure OpenAI pin for Phase 1; configurable judge deployment

## Context

ADR-0001 commits to an incremental staircase from the vendored CE-MCP authors' implementation. The Phase 1 PRD (issue #1, original revision) further pinned the calibration to OpenAI-direct (`OPENAI_API_KEY`) and `gpt-4.1-mini`:

> "The vendored README claims OpenRouter support but `requirements.txt` does not include it. This PRD uses OpenAI directly (via `OPENAI_API_KEY`) to side-step that discrepancy; OpenRouter support is a Phase 2b concern."

Pre-work for Phase 1 surfaced that the available LLM credentials in this environment are Azure OpenAI, not OpenAI-direct: `.env` at the repo root carries `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`. The user has `gpt-4.1-mini` deployed in their Azure resource. Going OpenAI-direct would require obtaining and managing a separate OpenAI account; going Azure preserves the PRD's model choice (`gpt-4.1-mini`) with credentials already in hand.

The vendored project is partially Azure-aware: `LLMFactory.get_model_configs()` already emits Azure `ModelConfig` entries for `gpt-4o`, `gpt-4o-mini`, `o4-mini`, `o3`, `gpt-5`, `gpt-5.2`, and `LLMFactory.create_llm_provider` already handles `provider_type="azure"`. Three gaps prevent Phase 1 from running on Azure unmodified:

1. The factory's Azure block does not register `gpt-4.1-mini`.
2. The CE-MCP cell (`agent/code_execution_executor.py`) hardcodes `AsyncOpenAI(api_key=...)` and has no Azure branch.
3. The judge provider (`global_runner.py:_get_judge_provider`) hardcodes the Azure deployment name to the literal string `"gpt-4.1"`.

## Decision

Three coupled choices, accepted together:

1. **Phase 1 runs on Azure OpenAI** with the model still pinned to `gpt-4.1-mini` (now meaning the Azure deployment of that model). The Phase-1 PRD's "OpenAI directly" line is superseded by this ADR.
2. **The vendored project is modified — narrowly, additively, reversibly.** Four edits enumerated in the Phase-1 PRD: add `gpt-4.1-mini` to the factory's Azure block; widen `CodeExecutionTaskExecutor.__init__` with optional Azure kwargs; teach `global_runner._execute_with_code_execution_agent` to detect Azure env vars and plumb them through; make the judge's Azure deployment name read from `AZURE_JUDGE_DEPLOYMENT` (default to `AZURE_AGENT_DEPLOYMENT`, finally to `"gpt-4.1-mini"`). Every edit preserves the OpenAI-direct path: `unset AZURE_OPENAI_API_KEY` reverts the harness to its shipped behaviour. This is a deviation from ADR-0001's spirit ("Phase 1 small-scale reproduction of the vendored CE-MCP numbers") and from the prior PRD's "The vendored project's code is not modified in this PRD" line.
3. **The judge deployment defaults to the same model as the agent (`gpt-4.1-mini`).** 2602.15945 used a distinct judge model from the agent model (gpt-4.1 for the judge, various for the agents). Same-model judging introduces an LLM-as-judge same-model-bias risk. The default is configurable via `AZURE_JUDGE_DEPLOYMENT`, so the moment the user deploys a separate judge model on Azure, the bias goes away without a code change.

## Consequences

- **Phase 1 numbers are not directly comparable to 2602.15945's published numbers** without an explicit anchor-shift note. The baseline numbers store and the calibration report must record the Azure-vs-OpenAI provenance so any later comparison is honest about the substitution. (`source: TBD` already covers the published-numbers absence; an `llm_provider: "azure"` field belongs next to it.)
- **The "no vendored modifications" invariant from ADR-0001 / the prior PRD is now broken.** Every later phase inherits a vendored project that has a small but real Azure carve-out. The carve-out is designed to be inert when Azure env vars are absent, but the diff exists and lives in version control.
- **The judge default carries a same-model-bias risk.** The Phase 1 calibration report's qualitative direction check (CE-MCP cheaper on multi-server / MCP-client cheaper on iterative-style tasks) is more robust to this bias than absolute judge scores; the bias risk lives in the judge scores. If absolute judge scores end up disagreeing strongly with 2602.15945's reported completion rate, suspecting same-model bias is the first hypothesis to test before suspecting harness damage.
- **Rollback is a single env-var unset away.** If the Azure switch ever needs to be reverted (e.g. to settle a reviewer concern about provider-specific drift), `unset AZURE_OPENAI_API_KEY AZURE_OPENAI_ENDPOINT && export OPENAI_API_KEY=…` returns the harness to its pre-ADR-0002 behaviour. The four vendored edits stay in place but become dead code paths.

## Rejected alternatives

- **Obtain an OpenAI-direct key and keep ADR-0001 / prior-PRD intent intact.** Cleanest theoretically, but the prior PRD already named OpenAI-direct as the path of *least* setup friction — that premise is wrong in this environment. Rejected as friction-without-benefit.
- **Switch the pinned model to `gpt-4o-mini`** (which is already in the vendored Azure factory block). Avoids the factory edit but introduces a bigger anchor-shift — `gpt-4o-mini` is a different model class than 2602.15945's reported numbers. Rejected: small code edit beats large measurement drift.
- **Skip the CE-MCP cell for Phase 1.** Cuts two of the four vendored edits. Phase 1 becomes a half-comparison and Phase 2's regression check is unanchored on the CE side. Rejected: defeats the point of Phase 1 (validate *both* halves of the eventual three-way comparison's vendored arms).
- **Monkey-patch `openai.AsyncOpenAI` from the calibration wrapper** to swap in an Azure client without editing vendored files. Preserves the vendored-disk-as-shipped invariant. Rejected as fragile: `AsyncOpenAI` and `AsyncAzureOpenAI` have different constructor signatures, and the patched site (CE executor) uses `model=...` where Azure needs `model=<deployment_name>` — the substitution leaks semantics. A clean four-line additive edit is more honest than a patch that can break on any vendored update.
- **Hardcode the judge deployment to `"gpt-4.1-mini"` (same as agent) without an env var.** Simpler. Rejected: the env-var indirection costs nothing and makes the same-model-bias fix a configuration change rather than a code change.

## References

- ADR-0001 — Headline framing, three-architecture comparison, incremental build from vendored project.
- Issue #1 — Phase 1: Vendored project calibration check (Azure-pinned). This ADR is referenced from the PRD's Implementation Decisions / Further Notes.
- `cemcpsec-C1F2/Performance Evaluation/mcp-bench/llm/factory.py` — `LLMFactory.get_model_configs()` Azure block.
- `cemcpsec-C1F2/Performance Evaluation/mcp-bench/agent/code_execution_executor.py` — `CodeExecutionTaskExecutor.__init__` hardcoded OpenAI client.
- `cemcpsec-C1F2/Performance Evaluation/mcp-bench/global_runner.py` — `_execute_with_code_execution_agent` and `_get_judge_provider`.
- 2602.15945 (Felendler et al., CE-MCP paper) — original judge model + comparison numbers being substituted away from in Phase 1.
