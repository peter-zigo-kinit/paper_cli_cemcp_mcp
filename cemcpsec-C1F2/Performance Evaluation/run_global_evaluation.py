#!/usr/bin/env python3
"""
Wrapper script to run global_runner.py from MCP_Research directory.

This script allows you to run the global evaluation runner from the project root
while using the mcp-bench virtual environment.
"""

import sys
import os
from pathlib import Path

# Get the project root (MCP_Research)
project_root = Path(__file__).parent.resolve()
mcp_bench_dir = project_root / "mcp-bench"

# Check if mcp-bench exists
if not mcp_bench_dir.exists():
    print(f"Error: mcp-bench directory not found at {mcp_bench_dir}")
    sys.exit(1)

# Add mcp-bench to Python path
sys.path.insert(0, str(mcp_bench_dir))

# Change to mcp-bench directory for execution (so relative paths work)
original_cwd = os.getcwd()
try:
    os.chdir(str(mcp_bench_dir))
    
    # Import and run the global runner
    if __name__ == "__main__":
        import asyncio
        from global_runner import main
        
        try:
            exit_code = asyncio.run(main())
            sys.exit(exit_code)
        except KeyboardInterrupt:
            print("\n⚠️  Evaluation interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
finally:
    # Restore original working directory
    os.chdir(original_cwd)

