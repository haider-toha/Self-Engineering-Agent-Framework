"""
Secure Execution Sandbox - Docker-based isolated environment for testing agent-generated code
"""

import os
import tempfile
import shutil
from typing import Dict, Any
import docker
from docker.errors import DockerException, ContainerError, ImageNotFound
from config import Config


class SecureSandbox:
    """
    Manages secure execution of untrusted code in isolated Docker containers.
    Each execution runs in a fresh container that is destroyed immediately after.
    """
    
    def __init__(self, image_name: str = None, timeout: int = None):
        """
        Initialize the secure sandbox
        
        Args:
            image_name: Docker image name to use
            timeout: Execution timeout in seconds
        """
        self.image_name = image_name or Config.DOCKER_IMAGE_NAME
        self.timeout = timeout or Config.DOCKER_TIMEOUT
        
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise Exception(f"Failed to connect to Docker. Is Docker running? Error: {str(e)}")
    
    def build_image(self) -> bool:
        """
        Build the sandbox Docker image from the dockerfile
        
        Returns:
            True if successful, False otherwise
        """
        try:
            dockerfile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker")
            
            print(f"Building Docker image '{self.image_name}' from {dockerfile_path}...")
            
            # Build the image
            image, build_logs = self.client.images.build(
                path=dockerfile_path,
                dockerfile="sandbox.dockerfile",
                tag=self.image_name,
                rm=True,
                forcerm=True
            )
            
            print(f"Docker image '{self.image_name}' built successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to build Docker image: {str(e)}")
            return False
    
    def ensure_image_exists(self) -> bool:
        """
        Check if the sandbox image exists, build it if not
        
        Returns:
            True if image exists or was built successfully
        """
        try:
            self.client.images.get(self.image_name)
            return True
        except ImageNotFound:
            print(f"Docker image '{self.image_name}' not found. Building it now...")
            return self.build_image()
    
    def verify_tool(self, function_name: str, function_code: str, test_code: str) -> Dict[str, Any]:
        """
        Verify a tool by running its tests in an isolated Docker container
        
        Args:
            function_name: The name of the function to test
            function_code: Python function implementation
            test_code: Pytest test code
            
        Returns:
            Dictionary with 'success' (bool) and 'output' (str) keys
        """
        # Ensure Docker image exists
        if not self.ensure_image_exists():
            return {
                "success": False,
                "output": f"Failed to ensure Docker image '{self.image_name}' exists"
            }
        
        # Create temporary directory for code files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Write code files to temp directory
            function_file = os.path.join(temp_dir, "tool_function.py")
            test_file = os.path.join(temp_dir, "test_tool.py")
            
            with open(function_file, 'w', encoding='utf-8') as f:
                f.write(function_code)
            
            # Modify test code to import from tool_function
            modified_test_lines = []
            for line in test_code.splitlines():
                # Comment out any lines that import from the original function name file
                if f"from {function_name}" in line and "import" in line:
                    modified_test_lines.append(f"# {line} # Patched by sandbox")
                else:
                    modified_test_lines.append(line)
            
            # Add proper import at the beginning
            import_statement = f"from tool_function import {function_name}\n"
            modified_test_code = import_statement + "\n".join(modified_test_lines)
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(modified_test_code)
            
            # Run container with mounted volume
            try:
                # Create and run container
                container = self.client.containers.run(
                    image=self.image_name,
                    command=["pytest", "-v", "/code/test_tool.py"],
                    volumes={temp_dir: {'bind': '/code', 'mode': 'ro'}},
                    detach=True,
                    remove=False,  # Don't auto-remove so we can get logs
                    network_disabled=True,  # Disable network for security
                    mem_limit="256m",  # Limit memory
                    cpu_period=100000,
                    cpu_quota=50000  # Limit CPU to 50%
                )
                
                # Wait for container to finish with timeout
                result = container.wait(timeout=self.timeout)
                exit_code = result['StatusCode']
                
                # Get output
                output = container.logs().decode('utf-8', errors='replace')
                
                # Remove container
                container.remove(force=True)
                
                # Return result
                success = exit_code == 0
                
                return {
                    "success": success,
                    "output": output,
                    "exit_code": exit_code
                }
                
            except Exception as e:
                # Try to clean up container if it exists
                try:
                    containers = self.client.containers.list(all=True, filters={"ancestor": self.image_name})
                    for c in containers:
                        c.remove(force=True)
                except Exception:
                    pass
                
                return {
                    "success": False,
                    "output": f"Container execution failed: {str(e)}"
                }
        
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    def test_sandbox(self) -> bool:
        """
        Test that the sandbox is working correctly
        
        Returns:
            True if sandbox is functional
        """
        test_function_name = "add"
        test_function = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers\"\"\"
    return a + b
"""
        
        test_code = """
import pytest
from tool_function import add

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
"""
        
        result = self.verify_tool(test_function_name, test_function, test_code)
        return result['success']


if __name__ == "__main__":
    # Test the sandbox
    sandbox = SecureSandbox()
    print("Testing sandbox...")
    
    if sandbox.test_sandbox():
        print("✓ Sandbox is working correctly!")
    else:
        print("✗ Sandbox test failed")

