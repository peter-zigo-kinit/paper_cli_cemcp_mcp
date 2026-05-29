# Two-pairing judge-and-agent model deployment

## Status

Accepted. Partially supersedes ADR-0002's "judge defaults to the same model as the agent" decision.

## Context

ADR-0002 pinned both the agent and the judge to `gpt-4.1-mini` on Azure, with the judge deployment configurable via `AZURE_JUDGE_DEPLOYMENT`. It flagged same-model bias as a known risk to be removed "the moment the user deploys a separate judge model on Azure" — and deferred that step.

That moment arrived. The user has now deployed `gpt-4o` and `gpt-5` on the same Azure resource as separate judge candidates. The project also needs two distinct evaluation contexts:

1. **Paper-replication context.** Reproduce CE-MCP (2602.15945) direction and magnitude on MCP-Bench using models close to what Felendler et al. used. Their judge was 3× GPT-4o averaged. Available to us: gpt-4o on Azure as a separate judge deployment.
2. **Development / headline context.** Run the three-cell comparison at the current frontier. The strongest reasonably-priced agent+judge pairing on the Azure deployment is gpt-5-mini agent + gpt-5 judge.

Same-model bias is fully avoided in pairing 1 (different families: 4.1 vs 4o) and reduced but not eliminated in pairing 2 (same family, different sizes).

The draft paper's three-tier model sweep (`draft_paper.md` §5.3: frontier / mid / local-GPU) is being scoped down to these two pairings for the current phase; the local-GPU tier becomes future work.

## Decision

Two coupled choices, accepted together:

1. **Adopt two named evaluation pairings.** Replace the single (agent, judge) pin with:

   | Pairing | Agent | Judge | Role |
   |---|---|---|---|
   | `paper` | `gpt-4.1-mini` | `gpt-4o` | Replication of 2602.15945 direction/magnitude on the same harness |
   | `dev` | `gpt-5-mini` | `gpt-5` | Headline three-cell comparison at the frontier |

   The `paper` pairing matches Felendler et al.'s pattern of *agent smaller than judge*, with one judge × 5 shuffles substituting for their 3 judges × 1 prompt — defended by MCP-Bench Table 7's evidence that prompt shuffling is a valid robustness mechanism. The `dev` pairing carries a residual same-family bias note (gpt-5.x agent + gpt-5.x judge) that belongs in threats-to-validity.

2. **Add a thin runner wrapper that translates `--pairing paper|dev` into the Azure-deployment env vars the vendored harness reads.** The user's `.env` carries the pairing definitions as `{JUDGE,AGENT}_{PAPER,DEV}_MODEL=…`. The vendored harness reads `AZURE_AGENT_DEPLOYMENT` and `AZURE_JUDGE_DEPLOYMENT`. A wrapper (location TBD — likely `tools/run-mcp-bench.sh` or similar) picks the pairing and exports the right values before launching `global_runner.py`. The vendored harness itself is not modified further. The dead env-var line `JUDGE_MODEL=…` from the pre-ADR `.env` should be removed in the same change.

## Consequences

- **Absolute scores across the two pairings are not comparable** — different judge models produce different score distributions. What IS comparable across pairings: direction of cell ranking (e.g., "CE-MCP wins on tokens" should hold in both pairings — if it doesn't, that's a finding) and sign of token/latency/reliability deltas (judge-independent).
- **The same-model-bias risk flagged in ADR-0002 is resolved for the `paper` pairing** and reduced but not eliminated for the `dev` pairing. Threats-to-validity in the draft paper needs one sentence acknowledging the residual same-family bias in the `dev` pairing.
- **`draft_paper.md` §5.3's three-tier table (frontier / mid / local-GPU) needs to be revised** to the two-pairing form above. Logged in [[evaluation-strategy]] §6 as a pending draft edit. Local-GPU tier becomes future work.
- **Judge instance count diverges from Felendler.** They averaged across 3 GPT-4o judge instances; we use 1 judge × 5 shuffles. Defended by MCP-Bench Table 7. If a camera-ready reviewer pushes back specifically on this, we re-run a small subset of `paper`-pairing tasks with 3 judges and compare to single-judge × 5-shuffle as a sensitivity check.
- **A runner wrapper is now a load-bearing piece of infrastructure.** Without it, the new `.env` entries are dead and the harness silently falls back to whatever `AZURE_AGENT_DEPLOYMENT` happens to be. The wrapper is small but must exist before any experiment claims "ran in paper pairing".

## Rejected alternatives

- **Full Felendler replication (3× GPT-4o judge averaging).** Closest match to 2602.15945 but ~3× the judge-API cost per task. Rejected for now: 1 judge × 5 shuffles is harness-native (already implemented) and the variance-reduction story is the same. Kept available as a sensitivity-analysis fallback.
- **Keep the single-pairing setup from ADR-0002 (gpt-4.1-mini agent + gpt-4.1-mini judge) and argue symmetric same-model bias.** Defensible as a within-study ranking story but fragile in peer review — the asymmetry concerns (e.g., judges over-rate fluent narrative output, which advantages MCP-client's chatty trajectories over CE-MCP's terse final answers) cannot be ruled out a priori. Rejected: the cost of removing the bias is now low (deployment already exists).
- **Use a third pairing for "mid-tier" (e.g., Claude Haiku or GPT-4o-mini as the agent).** Adds breadth but triples the experiment cost. Rejected for now: deferred to future work, sequenced after the two-pairing story is in shape.
- **Have the vendored harness directly read `JUDGE_PAPER_MODEL` / `AGENT_PAPER_MODEL` etc.** Avoids the wrapper but requires a fifth vendored code edit on top of ADR-0002's four. Rejected: keeps the vendored carve-out as small and reversible as possible. The wrapper is in our code, not theirs.
- **Modify `.env` to use `AZURE_AGENT_DEPLOYMENT` / `AZURE_JUDGE_DEPLOYMENT` directly and toggle between pairings by editing `.env`.** Works but loses the named-pairing affordance and risks half-edited `.env` states between runs. Rejected: a wrapper that picks the pairing in one place is safer.

## References

- ADR-0001 — Headline framing, three-architecture comparison, incremental build from vendored project.
- ADR-0002 — Azure pin and judge config. This ADR partially supersedes "judge defaults to same model as agent".
- [[evaluation-strategy]] §7.1 — judge model open question; now resolved by this ADR.
- [[mcp-bench]] §4.3 — MCP-Bench Table 7 prompt-shuffling validation evidence.
- [[ce-mcp]] §3.3 — Felendler et al.'s 3× GPT-4o judge averaging.
- `paper_draft/draft_paper.md` §5.3 — model-tier table needing revision per this ADR.
