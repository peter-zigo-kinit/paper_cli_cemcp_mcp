#!/usr/bin/env python3
"""
CSV Tracker for MCP-Bench Task Results

This module handles incremental CSV tracking of task execution results.
Saves after each task to ensure data persistence even if the process fails.
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import csv

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

logger = logging.getLogger(__name__)

if not PANDAS_AVAILABLE:
    logger.warning("pandas not available, using CSV module for tracking")


class CSVTracker:
    """Tracks task execution results in a CSV file with incremental saves."""
    
    def __init__(self, output_dir: str = "./results", filename: Optional[str] = None):
        """
        Initialize CSV tracker.
        
        Args:
            output_dir: Directory to save CSV files
            filename: Optional custom filename (default: auto-generated with timestamp)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"task_results_{timestamp}.csv"
        
        self.csv_path = self.output_dir / filename
        
        # JSON file for storing full data (including query, code, tools_used)
        json_filename = filename.replace('.csv', '.json')
        self.json_path = self.output_dir / json_filename
        
        # Define CSV columns (excluding query, code, tools_used - these go in JSON)
        self.columns = [
            'task_id',
            'server',
            'model',
            'agent_type',  # 'MCP' or 'CE' (Code Execution)
            'agent_execution_time',  # seconds
            'input_tokens',
            'output_tokens',
            'total_tokens',
            'answer',
            'num_turns',  # Number of turns/rounds used
            # Performance metrics
            'task_completion_score',
            'tool_selection_score',
            'planning_effectiveness_score',
            'task_fulfillment',
            'grounding',
            'tool_appropriateness',
            'parameter_accuracy',
            'dependency_awareness',
            'parallelism_and_efficiency',
            'input_schema_compliance',
            'valid_tool_name_rate',
            'execution_success_rate',
            'avg_rounds_per_task',
            'avg_tool_calls_per_task'
        ]
        
        if PANDAS_AVAILABLE:
            self.df = pd.DataFrame(columns=self.columns)
        else:
            self.df = None
        
        # Initialize JSON data list
        self.json_data = []
        
        # Load existing JSON data if it exists
        if self.json_path.exists():
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
                if not isinstance(self.json_data, list):
                    logger.warning(f"JSON file exists but is not a list, starting fresh")
                    self.json_data = []
                logger.info(f"Loaded existing JSON data: {self.json_path} ({len(self.json_data)} entries)")
            except Exception as e:
                logger.warning(f"Could not load existing JSON file, starting fresh: {e}")
                self.json_data = []
        else:
            # Create empty JSON file
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.info(f"Created JSON data file: {self.json_path}")
        
        # Create CSV file with headers if it doesn't exist
        if not self.csv_path.exists():
            self._write_header()
            logger.info(f"Created CSV tracker: {self.csv_path}")
        else:
            if PANDAS_AVAILABLE:
                # Load existing CSV if it exists
                try:
                    # pandas read_csv handles multi-line fields within quoted strings correctly by default
                    # It will properly parse CSV files with newlines inside quoted fields
                    self.df = pd.read_csv(self.csv_path, quoting=csv.QUOTE_ALL)
                    logger.info(f"Loaded existing CSV tracker: {self.csv_path} ({len(self.df)} rows)")
                    # Ensure CSV and JSON have the same number of entries
                    if len(self.df) != len(self.json_data):
                        logger.warning(f"CSV has {len(self.df)} rows but JSON has {len(self.json_data)} entries - they should match")
                except Exception as e:
                    logger.warning(f"Could not load existing CSV, starting fresh: {e}")
                    self.df = pd.DataFrame(columns=self.columns)
                    self._write_header()
            else:
                logger.info(f"Using existing CSV tracker: {self.csv_path}")
    
    def _write_header(self):
        """Write CSV header."""
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            # Use QUOTE_ALL to match the quoting style used for data rows
            writer = csv.writer(
                f,
                quoting=csv.QUOTE_ALL,
                doublequote=True,
                escapechar=None,
                lineterminator='\n'
            )
            writer.writerow(self.columns)
    
    def add_task_result(
        self,
        task_id: str,
        server: str,
        model: str,
        agent_type: str,  # 'MCP' or 'CE'
        agent_execution_time: float,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        query: str,
        answer: str,
        code: Optional[str] = None,
        num_turns: Optional[int] = None,
        tools_used: Optional[list] = None,  # List of tool call dicts
        evaluation: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a task result row and save to CSV immediately.
        
        Args:
            task_id: Task identifier
            server: Server name
            model: Model name
            agent_type: 'MCP' or 'CE'
            agent_execution_time: Execution time in seconds
            input_tokens: Input token count
            output_tokens: Output token count
            total_tokens: Total token count
            query: Task query/description
            answer: Final answer/solution
            code: Generated code (only for CE agent)
        """
        # Truncate long strings to avoid issues
        max_query_len = 10000
        max_answer_len = 50000
        max_code_len = 100000
        
        # Extract evaluation metrics if available
        eval = evaluation or {}
        
        # Helper function to build common fields (shared between CSV and JSON)
        def build_common_fields():
            return {
                'task_id': str(task_id),
                'server': str(server),
                'model': str(model),
                'agent_type': str(agent_type),
                'agent_execution_time': float(agent_execution_time),
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'total_tokens': int(total_tokens),
                'answer': str(answer)[:max_answer_len] if answer else '',
                'num_turns': int(num_turns) if num_turns is not None else 0,
                # Performance metrics (with defaults for None/missing values)
                'task_completion_score': float(eval.get('task_completion_score', 0)) if eval.get('task_completion_score') is not None else 0.0,
                'tool_selection_score': float(eval.get('tool_selection_score', 0)) if eval.get('tool_selection_score') is not None else 0.0,
                'planning_effectiveness_score': float(eval.get('planning_effectiveness_and_efficiency_score', 0)) if eval.get('planning_effectiveness_and_efficiency_score') is not None else 0.0,
                'task_fulfillment': float(eval.get('task_fulfillment', 0)) if eval.get('task_fulfillment') is not None else 0.0,
                'grounding': float(eval.get('grounding', 0)) if eval.get('grounding') is not None else 0.0,
                'tool_appropriateness': float(eval.get('tool_appropriateness', 0)) if eval.get('tool_appropriateness') is not None else 0.0,
                'parameter_accuracy': float(eval.get('parameter_accuracy', 0)) if eval.get('parameter_accuracy') is not None else 0.0,
                'dependency_awareness': float(eval.get('dependency_awareness', 0)) if eval.get('dependency_awareness') is not None else 0.0,
                'parallelism_and_efficiency': float(eval.get('parallelism_and_efficiency', 0)) if eval.get('parallelism_and_efficiency') is not None else 0.0,
                'input_schema_compliance': float(eval.get('input_schema_compliance', 0)) if eval.get('input_schema_compliance') is not None else 0.0,
                'valid_tool_name_rate': float(eval.get('valid_tool_name_rate', 0)) if eval.get('valid_tool_name_rate') is not None else 0.0,
                'execution_success_rate': float(eval.get('execution_success_rate', 0)) if eval.get('execution_success_rate') is not None else 0.0,
                'avg_rounds_per_task': float(eval.get('avg_rounds_per_task', 0)) if eval.get('avg_rounds_per_task') is not None else 0.0,
                'avg_tool_calls_per_task': float(eval.get('avg_tool_calls_per_task', 0)) if eval.get('avg_tool_calls_per_task') is not None else 0.0
            }
        
        # Build CSV row (without query, code, tools_used)
        csv_row = build_common_fields()
        
        # Build JSON row (with ALL fields including query, code, tools_used)
        json_row = build_common_fields()
        json_row.update({
            'query': str(query)[:max_query_len] if query else '',
            'code': str(code)[:max_code_len] if code else '',
            'tools_used': tools_used if tools_used is not None else []  # Keep as list, not JSON string
        })
        
        # Update DataFrame if pandas is available (using CSV row without query/code/tools_used)
        if PANDAS_AVAILABLE and self.df is not None:
            new_row_df = pd.DataFrame([csv_row])
            if len(self.df) == 0:
                # If dataframe is empty, just assign the new row directly
                self.df = new_row_df
            else:
                self.df = pd.concat([self.df, new_row_df], ignore_index=True)
        
        # Save to CSV immediately (append mode for efficiency)
        try:
            # Use csv.writer with proper settings
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(
                    f,
                    quoting=csv.QUOTE_ALL,  # Quote all fields
                    doublequote=True,  # Escape quotes by doubling them (RFC 4180 compliant)
                    escapechar=None,  # Use default (no escapechar when doublequote=True)
                    lineterminator='\n'  # Consistent line endings
                )
                # Convert all values to strings and handle None
                row_values = []
                for col in self.columns:
                    value = csv_row.get(col, '')
                    # Convert None to empty string
                    if value is None:
                        value = ''
                    # Convert all values to strings
                    elif isinstance(value, (int, float)):
                        value = str(value)
                    else:
                        value = str(value)
                    row_values.append(value)
                writer.writerow(row_values)
            logger.info(f"Saved task result to CSV: {task_id} ({server}, {model}, {agent_type})")
        except Exception as e:
            logger.error(f"Failed to save task result to CSV: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Save to JSON file (append the full row with query, code, tools_used)
        try:
            # Append to the JSON data list
            self.json_data.append(json_row)
            
            # Write the entire JSON file (this ensures consistency and order)
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved task result to JSON: {task_id} ({server}, {model}, {agent_type})")
        except Exception as e:
            logger.error(f"Failed to save task result to JSON: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_dataframe(self):
        """Get the current DataFrame (if pandas available) or None."""
        if PANDAS_AVAILABLE and self.df is not None:
            return self.df.copy()
        return None
    
    def get_csv_path(self) -> Path:
        """Get the CSV file path."""
        return self.csv_path
    
    def get_json_path(self) -> Path:
        """Get the JSON file path."""
        return self.json_path
    
    def get_json_data(self) -> list:
        """Get the current JSON data list (copy)."""
        return self.json_data.copy()

