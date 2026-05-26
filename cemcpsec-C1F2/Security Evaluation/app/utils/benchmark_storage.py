"""
Benchmark result storage and formatting utilities.

This module handles saving, loading, and formatting benchmark results.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from app.api.models import BenchmarkHistoryItem
from app.app_logging.logger import setup_logger


class BenchmarkStorage:
    """
    Handles benchmark result storage and formatting operations.
    
    This class provides methods to save, load, and format benchmark results.
    """
    
    def __init__(self):
        """Initialize the benchmark storage handler."""
        self.logger = setup_logger(__name__)
    
    def save_result(self, file_path: Path, query: str, result: Dict[str, Any]) -> None:
        """
        Save benchmark result to JSON file.
        
        This function:
        1. Loads existing results if file exists
        2. Appends new result with timestamp
        3. Saves back to file
        
        Args:
            file_path: Path to the JSON file
            query: Query that was executed
            result: Benchmark result dictionary
        """
        try:
            # Initialize empty results list
            existing_results = []
            
            # Load existing results if file exists
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        # Parse JSON data
                        data = json.load(f)
                        
                        # Convert data to list format
                        if isinstance(data, list):
                            existing_results = data
                        elif isinstance(data, dict):
                            existing_results = [data]
                            
                    except json.JSONDecodeError:
                        # Handle corrupted JSON file
                        self.logger.warning(f"Invalid JSON in {file_path}, starting fresh")
                        existing_results = []
            
            # Create new entry with timestamp
            new_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "result": result
            }
            
            # Append new entry to existing results
            existing_results.append(new_entry)
            
            # Write updated results back to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_results, f, indent=2)
            
            # Log successful save operation
            self.logger.info(f"Saved benchmark result to {file_path}")
            
        except Exception as e:
            # Log error and re-raise exception
            self.logger.error(f"Error saving benchmark result: {str(e)}")
            raise
    
    def load_results(self, file_path: Path) -> List[BenchmarkHistoryItem]:
        """
        Load benchmark results from JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of BenchmarkHistoryItem objects
        """
        # Return empty list if file doesn't exist
        if not file_path.exists():
            self.logger.info(f"Results file not found: {file_path}")
            return []
        
        try:
            # Read JSON file
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convert data to list format
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                results = [data]
            else:
                results = []
            
            # Convert to Pydantic models and return
            return [BenchmarkHistoryItem(**item) for item in results]
            
        except Exception as e:
            # Log error and return empty list
            self.logger.error(f"Error loading benchmark results from {file_path}: {str(e)}")
            return []
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw benchmark result into standardized structure.
        
        Args:
            result: Raw benchmark result dictionary
            
        Returns:
            Formatted result dictionary matching BenchmarkResult model
        """
        # Extract LLM calls and token data
        llm_calls = result.get("llm_calls", [])
        tokens = result.get("tokens", {})
        
        # Convert token format if needed (handle both formats)
        if isinstance(tokens, dict) and "prompt_tokens" not in tokens:
            tokens = {
                "prompt_tokens": tokens.get("input", 0),
                "completion_tokens": tokens.get("output", 0),
                "total_tokens": tokens.get("total", 0)
            }
        
        # Return formatted result dictionary
        return {
            "success": result.get("success", False),
            "final_output": result.get("output", result.get("final_output", "")),
            "error": result.get("error"),
            "time": round(result.get("time", 0), 2),
            "llm_calls": llm_calls,
            "total_tokens": tokens
        }

