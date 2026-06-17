"""Tests for CE tool_calls → execution_results conversion used in rule-based evaluation."""

import sys
from pathlib import Path

MCP_BENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_BENCH_ROOT))

from benchmark.code_execution_results import (
    build_code_execution_accumulated_information,
    compute_overall_score,
    extract_task_eval_context,
    tool_calls_to_execution_results,
)
from benchmark.evaluator import TaskEvaluator


def test_tool_calls_map_to_valid_rule_based_metrics():
    tool_calls = [
        {
            'tool': 'Unit Converter:convert_batch',
            'server': 'Unit Converter',
            'parameters': {'requests': [{'value': 1, 'from_unit': 'm', 'to_unit': 'ft'}]},
            'turn': 1,
            'success': True,
        },
        {
            'tool': 'Unit Converter:convert_temperature',
            'server': 'Unit Converter',
            'parameters': {'value': 350, 'from_unit': 'fahrenheit', 'to_unit': 'celsius'},
            'turn': 1,
            'success': True,
        },
    ]
    available_tools = {
        'Unit Converter:convert_batch': {
            'server': 'Unit Converter',
            'input_schema': {
                'type': 'object',
                'properties': {'requests': {'type': 'array'}},
                'required': ['requests'],
            },
        },
        'Unit Converter:convert_temperature': {
            'server': 'Unit Converter',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'value': {'type': 'number'},
                    'from_unit': {'type': 'string'},
                    'to_unit': {'type': 'string'},
                },
                'required': ['value', 'from_unit', 'to_unit'],
            },
        },
    }

    execution_results = tool_calls_to_execution_results(tool_calls)
    metrics = TaskEvaluator(None)._calculate_tool_accuracy_metrics(
        execution_results, available_tools, planning_json_compliance=1.0
    )

    assert metrics['valid_tool_name_rate'] == 1.0
    assert metrics['input_schema_compliance'] == 1.0
    assert metrics['execution_success_rate'] == 1.0


def test_failed_tool_call_is_counted_in_execution_success_rate():
    tool_calls = [
        {
            'tool': 'Unit Converter:convert_batch',
            'server': 'Unit Converter',
            'parameters': {},
            'turn': 1,
            'success': False,
            'error': 'validation failed',
        },
    ]
    available_tools = {
        'Unit Converter:convert_batch': {'server': 'Unit Converter', 'input_schema': {}},
    }

    execution_results = tool_calls_to_execution_results(tool_calls)
    metrics = TaskEvaluator(None)._calculate_tool_accuracy_metrics(
        execution_results, available_tools, planning_json_compliance=1.0
    )

    assert metrics['valid_tool_name_rate'] == 1.0
    assert metrics['execution_success_rate'] == 0.0


def test_empty_tool_calls_yields_empty_execution_results():
    assert tool_calls_to_execution_results([]) == []
    assert tool_calls_to_execution_results(None) == []


def test_extract_task_eval_context_uses_fuzzy_and_judge_refs():
    task_info = {
        'server_name': 'Unit Converter',
        'task': {
            'task_id': 'unit_converter_000',
            'task_description': 'concrete task',
            'fuzzy_description': 'fuzzy task',
            'dependency_analysis': 'step 1 then step 2',
        },
    }

    context = extract_task_eval_context(
        task_info,
        use_fuzzy_descriptions=True,
        enable_concrete_description_ref=True,
    )

    assert context['task_id'] == 'unit_converter_000'
    assert context['task_description'] == 'fuzzy task'
    assert context['concrete_task_description'] == 'concrete task'
    assert context['dependency_analysis'] == 'step 1 then step 2'


def test_build_code_execution_accumulated_information_includes_tool_calls():
    code_exec_result = {
        'total_turns': 1,
        'solution': 'final answer',
        'tool_calls': [
            {
                'tool': 'Unit Converter:convert_batch',
                'turn': 1,
                'success': True,
                'parameters': {'requests': []},
            }
        ],
        'code_executions': [
            {
                'turn': 1,
                'code': 'await server_manager.call_tool(...)',
                'reasoning': 'convert readings',
                'execution': {'output': 'done', 'success': True},
            }
        ],
    }

    digest = build_code_execution_accumulated_information(code_exec_result)

    assert 'Code Execution MCP Summary' in digest
    assert 'Unit Converter:convert_batch' in digest
    assert 'Generated Code:' in digest
    assert 'final answer' in digest


def test_compute_overall_score_matches_paper_four_dimension_mean():
    evaluation = {
        'valid_tool_name_rate': 1.0,
        'input_schema_compliance': 0.993,
        'task_completion_score': 7.525,
        'tool_selection_score': 7.58,
        'planning_effectiveness_and_efficiency_score': 4.94,
    }

    overall = compute_overall_score(evaluation)

    assert overall is not None
    assert abs(overall - 0.75025) < 0.001
