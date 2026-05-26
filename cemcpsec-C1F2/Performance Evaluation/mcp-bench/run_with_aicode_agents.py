#!/usr/bin/env python3
"""
Entry point script for running mcp-bench tasks with AI_Code_Execution_with_MCP agents.

This script provides a command-line interface to execute mcp-bench tasks using
the Traditional MCP and Code Execution MCP agents from AI_Code_Execution_with_MCP.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bridge.runner import BridgeRunner
import config.config_loader as config_loader

# Configure logging to console (not just file)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to terminal
    ]
)
logger = logging.getLogger(__name__)

# Suppress noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run mcp-bench tasks with AI_Code_Execution_with_MCP agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --agent traditional                    # Run with Traditional MCP agent
  %(prog)s --agent code_execution                # Run with Code Execution MCP agent
  %(prog)s --agent both                          # Run with both agents
  %(prog)s --tasks-file tasks/tasks.json         # Use specific task file
  %(prog)s --agent traditional --task-limit 5   # Run first 5 tasks
        '''
    )
    
    parser.add_argument(
        '--agent',
        choices=['traditional', 'code_execution', 'both'],
        default='traditional',
        help='Which agent to use (default: traditional)'
    )
    
    parser.add_argument(
        '--tasks-file',
        metavar='FILE',
        default=None,
        help='Path to tasks JSON file (default: use config default)'
    )
    
    parser.add_argument(
        '--task-limit',
        type=int,
        default=None,
        help='Limit number of tasks to run (default: all)'
    )
    
    parser.add_argument(
        '--use-fuzzy',
        action='store_true',
        default=config_loader.use_fuzzy_descriptions(),
        help='Use fuzzy task descriptions (default: from config)'
    )
    
    parser.add_argument(
        '--disable-fuzzy',
        action='store_true',
        help='Use detailed task descriptions instead of fuzzy'
    )
    
    parser.add_argument(
        '--enable-judge-stability',
        action='store_true',
        default=config_loader.is_judge_stability_enabled(),
        help='Enable LLM Judge stability testing (default: from config)'
    )
    
    parser.add_argument(
        '--disable-judge-stability',
        action='store_true',
        help='Disable LLM Judge stability testing'
    )
    
    parser.add_argument(
        '--output',
        metavar='FILE',
        help='Output file for results (default: auto-generated timestamp name)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--servers',
        nargs='+',
        metavar='SERVER',
        help='Filter tasks by server name(s). Example: --servers Wikipedia "National Parks"'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine fuzzy description setting
    use_fuzzy = args.use_fuzzy
    if args.disable_fuzzy:
        use_fuzzy = False
    
    # Determine judge stability setting
    enable_judge_stability = args.enable_judge_stability
    if args.disable_judge_stability:
        enable_judge_stability = False
    
    # Print configuration
    print("=" * 80)
    print("AI_Code_Execution_with_MCP Bridge Runner")
    print("=" * 80)
    print(f"Agent type: {args.agent}")
    print(f"Tasks file: {args.tasks_file or config_loader.get_tasks_file()}")
    print(f"Task limit: {args.task_limit or 'all'}")
    print(f"Servers filter: {args.servers or 'all servers'}")
    print(f"Use fuzzy descriptions: {use_fuzzy}")
    print(f"Judge stability: {enable_judge_stability}")
    print("=" * 80)
    print()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY environment variable not set!")
        print("   Set it in your .env file or export it:")
        print("   export OPENAI_API_KEY=your_key_here")
        print("   Or create .env file in AI_Code_Execution_with_MCP directory")
        print()
    
    try:
        # Create runner
        runner = BridgeRunner(
            tasks_file=args.tasks_file,
            agent_type=args.agent,
            use_fuzzy_descriptions=use_fuzzy,
            enable_judge_stability=enable_judge_stability,
            server_filter=args.servers
        )
        
        # Run benchmark
        logger.info("Starting benchmark execution...")
        results = await runner.run_benchmark(task_limit=args.task_limit)
        
        # Save results
        if results:
            output_file = args.output
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                agent_suffix = args.agent.replace('_', '-')
                output_file = f'aicode_bridge_results_{agent_suffix}_{timestamp}.json'
            
            # Save aggregated metrics
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {output_file}")
            
            # Also save detailed results
            detailed_output = output_file.replace('.json', '_detailed.json')
            with open(detailed_output, 'w', encoding='utf-8') as f:
                json.dump(runner.results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Detailed results saved to {detailed_output}")
        else:
            logger.warning("No results to save")
    
    except Exception as e:
        logger.error(f"Error running benchmark: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

