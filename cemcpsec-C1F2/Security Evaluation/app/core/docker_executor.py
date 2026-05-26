"""
Persistent Docker executor - keeps container alive and sends code via stdin.
"""
import os
import asyncio
import json
from typing import Dict, Any, Optional
import time
from app.app_logging.logger import setup_logger
from app.config import DOCKER_IMAGE_NAME, DOCKER_MCP_GATEWAY, CODE_EXECUTION_TIMEOUT

logger = setup_logger(__name__)

class DockerCodeExecutor:
    """Executes code in persistent Docker containers via stdin/stdout"""
    
    def __init__(
        self,
        image: str = DOCKER_IMAGE_NAME,
        gateway_url: str = DOCKER_MCP_GATEWAY,
        timeout_s: int = CODE_EXECUTION_TIMEOUT
        
    ):
        self.image = image
        self.gateway_url = gateway_url
        self.timeout_s = timeout_s
    
        
        # Container state
        self.process: Optional[asyncio.subprocess.Process] = None
        self.last_used = 0
        self.is_ready = False
    async def start_container_dev(self):
        """Start persistent container for development"""
        logger.info(f"Starting persistent container for development: {self.image}")
        if self.process is not None:
            logger.info("Container already running")
            return  # Already running
        
        cmd = [
            "docker", "run",
            "-it",  # Interactive (stdin open)
            "--rm",  # Still cleanup on stop
            "-e", f"MCP_GATEWAY={self.gateway_url}",
            self.image,
            "bash"
        ]
        
        logger.info(f"Docker command: {' '.join(cmd)}")
        self.process = await asyncio.create_subprocess_exec(
            *cmd)
        logger.info(f"Process created, PID: {self.process.pid}")
        return self.process

    async def start_container(self):
        """Start persistent container"""

        if os.environ.get("DEV_MODE") == "True":
            return await self.start_container_dev()

        logger.info(f"Starting persistent container: {self.image}")
        if self.process is not None:
            logger.info("Container already running")
            return  # Already running
        
        cmd = [
            "docker", "run",
            "-i",  # Interactive (stdin open)
            "--rm",  # Still cleanup on stop
            "-e", f"MCP_GATEWAY={self.gateway_url}",
            self.image,
            "python", "-u", "/opt/execution_server.py"
        ]
        
        logger.info(f"Docker command: {' '.join(cmd)}")
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            logger.info(f"Process created, PID: {self.process.pid}")
            
            # Wait for READY signal from stderr (not stdout!)
            logger.info("Waiting for READY signal from container...")
            ready_line = await asyncio.wait_for(
                self.process.stderr.readline(),  
                timeout=20
            )
            
            logger.info(f"Received from stderr: {ready_line}")
            
            if b"READY" not in ready_line: # in case of mounting error (b"READY" won't received)
                # Read more stderr for debugging
                stderr_data = ready_line.decode('utf-8', errors='replace')
                try:
                    more_stderr = await asyncio.wait_for( 
                        self.process.stderr.read(1024),
                        timeout=2
                    )
                    stderr_data += more_stderr.decode('utf-8', errors='replace')
                except:
                    pass
                
                raise RuntimeError(f"Container failed to start. stderr: {stderr_data}")
            
            self.is_ready = True
            self.last_used = time.time()
            logger.info(f"Persistent container started successfully: {self.image}")
            
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for READY signal from container")
            # Try to get stderr output
            if self.process:
                try:
                    stderr_output = await asyncio.wait_for(
                        self.process.stderr.read(1024),
                        timeout=1
                    )
                    logger.error(f"Container stderr: {stderr_output.decode('utf-8', errors='replace')}")
                except:
                    pass
                self.process.kill()
                await self.process.wait()
                self.process = None
            raise RuntimeError("Container startup timeout - no READY signal received")
            
        except Exception as e:
            logger.error(f"Failed to start container: {type(e).__name__}: {str(e)}")
            if self.process:
                self.process.kill()
                await self.process.wait()
                self.process = None
            raise

    async def stop_container(self):
        """Stop the container"""
        if self.process is None:
            return
        
        try:
            self.process.stdin.close()
            await asyncio.wait_for(self.process.wait(), timeout=5)
        except:
            self.process.kill()
            await self.process.wait()
        
        self.process = None
        self.is_ready = False
        logger.info(f"Persistent container stopped: {self.image}")
    
    async def execute_async(self, code: str) -> Dict[str, Any]:
        """Execute code in persistent container
        Args:
            code: str - The code to execute
        Returns:
            Dict[str, Any] - The result of the execution { success: bool, output: str, error: str, return_code: int }
        """
        logger.info("=" * 80)
        logger.info("PERSISTENT DOCKER EXECUTOR - execute_async called")
        logger.info(f"Code length: {len(code)} bytes")
        
        # Ensure container is running
        if not self.is_ready or self.process is None:
            logger.info("Container not ready, starting...")
            await self.start_container()
        
        # Check if container died or transport closed
        if self.process.returncode is not None or self.process.stdin.is_closing():
            logger.warning(f"Container died (returncode={self.process.returncode}, stdin_closing={self.process.stdin.is_closing()}), restarting...")
            self.is_ready = False
            self.process = None
            await self.start_container()
        
        try:
            # Send code with length prefix
            code_bytes = code.encode('utf-8')
            length_bytes = len(code_bytes).to_bytes(4, 'big') # int converted to exact 4 bytes
            
            logger.info(f"Sending {len(code_bytes)} bytes of code to container")
            
            try:
                self.process.stdin.write(length_bytes)
                self.process.stdin.write(code_bytes)
                await self.process.stdin.drain()
            except (RuntimeError, OSError, BrokenPipeError) as transport_error:
                # Transport is closed, restart container and retry
                logger.warning(f"Transport error: {transport_error}, restarting container...")
                self.is_ready = False
                self.process = None
                await self.start_container()
                
                # Retry sending code
                self.process.stdin.write(length_bytes)
                self.process.stdin.write(code_bytes)
                await self.process.stdin.drain()
            
            logger.info("Code sent, waiting for response...")
            
            # Read result with timeout
            async def read_result():
                # Read length
                logger.info("Reading response length...")
                length_bytes = await self.process.stdout.readexactly(4)
                length = int.from_bytes(length_bytes, 'big')
                logger.info(f"Response length: {length} bytes")
                
                # Read result JSON
                result_bytes = await self.process.stdout.readexactly(length)
                result = json.loads(result_bytes.decode('utf-8'))
                logger.info(f"Received result: success={result.get('success')}, output_len={len(result.get('output', ''))}")
                return result
            
            result = await asyncio.wait_for(read_result(), timeout=self.timeout_s)
            self.last_used = time.time()
            logger.info("Code execution completed successfully")
            logger.info("=" * 80)
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout after {self.timeout_s}s waiting for container response")
            # Kill and restart container on timeout
            await self.stop_container()
            return {
                "success": False,
                "output": "",
                "error": f"Timeout after {self.timeout_s}s",
                "return_code": -1
            }
        
        except Exception as e:
            logger.error(f"Container execution error: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            # Restart container on error
            await self.stop_container()
            return {
                "success": False,
                "output": "",
                "error": f"Container error: {str(e)}",
                "return_code": -1
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_container()

docker_executor_instance = None

def get_docker_executor(image: str = DOCKER_IMAGE_NAME, gateway_url: str = DOCKER_MCP_GATEWAY, timeout_s: int = 30):
    global docker_executor_instance
    if docker_executor_instance is None:
        docker_executor_instance = DockerCodeExecutor(image = image, gateway_url=gateway_url, timeout_s=timeout_s)
    return docker_executor_instance