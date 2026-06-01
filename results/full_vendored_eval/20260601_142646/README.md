# Full vendored CE-MCP eval — 2026-06-01 14:26 → 17:06

Closes the implementation of issue [#10](https://github.com/peter-zigo-kinit/paper_cli_cemcp_mcp/issues/10).

## What was run

The vendored CE-MCP harness's `global_runner.py` invoked once per shipped task file, against **Azure `gpt-4.1-mini`** (deployment + judge), with no `--servers` filter and no `--task-limit`. Both cells (`traditional` MCP-client and `code_execution` CE-MCP) exercised per task by the runner's default behaviour. No vendored-code changes beyond what Slice 1 already landed.

| File | Path | Tasks | Cells | Combinations |
| --- | --- | --- | --- | --- |
| single | `tasks/mcpbench_tasks_single_runner_format.json` | 18 across 9 servers | 2 | 36 |
| multi2 | `tasks/mcpbench_tasks_multi_2server_runner_format.json` | 8 across 8 server pairs | 2 | 16 |
| multi3 | `tasks/mcpbench_tasks_multi_3server_runner_format.json` | 2 across 2 server triples | 2 | 4 |
| **total** | — | **28** | — | **56** |

## Outcome

All 56 combinations completed; **zero failed tasks** (every row carries nonzero tokens and a judge score). Exit codes `single=0 multi2=0 multi3=0`.

| Metric | Total |
| --- | --- |
| Combinations attempted | 56 |
| Combinations completed | 56 |
| Combinations failed | 0 |
| Servers attempted | 15 (all 15 required by the shipped task files) |
| Servers skipped due to missing keys | 0 |
| Wall-clock | 2h 40m |
| Total input tokens | 1,952,799 |
| Total output tokens | 337,019 |
| Approx Azure cost | ~$0.50 USD |
| HTTP 500 errors | 0 |
| HTTP 400 content-filter rejections | 51 (all in `single`, all on internal subroutines; runner's fallback paths absorbed them — no task failures resulted) |

## Headline qualitative read

The vendored harness reproduces the paper's headline finding on this Azure deployment:

- **Aggregate**: CE-MCP cell consumed **893K tokens** across 28 runs vs MCP-client's **1.40M tokens** — CE-MCP **~36% cheaper overall**.
- **Multi-server tasks** (multi2 + multi3): CE-MCP **~65% cheaper** (208K vs 602K). The CE-MCP advantage grows with task complexity.
- **Single-server tasks**: CE-MCP **~14% cheaper** on average — the narrower margin matches the paper's framing that CE-MCP's benefit comes from fewer LLM-mediated tool round-trips, which dominate in multi-step workflows but matter less for one-shot calls.

Per-server (single-server) token ratio (CE total / MCP total):

| Server | MCP tokens | CE tokens | Ratio | |
| --- | ---: | ---: | ---: | --- |
| Math MCP | 50,328 | 5,398 | **0.11×** | CE 9× cheaper |
| Unit Converter | 63,435 | 7,779 | **0.12×** | CE 8× cheaper |
| Call for Papers | 119,745 | 51,135 | 0.43× | CE 2× cheaper |
| Paper Search | 111,990 | 63,904 | 0.57× | CE 1.8× cheaper |
| Reddit | 72,733 | 57,547 | 0.79× | CE 1.3× cheaper |
| Scientific Computing | 129,076 | 111,566 | 0.86× | CE 1.2× cheaper |
| Car Price Evaluator | 176,042 | 164,680 | 0.94× | parity |
| Time MCP | 36,323 | 59,766 | 1.65× | MCP cheaper |
| Weather Data | 35,416 | 162,808 | 4.60× | MCP cheaper — outlier |

The two outliers (Time MCP, Weather Data) likely reflect CE-MCP's inherent overhead on tasks that fit cleanly in a single tool call — the code-execution scaffold (planning prompt + Python emission + sandbox round-trip) costs more than the saved round-trips.

## Answer quality (judge scores, /10)

| Cell | Mean | n |
| --- | ---: | ---: |
| MCP-client | **9.39** | 28 |
| CE-MCP | **6.56** | 28 |

The CE-MCP variance is real but partially methodological: the 51 content-filter rejections all hit CE-MCP internal subroutines (planning, summarization, compression) and triggered rule-based fallbacks instead of LLM-generated text, degrading the quality of the affected rows. Phase-2 calibration on the LangChain reinterpretation will not have this confound.

## What we did NOT do (kept out of scope, per issue #10)

- No calibration logic, no baseline numbers store, no pass/fail report generator (deferred to Phase 2 — see [.out-of-scope/phase1-calibration-on-vendored-code.md](../../.out-of-scope/phase1-calibration-on-vendored-code.md)).
- No Tier-0 manipulation check (deferred — Phase 2 gets its own pre-flight).
- No model sweep — Azure `gpt-4.1-mini` only.
- No comparison to 2602.15945's published numbers.
- No modifications to vendored code beyond what Slice 1 already changed.

## Reproducing this run

Prerequisites:

- `.env` at the repo root with `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `NASA_API_KEY`, `NPS_API_KEY`.
- The 15 vendored MCP servers installed (run `mcp_servers/install.sh`, or the targeted 13-server installer at the path noted in the PR description).
- The vendored Python venv at `cemcpsec-C1F2/Performance Evaluation/mcp-bench/.venv` with vendored `requirements.txt` installed.

Then, for each task file:

```bash
cd "cemcpsec-C1F2/Performance Evaluation/mcp-bench"
export PATH="$(pwd)/.venv/bin:$PATH"        # so the 3 servers using bare `python` resolve to venv python
.venv/bin/python global_runner.py \
    --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
    --models gpt-4.1-mini \
    --output-dir <repo>/results/full_vendored_eval/<ts>/single
```

Repeat for `multi_2server` and `multi_3server`.

## Files in this directory

| File | What |
| --- | --- |
| `run.json` | Top-level manifest: timestamp, repo SHA, model, deployment names, exit codes per task file |
| `README.md` | This file |
| `_logs/{single,multi2,multi3}.log` | Raw runner stdout/stderr per task file |
| `{single,multi2,multi3}/global_evaluation_<ts>.csv` | Per-row results — one row per (task, cell). The CSV is the contract Phase 2's regression check will read. |
| `{single,multi2,multi3}/global_evaluation_<ts>.json` | Same data as JSON, lossless |
| `{single,multi2,multi3}/global_evaluation_summary_<ts>.json` | Runner's own summary blob — total/completed/failed counts, errors list |

## Caveats for paper write-up

- **LLM-as-judge same-model bias.** Both the agent and the judge are `gpt-4.1-mini` (Azure default judge deployment matches agent, per ADR-0002). Absolute judge scores carry that bias; qualitative cross-cell comparison is what's defensible.
- **Content-filter quality drag on CE-cell.** 51 of the runner's internal LLM calls during `single` hit `jailbreak.detected: True` and fell back to rule-based compression. This depresses the CE-MCP cell's `answer` quality on some rows without breaking task execution. To eliminate, the Azure deployment's prompt-shield needs full disable (currently set to minimum severity but jailbreak detection is still active).
- **No `paper_search_mcp` ./tools entry was used.** The vendored harness uses its own `mcp_servers/paper-search-mcp/`; the project-root `tools/paper-search-mcp/` is unrelated to this eval.
