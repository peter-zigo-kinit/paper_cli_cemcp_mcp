"""
Persistent execution server for Docker containers.
Reads code from stdin, executes it, returns results to stdout.
"""
import sys
import json
import asyncio
import io
import contextlib
import traceback
import inspect
import os

async def execute_code(code: str) -> dict:
    """Execute code and return results"""
    stdout_capture = io.StringIO() # in-memory temporary buffer to capture stdout (acts like a file to write into)
    stderr_capture = io.StringIO() 
    
    try:
        # Setup execution namespace with __name__ set to '__main__'
        # so that "if __name__ == '__main__'" blocks execute
        exec_namespace = {
            '__builtins__': __builtins__,
            '__name__': '__main__',
            'asyncio': asyncio,
        }
        # redirect stdout and stderr to the in-memory temporary buffers. (print function is to buffer captured stdout and stderr)
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stderr_capture):
            exec(code, exec_namespace, exec_namespace)
            
            # Also handle async main functions if they weren't auto-called
            if 'main' in exec_namespace and \
               inspect.iscoroutinefunction(exec_namespace['main']) and \
               '__main__' not in code:  # Only if not already called
                await exec_namespace['main']()
        
        # Get captured output and errors
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        # If there's stderr output but no stdout, include stderr in output for debugging
        if stderr_output and not stdout_output:
            stdout_output = f"[stderr]\n{stderr_output}"
        
        return {
            "success": True,
            "output": stdout_output,
            "error": stderr_output if stderr_output else None,
            "return_code": 0
        }
    
    except Exception as e:
        return {
            "success": False,
            "output": stdout_capture.getvalue(),
            "error": f"{traceback.format_exc()}\n{stderr_capture.getvalue()}",
            "return_code": -1
        }

async def main_loop():
    """Main server loop - reads from stdin, executes, writes to stdout"""
    # Send READY to stderr, keep stdout clean for binary data
    print("READY", file=sys.stderr, flush=True)  # ← CHANGED: Use stderr
    
    while True:
        try:
            # Read length prefix (4 bytes)
            length_bytes = sys.stdin.buffer.read(4) # read exact 4 bytes
            if not length_bytes: # there is nothing to execute keep trying.
                break 
            
            # Read code payload
            length = int.from_bytes(length_bytes, 'big') # bytes converted to int
            code = sys.stdin.buffer.read(length).decode('utf-8')
            
            # Execute code
            result = await execute_code(code)
            
            # Write result as JSON with length prefix
            result_json = json.dumps(result).encode('utf-8')
            sys.stdout.buffer.write(len(result_json).to_bytes(4, 'big'))
            sys.stdout.buffer.write(result_json)
            sys.stdout.buffer.flush()
            
        except Exception as e:
            # Write error result
            error_result = {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1
            }
            result_json = json.dumps(error_result).encode('utf-8')
            sys.stdout.buffer.write(len(result_json).to_bytes(4, 'big'))
            sys.stdout.buffer.write(result_json)
            sys.stdout.buffer.flush()

if __name__ == "__main__":
    asyncio.run(main_loop())