# Phase 1 calibration on the vendored code

The project does not run a Phase-1 *calibration* layer on top of the vendored CE-MCP harness. Calibration — a re-runnable, scope-pinned anchor that future regression checks read against, with a baseline numbers store and a pass/fail/deferred report — was originally scoped as Phase 1 (issue #1, with implementation slices #4, #5, #6). All four were closed `wontfix` after the maintainer decided to skip calibration on the vendored harness and apply it later to the Phase-2 LangChain reinterpretation instead.

## Why this is out of scope

The vendored harness exists in this repo to *reproduce* the CE-MCP paper's evaluation, not to become the long-lived measurement substrate. Phase 2 replaces the vendored LLM client with a LangChain-based client and reintroduces reliability instrumentation; that swap is the point at which it becomes worth the engineering effort to build a calibration anchor, because Phase 2's deliverable is *itself* a harness whose numbers later phases will compare against.

Anchoring calibration on the vendored code instead would have meant:

- Building three Phase-1 modules (calibration runner wrapper, Tier-0 manipulation check, baseline store + pure report function) that the LangChain swap would either replace or invalidate weeks later.
- Pinning the on-disk results schema to whatever the vendored `CSVTracker` and `GlobalRunner.run()` happen to write, then re-pinning it after the Phase-2 swap when the LangChain client's reliability instrumentation produces a richer record.
- Maintaining a Phase-1 baseline JSON with `source: TBD` slots that nothing read until Phase 2 came along and replaced the substrate underneath it.

The simpler shape is: run the vendored harness *as-is* on its shipped task files (issue #10) to capture what the CE-MCP authors' implementation produces against our Azure deployment, then build calibration once — on the LangChain interpretation, against numbers we trust because we wrote the client.

## What replaces it

Issue #10 — "Full vendored CE-MCP performance evaluation on Azure `gpt-4.1-mini`" — runs every task in the shipped task files through the vendored runner unmodified, both cells, no calibration tooling. Phase 2 then builds the LangChain client and the calibration layer on top of *that*.

```text
Phase 1 (issue #3 + #10) — vendored harness reproduces the paper's runs on Azure
Phase 2                  — LangChain LLM-client swap + reliability instrumentation
Phase 2 (calibration)    — baseline store + report generator built on the LangChain client
Phase 3+                 — model sweep, complexity sweep, CLI-wrapper cell, multi-server etc.
```

The Phase-2 calibration carries forward several pieces from the original Phase-1 PRD that remain individually sensible — the pure-function shape of the report generator, the `source: TBD` baseline pattern, the Tier-0 manipulation-check idea — but applied to the LangChain client, not to the vendored code path.

## Prior requests

- #1 — Phase 1: Vendored project calibration check (Azure-pinned)
- #4 — Slice 2: Calibration runner wrapper + on-disk output schema
- #5 — Slice 3: Tier-0 manipulation check entry point
- #6 — Slice 4: Baseline numbers store + calibration report generator
