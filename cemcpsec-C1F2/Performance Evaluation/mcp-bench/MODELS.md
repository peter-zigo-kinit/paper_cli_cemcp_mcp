# Model Configuration Guide

## Where Models Are Defined

Models are defined in **`mcp-bench/llm/factory.py`** in the `LLMFactory.get_model_configs()` method. The global runner automatically detects and uses all available models based on your environment variables.

## How Models Are Loaded

The global runner calls `LLMFactory.get_model_configs()` which scans your environment variables and creates model configurations for:

1. **OpenAI Models** (if `OPENAI_API_KEY` is set):
   - `gpt-4.1`
   - `gpt-4.1-mini`
   - `gpt-5-nano`

2. **Azure OpenAI Models** (if `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are set):
   - `o4-mini`
   - `gpt-4o`
   - `gpt-4o-mini`
   - `o3`
   - `gpt-5`

3. **OpenRouter Models** (if `OPENROUTER_API_KEY` is set):
   - `qwen-3-32b`
   - `qwen3-30b-a3b-instruct-2507`
   - `qwen3-235b-a22b-thinking-2507`
   - `qwen3-235b-a22b-2507`
   - `gpt-oss-20b`
   - `gpt-oss-120b`
   - `kimi-k2`
   - `minimax-m1`
   - `nova-micro-v1`
   - `grok-3-mini`
   - `gemini-2.5-flash-lite`
   - `gpt-5-mini-openrouter`
   - `gpt-5-nano`
   - `deepseek-r1-0528`
   - `deepseek-r1-0528-qwen3-8b`
   - `ernie-4.5-21b-a3b`
   - `glm-4.5-air`
   - `mistral-small-3.2-24b-instruct`
   - `gemma-3-27b-it`
   - `qwq-32b`
   - `glm-4.5`
   - `claude-sonnet-4`
   - `gemini-2.5-pro`

4. **Llama Models** (if corresponding environment variables are set):
   - `llama-4-maverick` (requires `LLAMA_4_MAVERICK_API_KEY`, `LLAMA_4_MAVERICK_BASE_URL`, `LLAMA_4_MAVERICK_MODEL`)
   - `llama-3-2-90b` (requires `LLAMA_3_2_90B_API_KEY`, etc.)
   - `llama-3-3-70b`
   - `llama-3-1-70b-instruct`
   - `llama-3-1-70b-dev`
   - `llama-3-1-8b`

## Which Models Are Used

The global runner uses **ALL available models** that are detected based on your environment variables. For example:

- If you only have `OPENAI_API_KEY` set, it will use: `gpt-4.1`, `gpt-4.1-mini`, `gpt-5-nano`
- If you have both `OPENAI_API_KEY` and `AZURE_OPENAI_API_KEY` set, it will use all OpenAI + Azure models
- If you have `OPENROUTER_API_KEY` set, it will use all OpenRouter models

## How to Check Available Models

You can check which models are available by running:

```python
from llm.factory import LLMFactory
models = LLMFactory.get_model_configs()
print(f"Available models: {list(models.keys())}")
```

Or run the global runner with verbose logging to see which models it detects:

```bash
python global_runner.py --tasks-file tasks/tasks.json --verbose
```

## How to Add New Models

To add a new model, edit `mcp-bench/llm/factory.py` and add it to the appropriate section:

### For OpenRouter Models:

```python
if os.getenv("OPENROUTER_API_KEY"):
    configs["your-model-name"] = ModelConfig(
        name="your-model-name",
        provider_type="openrouter",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model_name="provider/model-id"  # The exact model ID from OpenRouter
    )
```

### For OpenAI Models:

```python
if os.getenv("OPENAI_API_KEY"):
    configs["your-model-name"] = ModelConfig(
        name="your-model-name",
        provider_type="openai_compatible",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.openai.com/v1",
        model_name="your-model-name"
    )
```

### For Azure Models:

```python
if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
    configs["your-model-name"] = ModelConfig(
        name="your-model-name",
        provider_type="azure",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name="your-deployment-name"
    )
```

## Environment Variables Required

Set these in your `.env` file or environment:

- **OpenAI**: `OPENAI_API_KEY`
- **Azure**: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`
- **OpenRouter**: `OPENROUTER_API_KEY`
- **Llama**: `LLAMA_*_API_KEY`, `LLAMA_*_BASE_URL`, `LLAMA_*_MODEL` (for each model)

## Model Usage in Global Runner

The global runner will:
1. Call `get_available_models()` which uses `LLMFactory.get_model_configs()`
2. Run each task with each available model
3. Test both agents (Traditional MCP and Code Execution) with each model
4. Log results with model name included

Example: If you have 3 models and 5 tasks, it will run:
- 5 tasks × 3 models × 2 agents = **30 total combinations**

