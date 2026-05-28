# Paper: Controlled Benchmark Comparison of MCP-Client, CLI-Wrapper, and Code-Execution-MCP Agents

The repo holds the paper draft (`paper_draft/`) and the starting-point implementation for the empirical work (`cemcpsec-C1F2/Performance Evaluation/`, vendored from the CE-MCP paper artifact). Glossary terms below are the canonical names used in the paper text, experiment plan, code, and issues; the existing vendored project uses several aliases that must be translated.

## Language

### Cells (the three agent architectures under comparison)

**MCP-client**:
The baseline architecture. An agent runs an in-context ReAct loop; tool schemas and JSON-RPC responses are injected into model context every turn. Realised in the vendored project as `agent/executor.py`.
_Avoid_: "Traditional MCP Agent" (vendored project's label), "direct MCP", "MCP host" (the latter is the role, not the architecture).

**CLI-wrapper**:
The same underlying MCP servers exposed as CLI commands; agent runs an in-context ReAct loop issuing one CLI subcommand per turn. Does not exist in the vendored project — to be built.
_Avoid_: "CLI agent" (overloaded with general-purpose CLI coding agents like Claude Code), "MCP-as-CLI" (ambiguous on direction).

**CE-MCP**:
Code-Execution MCP per Felendler et al. (2602.15945). Four-phase: post-query lazy discovery → code generation → sandboxed execution → final-result return. Realised in the vendored project as `agent/code_execution_executor.py` + `agent/dynamic_tool_discovery.py`.
_Avoid_: "Code Execution Agent" (vendored project's label — drop the "agent" suffix in paper-side text to disambiguate from CodeAct's general "code-action agent"), "CE" alone (ambiguous).

### Comparison axes

**Surface representation**:
How tool definitions and invocations reach the model. Two values in this project: MCP JSON-RPC schemas vs CLI help text / subcommands.
_Avoid_: "tool interface" (ambiguous with "tool calling format"), "representation" alone.

**Orchestration locus**:
Where tool calls are sequenced. Two values: in-context (ReAct loop in model context) vs sandbox (model emits one program, sandbox executes the call sequence, only the final result returns).
_Avoid_: "execution model", "execution mode" — both used inconsistently in the vendored project.

### Framing

**Three architectures (Option B)**:
Each cell is treated as a deployed system as practitioners use it; the comparison is between strategies, not between single-axis controlled variants. See `docs/adr/0001-...` once written.
_Avoid_: "2×2 factorial", "factorial design" — these were considered and rejected for this paper.

## Flagged ambiguities

- **"Agent"** is overloaded. In the vendored project it names the cell ("Traditional Agent" / "Code Execution Agent"). In the paper it names the runtime entity that uses a cell. Resolution: prefer **cell** when naming the architecture under test; reserve **agent** for the model+loop runtime.
- **"Token usage"** appears in the vendored project as a single number; the paper requires input/output/total broken out separately. Always specify the breakdown in this project.

## Example dialogue

> Engineer: "Did the traditional agent's run finish?"
> Researcher: "Use *MCP-client cell* — 'traditional' is the vendored label. And which token breakdown — input only, or total?"
> Engineer: "Total, on the medium-complexity tasks."
> Researcher: "OK. That's MCP-client × medium-complexity, total tokens. The orchestration locus is in-context for both MCP-client and CLI-wrapper, so any difference is the surface representation."
