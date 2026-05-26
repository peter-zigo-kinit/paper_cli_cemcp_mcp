"""
Task Adapter for converting mcp-bench task format to agent input format.

This module handles the conversion between mcp-bench's task structure
and the simple query string format expected by AI_Code_Execution_with_MCP agents.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskAdapter:
    """Adapter for converting mcp-bench tasks to agent input format."""
    
    def __init__(self, use_fuzzy_descriptions: bool = False):
        """
        Initialize the task adapter.
        
        Args:
            use_fuzzy_descriptions: If True, use fuzzy_description instead of task_description
        """
        self.use_fuzzy_descriptions = use_fuzzy_descriptions
    
    def extract_task_query(self, task_info: Dict[str, Any]) -> str:
        """
        Extract task query from mcp-bench task format.
        
        Args:
            task_info: Task dictionary from mcp-bench format with structure:
                {
                    'server_name': str,
                    'task': {
                        'task_id': str,
                        'task_description': str,
                        'fuzzy_description': str (optional),
                        ...
                    }
                }
        
        Returns:
            Task query string to pass to agent
        """
        task_data = task_info.get('task', {})
        
        if self.use_fuzzy_descriptions:
            task_query = task_data.get('fuzzy_description', task_data.get('task_description', ''))
        else:
            task_query = task_data.get('task_description', '')
        
        if not task_query:
            logger.warning(f"No task description found for task {task_data.get('task_id', 'unknown')}")
            return ""
        
        return task_query
    
    def get_task_metadata(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from task info.
        
        Args:
            task_info: Task dictionary from mcp-bench format
        
        Returns:
            Dictionary with task metadata:
                - task_id: Task identifier
                - server_name: Server name(s) required for task
                - concrete_task_description: Original detailed description (if using fuzzy)
        """
        task_data = task_info.get('task', {})
        server_name = task_info.get('server_name', '')
        
        metadata = {
            'task_id': task_data.get('task_id', 'unknown'),
            'server_name': server_name,
        }
        
        # Include concrete description if using fuzzy descriptions
        if self.use_fuzzy_descriptions:
            metadata['concrete_task_description'] = task_data.get('task_description', '')
        
        return metadata

