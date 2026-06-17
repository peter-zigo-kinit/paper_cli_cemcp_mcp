"""Helpers for mapping Code Execution agent traces to MCP-Bench evaluation format."""

from collections import defaultdict
from typing import Any, Dict, List, Optional


def tool_calls_to_execution_results(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert CE agent ``tool_calls`` to ``TaskEvaluator`` execution_results format.

    The Code Execution executor records each MCP invocation in ``tool_calls``.
    Rule-based metrics (valid tool name, schema compliance, execution success)
    require that shape—not synthetic ``code_execution`` stubs.
    """
    execution_results: List[Dict[str, Any]] = []
    for call in tool_calls or []:
        tool_name = call.get('tool')
        if not tool_name:
            continue
        entry: Dict[str, Any] = {
            'tool': tool_name,
            'server': call.get('server', ''),
            'parameters': call.get('parameters') or {},
            'round_num': call.get('turn', call.get('round_num', 0)),
            'success': bool(call.get('success', False)),
        }
        if call.get('error'):
            entry['error'] = call['error']
        execution_results.append(entry)
    return execution_results


def extract_task_eval_context(
    task_info: Dict[str, Any],
    *,
    use_fuzzy_descriptions: bool,
    enable_concrete_description_ref: bool,
) -> Dict[str, Any]:
    """Extract task description and judge-only reference fields from a task record."""
    task_data = task_info.get('task', {})
    if isinstance(task_data, str):
        return {
            'task_id': task_info.get('task_id', 'unknown'),
            'task_description': task_data,
            'concrete_task_description': None,
            'dependency_analysis': '',
        }

    if use_fuzzy_descriptions:
        task_description = task_data.get('fuzzy_description', task_data.get('task_description', ''))
    else:
        task_description = task_data.get('task_description', '')

    concrete_task_description = None
    if enable_concrete_description_ref and use_fuzzy_descriptions:
        concrete_task_description = task_data.get('task_description', '')

    return {
        'task_id': task_data.get('task_id', task_info.get('task_id', 'unknown')),
        'task_description': task_description,
        'concrete_task_description': concrete_task_description,
        'dependency_analysis': task_data.get('dependency_analysis', ''),
    }


def build_code_execution_accumulated_information(code_exec_result: Dict[str, Any]) -> str:
    """Build chronological CE execution digest for the LLM judge."""
    parts = [
        'Code Execution MCP Summary',
        f"Total turns: {code_exec_result.get('total_turns', 0)}",
        f"Total MCP tool calls: {len(code_exec_result.get('tool_calls', []))}",
        '',
    ]

    tool_calls_by_turn: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for call in code_exec_result.get('tool_calls', []):
        tool_calls_by_turn[call.get('turn', 0)].append(call)

    for code_exec in code_exec_result.get('code_executions', []):
        turn = code_exec.get('turn', '?')
        parts.append(f'--- Turn {turn} ---')

        code = code_exec.get('code', '')
        if code:
            parts.append(f'Generated Code:\n{code}')

        reasoning = code_exec.get('reasoning', '')
        if reasoning:
            parts.append(f'Reasoning: {reasoning}')

        exec_info = code_exec.get('execution', {})
        output = exec_info.get('output', '')
        if output:
            parts.append(f'Execution Output:\n{output}')
        if exec_info.get('final_answer'):
            parts.append(f"Final Answer:\n{exec_info.get('final_answer')}")
        if exec_info.get('error'):
            parts.append(f"Error: {exec_info.get('error')}")

        turn_calls = tool_calls_by_turn.get(code_exec.get('turn', 0), [])
        if turn_calls:
            parts.append('MCP Tool Calls:')
            for tool_call in turn_calls:
                status = 'success' if tool_call.get('success') else f"FAILED ({tool_call.get('error', 'unknown')})"
                parts.append(f"  - {tool_call.get('tool')}: {status}")
                parameters = tool_call.get('parameters')
                if parameters:
                    parts.append(f'    parameters: {parameters}')
        parts.append('')

    solution = code_exec_result.get('solution', '')
    if solution:
        parts.append('--- Final Solution ---')
        parts.append(solution)

    return '\n'.join(parts)


def compute_overall_score(evaluation: Dict[str, Any]) -> Optional[float]:
    """Paper Table 3 Overall Score: mean of four 0-1 dimensions."""
    schema_metrics = [
        evaluation.get('valid_tool_name_rate'),
        evaluation.get('input_schema_compliance'),
    ]
    schema_values = [value for value in schema_metrics if value is not None]
    if not schema_values:
        return None

    schema_understanding = sum(schema_values) / len(schema_values)
    judge_axes = [
        evaluation.get('task_completion_score'),
        evaluation.get('tool_selection_score'),
        evaluation.get('planning_effectiveness_and_efficiency_score'),
    ]
    if any(axis is None for axis in judge_axes):
        return None

    normalized_judge_axes = [axis / 10.0 for axis in judge_axes]
    return (schema_understanding + sum(normalized_judge_axes)) / 4
