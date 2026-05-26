# MCP-Bench with Code Execution Agent

## Overview

This repository extends the original **MCP-Bench** framework with a novel **Code Execution Agent** that uses dynamic tool discovery, code generation, and execution to solve complex tasks. The framework now supports comprehensive evaluation comparing both traditional MCP agents and code execution agents across multiple dimensions, including task performance, token usage, execution time, number of turns, and more.

### What's New: Code Execution Agent

The Code Execution Agent represents a paradigm shift from traditional tool-calling approaches:

- **Dynamic Tool Discovery**: Scans `mcp_servers` directory to discover tools from source files without requiring pre-connection
- **Code Generation**: Uses LLMs to generate Python code that programmatically calls MCP tools
- **Code Execution**: Executes generated code in a controlled environment using `exec()`
- **Fault Tolerance**: Multi-turn execution with error correction and retry logic
- **Task-Aware Discovery**: Analyzes task requirements to identify and discover only relevant servers/tools
- **Comprehensive Evaluation**: Compare both agents across tokens, time, performance, turns, and more

### Original MCP-Bench

The original MCP-Bench provides:
- **Traditional MCP Agent**: Direct tool calling through MCP protocol
- **Multi-Round Execution**: Strategic planning and parallel tool execution
- **28 MCP Servers**: Diverse real-world tools (Wikipedia, NASA, National Parks, etc.)
- **LLM-as-Judge Evaluation**: Automated task completion assessment

## Key Differences from Original MCP-Bench

### New Components

1. **`agent/code_execution_executor.py`**: Code execution agent that generates and runs Python code
2. **`agent/dynamic_tool_discovery.py`**: Dynamic tool discovery by scanning server source files
3. **`global_runner.py`**: Comprehensive evaluation runner that executes both agents and compares results
4. **Enhanced Evaluation**: Metrics for tokens, time, turns, code quality, and agent comparison

### Architecture Differences

| Feature | Original MCP-Bench | Extended Version |
|---------|-------------------|------------------|
| Tool Discovery | Pre-connection via MCP protocol | Dynamic scanning of source files |
| Execution Model | Direct tool calls | Code generation + execution |
| Agent Types | Traditional only | Traditional + Code Execution |
| Evaluation | Task completion only | Multi-dimensional comparison |
| Runner | `benchmark/runner.py` | `global_runner.py` (runs both agents) |

## Installation

### Prerequisites

- Python 3.10+
- Conda (recommended) or virtual environment
- Git
- OpenAI API key (for code execution agent)
- OpenRouter API key (for traditional agent) or Azure OpenAI

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd mcp-bench
```

### Step 2: Set Up Python Environment

```bash
# Create conda environment
conda create -n mcpbench python=3.10
conda activate mcpbench

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install MCP server dependencies
cd mcp_servers
bash install.sh  # On Windows, use WSL or Git Bash
cd ..
```

**Note for Windows**: The `install.sh` script requires a Unix-like environment. Use WSL (Windows Subsystem for Linux) or Git Bash:

```powershell
# Option 1: Use WSL
wsl
cd /mnt/c/path/to/mcp-bench/mcp_servers
bash install.sh

# Option 2: Use Git Bash
# Open Git Bash and navigate to mcp_servers directory
bash install.sh
```

### Step 4: Configure Environment Variables

Create a `.env` file in the `mcp-bench` directory:

```bash
# For Code Execution Agent (required)
export OPENAI_API_KEY="your-openai-api-key-here"

# For Traditional Agent (choose one)
export OPENROUTER_API_KEY="your-openrouter-key-here"
# OR
export AZURE_OPENAI_API_KEY="your-azure-key-here"
export AZURE_OPENAI_ENDPOINT="your-azure-endpoint-here"
```

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY="your-openai-api-key-here"
$env:OPENROUTER_API_KEY="your-openrouter-key-here"
```

**Windows Command Prompt:**
```cmd
set OPENAI_API_KEY=your-openai-api-key-here
set OPENROUTER_API_KEY=your-openrouter-key-here
```

### Step 5: Configure MCP Server API Keys

