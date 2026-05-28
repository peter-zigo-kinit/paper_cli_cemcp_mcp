# `tools/` — project-level MCP servers

External MCP servers used by Claude Code (and humans) while working on this project. These are **not** part of the MCP-bench experiment under `cemcpsec-C1F2/`, which has its own separate `mcp_servers/` checkout that the benchmark measures.

Each subdirectory here is an upstream clone, gitignored. To get a fresh checkout running, clone and `uv sync` each one per the table below.

| Server | Upstream | Used for |
| --- | --- | --- |
| `paper-search-mcp/` | https://github.com/openags/paper-search-mcp | Searching + downloading + reading papers (arXiv, PubMed, bioRxiv, Semantic Scholar, etc.). Primary use case: pulling 2602.15945 and related works into the workspace for the paper draft. |

## Setup

From the repo root:

```bash
# paper-search-mcp
git clone https://github.com/openags/paper-search-mcp tools/paper-search-mcp
(cd tools/paper-search-mcp && uv sync)
```

`uv` is required. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh` if missing.

## Wiring

`.mcp.json` at the repo root registers each server with Claude Code via project-relative `--directory` paths. After cloning + `uv sync`, the next Claude Code session in this project picks it up automatically.

## Optional credentials

- **Semantic Scholar API key.** Without it, the `search_semantic` tool still works but at a lower rate limit. Get a free key at https://www.semanticscholar.org/product/api and add it as `SEMANTIC_SCHOLAR_API_KEY` in `.mcp.json` (or in your shell `.env` if you prefer keeping the file untouched — Claude Code reads env-var references in `.mcp.json`).

## Available tools (paper-search-mcp)

| Category | Tools |
| --- | --- |
| Search | `search_arxiv`, `search_pubmed`, `search_biorxiv`, `search_medrxiv`, `search_google_scholar`, `search_iacr`, `search_semantic`, `search_crossref`, `get_crossref_paper_by_doi` |
| Download | `download_arxiv`, `download_biorxiv`, `download_medrxiv`, `download_iacr`, `download_semantic` (PDFs to `./downloads` by default) |
| Read | `read_arxiv_paper`, `read_biorxiv_paper`, `read_medrxiv_paper`, `read_iacr_paper`, `read_semantic_paper` (extracts full text from a downloaded PDF) |

`download_pubmed` and `download_crossref` exist but are metadata-only (no PDF support).
