# Headline framing, three-architecture comparison, incremental build from vendored project

## Context

The original paper plan (`paper_draft/draft_paper.md` + `paper_draft/experiment.md`) named four candidate framings (decision matrix; refutation of gray lit; first controlled three-way; RQ3 capability threshold), implicitly tried to be all of them, and §6 itself flagged "RQ3 capability threshold" as the most scoop-resistant option. The plan also assumed a from-scratch harness on MCP-Universe (primary) + MCP-Bench (secondary), with execution-based evaluators and a 3-cell × 3-model-tier × 3-complexity-tier design. A vendored CE-MCP authors' implementation exists at `cemcpsec-C1F2/Performance Evaluation/mcp-bench/` covering ~30% of that plan: MCP-Bench only, LLM-as-judge only, OpenAI/Azure only, two cells (MCP-client + CE-MCP), no CLI-wrapper, no held-constant discovery.

## Decision

Three coupled choices, accepted together:

1. **Headline = (a) developer decision matrix + (c) first controlled three-way comparison.** RQ3 capability threshold demoted from headline to a finding that falls out of the matrix. Refutation of gray-lit numbers is a byproduct, not a contribution.
2. **Comparison frame = three architectures, not a 2×2 factorial.** Each cell is treated as the deployed strategy a practitioner would use, not as a single-axis controlled variant. The `experiment.md §1` 2×2 table and `draft_paper.md §3.4` "this is not a 2×2" sentences must both be rewritten to align on this framing. The two underlying axes (surface representation, orchestration locus) remain in `CONTEXT.md` as analytical vocabulary but are not the comparison structure.
3. **Build = incremental staircase from the vendored project.** Phase 1 small-scale reproduction of the vendored CE-MCP numbers as a manipulation check; Phase 2 swap the OpenAI/Azure LLM layer for a framework-agnostic one (LangChain, with LangSmith telemetry — chosen over PydanticAI/Logfire to gain LangChain experience); Phase 3 add the CLI-wrapper cell over MCP-Bench's vendored servers; Phase 4 add MCP-Universe harness; Phase 5 add execution-based evaluators. Each phase has its own go/no-go gate.

## Consequences

- **Calendar scoop is now the dominant risk** on contribution (c). The most scoop-resistant framing was deliberately not chosen; mitigation must come from execution speed and artefact release, not framing.
- **The decision matrix needs a synthesis layer.** 108 raw numbers (3 cells × 3 model tiers × 3 complexity tiers × 4 metrics) is not a usable developer artefact; the paper owes a one-glance "given X, pick Y" output on top of the tables.
- **"Controlled" is now load-bearing twice** — both (a) and (c) collapse if reviewers don't believe the comparison is controlled. Implementation-parity protocol (`experiment.md §5.6 / §7.4`) becomes the single most important section to defend.
- **The vendored project's discovery asymmetry must be fixed before any final-run numbers are produced.** CE-MCP's source-file scanning vs MCP-client's pre-connection MCP-protocol enumeration is a built-in parity violation; left alone it would invalidate the "controlled" claim independent of any other axis.
- **Each staircase phase may end the paper.** If Phase 4 (MCP-Universe harness) proves infeasible, the paper contracts to "controlled three-way on MCP-Bench with the existing LLM-judge, calibrated against CE-MCP's published numbers." That is a narrower but still-publishable claim; we accept that outcome rather than over-commit to MCP-Universe up front.

## Rejected alternatives

- **(d) RQ3 capability threshold as headline.** Was the §6-identified least-scoopable option but yields a less useful developer artefact and a less defensible "first" claim. Rejected in favour of (a)+(c).
- **2×2 factorial framing.** Single-variable-diff arms are scientifically cleaner but make the CE-CLI omission (`draft_paper.md §3.4`) read as a missing data point rather than a principled exclusion. Rejected.
- **B3 (build fresh MCP-Universe harness; vendored project = CE-MCP replication only).** Most defensible end-state but commits maximum engineering up front with no intermediate exit. B4 reaches the same end-state with optional stopping points. Rejected.
- **B1 (ride the vendored project as-is to write-up).** Fastest, but the resulting paper is "CE-MCP replication on more models," not the planned three-way comparison. Rejected.