Some MCP servers require external API keys. Edit `mcp_servers/api_key`:

```bash
NPS_API_KEY=your-nps-key-here
NASA_API_KEY=your-nasa-key-here
HF_TOKEN=your-huggingface-token-here
GOOGLE_MAPS_API_KEY=your-google-maps-key-here
NCI_API_KEY=your-nci-key-here
```

**Quick Links for API Keys** (all free and easy to get):
- [NPS API Key](https://www.nps.gov/subjects/developer/get-started.htm)
- [NASA API Key](https://api.nasa.gov/)
- [Hugging Face Token](https://huggingface.co/docs/hub/security-tokens)
- [Google Maps API Key](https://developers.google.com/maps)
- [NCI API Key](https://clinicaltrialsapi.cancer.gov/signin)

### Step 6: Verify Installation

```bash
# Verify MCP servers can be connected
python utils/collect_mcp_info.py
# Should see "28/28 servers connected"

# List available models
source .env  # On Windows: just set env vars
python run_benchmark.py --list-models
```

## Usage

### Quick Start: Run Both Agents

The `global_runner.py` executes both traditional and code execution agents and compares results:

```bash
# Run all tasks with both agents
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json

# Run with filters
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
  --servers Wikipedia \
  --models gpt-4.1-mini \
  --task-limit 5
```

### Run Traditional Agent Only

```bash
# Using benchmark runner
python run_benchmark.py --models gpt-4o

# Single server tasks
python run_benchmark.py \
  --models gpt-4o \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json

# Multi-server tasks
python run_benchmark.py \
  --models gpt-4o \
  --tasks-file tasks/mcpbench_tasks_multi_2server_runner_format.json
```

### Run Code Execution Agent Only

```bash
# Using global runner (filters to code execution results)
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
  --models gpt-4.1-mini \
  --servers Wikipedia
```

### Command Line Options

#### Global Runner (`global_runner.py`)

```bash
python global_runner.py \
  --tasks-file <path> \          # Required: Path to tasks JSON file
  --task-limit <number> \        # Optional: Limit number of tasks
  --servers <server1> <server2> \ # Optional: Filter by server names
  --models <model1> <model2> \   # Optional: Filter by model names
  --output-dir <dir> \           # Optional: Output directory (default: ./results)
  --verbose                      # Optional: Enable verbose logging
```

**Examples:**

```bash
# Run Wikipedia tasks with both agents
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_multi_2server_runner_format.json \
  --servers Wikipedia \
  --task-limit 3

# Compare specific models
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
  --models gpt-4o gpt-4.1-mini \
  --task-limit 10

# Run all tasks (may take a long time)
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json
```

#### Benchmark Runner (`run_benchmark.py`)

```bash
python run_benchmark.py \
  --models <model1> <model2> \   # Required: Model names
  --tasks-file <path> \          # Optional: Tasks file (default from config)
  --list-models                   # List available models
```

## Architecture

### Code Execution Agent Flow

```
Task Input
    ↓
Dynamic Tool Discovery
    ├─ Analyze task keywords
    ├─ Identify relevant servers
    ├─ Scan server source files
    └─ Extract tool definitions
    ↓
Code Generation (LLM)
    ├─ Generate Python code
    ├─ Include tool calls
    └─ Add error handling
    ↓
Code Execution
    ├─ Execute in controlled environment
    ├─ Capture output
    └─ Handle errors
    ↓
Multi-Turn Refinement
    ├─ Analyze results
    ├─ Fix errors
    └─ Improve code
    ↓
Final Answer
```

### Traditional Agent Flow

```
Task Input
    ↓
Tool Discovery (MCP Protocol)
    ├─ Connect to servers
    ├─ List available tools
    └─ Build tool registry
    ↓
Multi-Round Planning
    ├─ Plan tool calls
    ├─ Execute in parallel
    └─ Accumulate results
    ↓
Result Synthesis
    └─ Generate final answer
```

### Project Structure

```
mcp-bench/
├── agent/                          # Task execution agents
│   ├── executor.py                 # Traditional MCP agent
│   ├── code_execution_executor.py  # Code execution agent ⭐ NEW
│   ├── dynamic_tool_discovery.py   # Dynamic tool discovery ⭐ NEW
│   └── execution_context.py        # Execution state management
├── benchmark/                      # Evaluation framework
│   ├── runner.py                   # Benchmark orchestrator
│   ├── evaluator.py                # LLM-as-judge evaluation
│   ├── results_aggregator.py       # Results aggregation
│   └── results_formatter.py        # Results formatting
├── global_runner.py                # Comprehensive evaluation runner ⭐ NEW
├── config/                         # Configuration management
│   ├── benchmark_config.yaml       # Benchmark settings
│   └── config_loader.py            # Config loader
├── llm/                            # LLM provider abstractions
│   ├── factory.py                  # Model factory
│   └── provider.py                 # Provider interface
├── mcp_modules/                    # MCP server management
│   ├── connector.py                # Server connections
│   ├── server_manager_persistent.py # Persistent connections
│   └── tool_cache.py               # Tool call caching
├── tasks/                          # Benchmark task files
│   ├── mcpbench_tasks_single_runner_format.json
│   ├── mcpbench_tasks_multi_2server_runner_format.json
│   └── mcpbench_tasks_multi_3server_runner_format.json
└── mcp_servers/                    # 28 MCP server implementations
    ├── commands.json               # Server configurations
    ├── api_key                     # API keys file
    └── [28 server directories]
```

## Evaluation Metrics

The global runner compares both agents across multiple dimensions:

### Performance Metrics

- **Task Completion Rate**: Percentage of tasks successfully completed
- **LLM Judge Score**: Quality assessment by LLM-as-judge (0-1 scale)
- **Schema Compliance**: Adherence to tool parameter schemas

### Efficiency Metrics

- **Token Usage**: Total tokens consumed (prompt + completion)
- **Execution Time**: Time to complete task
- **Number of Turns**: Iterations/rounds required
- **Tool Calls**: Number of tool invocations

### Code Execution Specific

- **Code Quality**: Syntax correctness, error handling
- **Code Execution Success**: Percentage of successful code runs
- **Error Recovery**: Ability to fix errors across turns

### Comparison Metrics

- **Agent Comparison**: Side-by-side performance comparison
- **Win Rate**: Which agent performs better per task
- **Efficiency Ratio**: Token/time efficiency comparison

## MCP Servers

The framework includes 28 diverse MCP servers:

- **Wikipedia** - Encyclopedia content search and retrieval
- **NASA Data** - Space mission data and astronomical information
- **National Parks** - US National Parks information and visitor services
- **Unit Converter** - Measurement conversions across different unit systems
- **Math MCP** - Mathematical calculations and computational operations
- **Weather Data** - Weather forecasts and meteorological information
- **Google Maps** - Location services, geocoding, and mapping functionality
- **Hugging Face** - Machine learning models, datasets, and AI capabilities
- **Metropolitan Museum** - Art collection database and museum information
- **BioMCP** - Biomedical research data, clinical trials, and health information
- **Paper Search** - Academic paper search across multiple research databases
- **Reddit** - Social media content and community discussions
- And 17 more...

See the original [MCP-Bench paper](https://arxiv.org/abs/2508.20453) for complete server list.

## Dynamic Tool Discovery

The Code Execution Agent uses dynamic tool discovery to find tools without pre-connection:

### How It Works

1. **Task Analysis**: Analyzes task description for keywords (e.g., "wikipedia", "weather", "math")
2. **Server Identification**: Maps keywords to server directories
3. **Source File Scanning**: Scans Python/TypeScript/JavaScript files for tool definitions
4. **Tool Extraction**: Parses tool names, descriptions, and input schemas
5. **Tool Formatting**: Formats tools for LLM code generation prompt

### Supported Patterns

- **Python (FastMCP)**: `@server.tool()` decorators
- **TypeScript/JavaScript**: `tools: [...]` arrays in MCP SDK
- **Tool Definitions**: Extracts name, description, and input schema

### Example

For a task mentioning "Wikipedia", the agent:
1. Identifies `wikipedia-mcp` server directory
2. Scans `wikipedia_mcp/server.py`
3. Discovers tools: `search_wikipedia`, `get_article`, `get_summary`, etc.
4. Generates code using these discovered tools

## Code Execution Features

### Multi-Turn Execution

- Up to 7 turns of code generation and execution
- Each turn can fix errors from previous attempts
- Progressive refinement of solution

### Error Handling

- Syntax error detection and correction
- Runtime error recovery
- Tool call error handling
- Automatic retry with improved code

### Code Quality

- Automatic search fallback injection
- Result extraction helpers
- Type checking and validation
- Comprehensive error messages

### Reasoning

- LLM-generated reasoning for each code generation
- Final answer synthesis from execution results
- Multi-step problem decomposition

## Results and Output

### Output Files

Results are saved in the `results/` directory (or specified `--output-dir`):

- **CSV File**: `global_evaluation_YYYYMMDD_HHMMSS.csv` - Tabular results
- **JSON File**: `global_evaluation_YYYYMMDD_HHMMSS.json` - Detailed results

### CSV Columns

- `task_id`, `server_name`, `model_name`
- `agent_type` (traditional/code_execution)
- `status`, `execution_time`, `token_usage`
- `judge_score`, `completion_rate`
- `turns`, `tool_calls`
- `solution` (truncated)

### JSON Structure

```json
{
  "timestamp": "2025-01-XX...",
  "statistics": {
    "total_tasks": 100,
    "completed_combinations": 95,
    "failed_combinations": 5
  },
  "results": [
    {
      "task_id": "...",
      "server_name": "Wikipedia",
      "model_name": "gpt-4.1-mini",
      "agent_type": "code_execution",
      "execution_time": 12.5,
      "token_usage": 5000,
      "judge_score": 0.85,
      "turns": 2,
      "solution": "..."
    }
  ]
}
```

## Troubleshooting

### Common Issues

**1. "MCP servers directory not found"**
- Ensure you're running from `mcp-bench` directory
- Check that `mcp_servers/` directory exists

**2. "OPENAI_API_KEY not set"**
- Set environment variable: `export OPENAI_API_KEY="your-key"`
- Or create `.env` file in `mcp-bench/` directory

**3. "Server connection failed"**
- Run `python utils/collect_mcp_info.py` to verify servers
- Check that `mcp_servers/install.sh` completed successfully
- Verify API keys in `mcp_servers/api_key`

**4. "Import errors"**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**5. "Tool discovery failed"**
- Check that server source files exist in `mcp_servers/`
- Verify server directory structure matches expected patterns
- Check logs for specific parsing errors

### Windows-Specific

**Install Script Issues:**
- Use WSL: `wsl` then `bash install.sh`
- Or use Git Bash
- Or install servers individually: `cd mcp_servers/wikipedia-mcp && uv sync`

**Path Issues:**
- Use forward slashes in paths
- Run from `mcp-bench` directory
- Use absolute paths if needed

## Advanced Usage

### Custom Model Configuration

Edit `llm/factory.py` to add custom models:

```python
configs["your-model"] = ModelConfig(
    name="your-model",
    provider_type="openrouter",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model_name="provider/model-id"
)
```

### Task Generation

Generate custom benchmark tasks:

```bash
cd synthesis
python generate_benchmark_tasks.py \
  --mode single \
  --tasks-per-combination 5 \
  --output ../tasks/my_tasks.json
```

### Filtering Tasks

```bash
# Run only Wikipedia tasks
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_multi_2server_runner_format.json \
  --servers Wikipedia

# Run only specific models
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
  --models gpt-4o gpt-4.1-mini

# Limit number of tasks
python global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
  --task-limit 10
```


## Acknowledgments

- Built on the [Model Context Protocol](https://github.com/anthropics/mcp) by Anthropic
- The CE-MCP built on the [Code Execution MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) by Antropic
- Original MCP-Bench by Accenture Research
- Code Execution Agent implementation extends the original framework

## License

Apache 2.0 License - See LICENSE file for details
