"""
Service Manager for managing service lifecycle and mutations.

Handles:
- Original/working copies of services
- Starting/stopping service instances
- Applying and reverting mutations
- Managing multiple parallel instances on different ports
"""

import shutil
import subprocess
import time
import socket
import platform
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import requests

from .mutator import Mutator, Mutant
from .config import get_service_config


# Configuration
SHOW_OUTPUT = False  # Set to True to show script output during execution


def to_unix_path(path: Path) -> str:
    """Convert Windows path to Unix-style path for Git Bash."""
    path_str = str(path.resolve())
    if platform.system() == "Windows" and len(path_str) >= 2 and path_str[1] == ':':
        # Convert C:\path\to\file to /c/path/to/file
        drive = path_str[0].lower()
        rest = path_str[2:].replace('\\', '/')
        return f"/{drive}{rest}"
    return path_str.replace('\\', '/')


@dataclass
class ServiceInstance:
    """Represents a running service instance."""
    service_name: str
    port: int
    working_dir: Path
    process: Optional[subprocess.Popen] = None
    health_endpoint: str = "/api/v1/utils/health-check"  # Default for FastAPI, can be overridden
    
    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.port}"
    
    def is_healthy(self, timeout: float = 2.0) -> bool:
        """Check if service is responding."""
        try:
            resp = requests.get(f"{self.base_url}{self.health_endpoint}", timeout=timeout)
            return resp.status_code == 200
        except:
            return False


class ServiceManager:
    """
    Manages service lifecycle and mutations.
    
        Directory structure expected:
        services/
            {service_name}/
                original/     # Pristine copy (never modified)
                working/      # Active copy (mutations applied here)
                spec.json     # OpenAPI specification
                start.sh      # Start script
                stop.sh       # Stop script
                reset.sh      # Reset script
    """


    
    def __init__(self, services_root: Path):
        """
        Initialize the service manager.
        
        Args:
            services_root: Root directory containing all services
        """
        self.services_root = Path(services_root)
        self.instances: dict[int, ServiceInstance] = {}  # port -> instance
        self._is_windows = platform.system() == "Windows"
    
    def _run_script(
        self, 
        service_name: str, 
        script_name: str, 
        timeout: int = 60,
        show_output: bool = None
    ) -> bool:
        """
        Helper to run a service script (start.sh, stop.sh, reset.sh).
        
        Args:
            service_name: Name of the service
            script_name: Name of the script to run (e.g., "start.sh")
            timeout: Timeout in seconds
            show_output: Whether to show script output (defaults to SHOW_OUTPUT)
        
        Returns:
            True if script ran successfully, False otherwise
        """
        if show_output is None:
            show_output = SHOW_OUTPUT
            
        service_dir = self.get_service_dir(service_name)
        script_file = service_dir / script_name
        
        if not script_file.exists():
            print(f"      Warning: {script_name} not found: {script_file}")
            return False
        
        try:
            # Use relative path from services_root to avoid Windows path issues with bash
            # e.g., "fastapi/start.sh" instead of "C:\...\services\fastapi\start.sh"
            try:
                script_path = script_file.relative_to(self.services_root).as_posix()
            except ValueError:
                # Fallback to just script name with relative dir
                script_path = f"./{script_name}"
            
            result = subprocess.run(
                ["bash", script_path],
                cwd=str(self.services_root),
                capture_output=not show_output,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                print(f"      Warning: {script_name} failed with code {result.returncode}")
                if not show_output and result.stderr:
                    print(f"      stderr: {result.stderr[:300]}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            print(f"      Warning: {script_name} timed out after {timeout}s")
            return False
        except Exception as e:
            print(f"      Warning: {script_name} error: {e}")
            return False
    
    def get_service_dir(self, service_name: str) -> Path:
        """Get the service directory."""
        return self.services_root / service_name
    
    def get_original_path(self, service_name: str) -> Path:
        """Get path to original (read-only) service copy."""
        return self.get_service_dir(service_name) / "original"
    
    def get_working_path(self, service_name: str) -> Path:
        """Get path to working (mutable) service copy."""
        return self.get_service_dir(service_name) / "working"
    
    def get_spec_path(self, service_name: str) -> Path:
        """Get path to OpenAPI spec."""
        return self.get_service_dir(service_name) / "spec.json"
    
    def get_reset_script_path(self, service_name: str) -> Path:
        """Get path to reset script."""
        return self.get_service_dir(service_name) / "reset.sh"
    
    def setup_service_directories(self, service_name: str) -> None:
        """
        Set up the original and working directories for a service.
        
        The start.sh script clones the repo into original/.
        This method ensures working/ exists (copies from original/).
        """
        service_dir = self.get_service_dir(service_name)
        original_dir = self.get_original_path(service_name)
        working_dir = self.get_working_path(service_name)
        
        if not original_dir.exists():
            raise FileNotFoundError(
                f"Original directory not found: {original_dir}. "
                "Run setup_services script first."
            )
        
        # Always reset working/ from original/
        self.reset_working_copy(service_name)
    
    def reset_working_copy(self, service_name: str, source_subdir: str = None) -> None:
        """
        Reset working/ source files to match original/ (pristine state).
        
        Only resets the source subdirectory to avoid deleting Docker-mounted 
        directories or .git folders.
        
        The source_subdir is determined from the service config if not provided:
        - fastapi: backend/app
        - litellm: litellm
        - rbac-user-management: src
        - todoapp: Todo.Api
        
        Note: We must update file modification times after copying to trigger
        hot-reload detection in the running service.
        """
        original_dir = self.get_original_path(service_name)
        working_dir = self.get_working_path(service_name)
        
        if not original_dir.exists():
            raise FileNotFoundError(f"Original directory not found: {original_dir}")
        
        # Get source_subdir from service config if not provided
        if source_subdir is None:
            service_config = get_service_config(service_name)
            source_subdir = service_config.source_subdir
        
        # If source_subdir is empty, reset the entire working directory
        if not source_subdir:
            print(f"  Warning: No source_subdir configured for {service_name}, resetting entire working directory")
            original_src = original_dir
            working_src = working_dir
        else:
            original_src = original_dir / source_subdir
            working_src = working_dir / source_subdir
        
        if original_src.exists() and working_src.exists():
            # Copy each file from original to working (overwrite)
            for src_file in original_src.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(original_src)
                    dst_file = working_src / rel_path
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    # Touch the file to update modification time and trigger hot-reload
                    os.utime(dst_file, None)
        else:
            print(f"  Warning: Source directory not found: {original_src} or {working_src}")
    
    def _copy_directory(self, src: Path, dst: Path) -> None:
        """Copy a directory, handling Windows permission issues."""
        if dst.exists():
            def remove_readonly(func, path, excinfo):
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(dst, onerror=remove_readonly)
        shutil.copytree(src, dst)
    
    def apply_mutation(self, service_name: str, mutant: Mutant) -> bool:
        """Apply a mutation to the working copy."""
        working_dir = self.get_working_path(service_name)
        mutator = Mutator(working_dir)
        return mutator.apply_mutation(mutant, mode="inject_bug")
    
    def revert_mutation(self, service_name: str, mutant: Mutant) -> bool:
        """Revert a mutation in the working copy."""
        working_dir = self.get_working_path(service_name)
        mutator = Mutator(working_dir)
        return mutator.apply_mutation(mutant, mode="fix_bug")
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def is_service_healthy(self, port: int, health_endpoint: str = "/docs", timeout: float = 5.0) -> bool:
        """
        Check if a service is healthy on the given port.
        
        Args:
            port: The port to check
            health_endpoint: The endpoint to check (default /docs for FastAPI)
            timeout: Request timeout in seconds
            
        Returns:
            True if service responds with 200 OK
        """
        try:
            resp = requests.get(f"http://localhost:{port}{health_endpoint}", timeout=timeout)
            return resp.status_code == 200
        except:
            return False
    
    def get_available_ports(self, count: int, start_port: int = 8000) -> list[int]:
        """Get N available ports starting from start_port."""
        ports = []
        port = start_port
        while len(ports) < count:
            if not self._is_port_in_use(port):
                ports.append(port)
            port += 1
        return ports
    
    def start_service(
        self,
        service_name: str,
        port: int,
        wait_for_healthy: bool = True,
        max_wait_seconds: float = 30.0
    ) -> ServiceInstance:
        """
        Start a service instance on the specified port.
        
        Prerequisites: Run scripts/setup_services.sh first to set up original/ and working/.
        If working/ doesn't exist, will attempt to create it from original/.
        """
        if port in self.instances:
            raise RuntimeError(f"Port {port} already has a running instance")
        
        original_dir = self.get_original_path(service_name)
        working_dir = self.get_working_path(service_name)
        service_dir = self.get_service_dir(service_name)
        
        start_script = service_dir / "start.sh"
        if not start_script.exists():
            raise FileNotFoundError(f"Start script not found: {start_script}")
        
        # Check if setup has been run
        if not original_dir.exists():
            raise FileNotFoundError(
                f"original/ directory not found for {service_name}. "
                "Please run: bash scripts/setup_services.sh"
            )
        
        # Create working/ from original/ if needed
        if not working_dir.exists():
            print(f"Creating working/ from original/...")
            self._copy_directory(original_dir, working_dir)
        
        # Run start.sh to start Docker (use longer timeout, show output)
        print(f"Running start.sh for {service_name}...")
        success = self._run_script(service_name, "start.sh", timeout=180, show_output=True)
        
        if not success:
            print(f"Warning: start.sh may have failed for {service_name}")
        
        # Get service-specific health endpoint
        service_config = get_service_config(service_name)
        
        instance = ServiceInstance(
            service_name=service_name,
            port=port,
            working_dir=working_dir,
            process=None,  # No ongoing process - docker-compose is detached
            health_endpoint=service_config.health_endpoint
        )
        
        self.instances[port] = instance
        
        # Wait for service to be healthy
        if wait_for_healthy:
            start_time = time.time()
            while time.time() - start_time < max_wait_seconds:
                if instance.is_healthy():
                    return instance
                time.sleep(1.0)
            
            # Service didn't become healthy - don't raise, just warn
            # It might still be starting up via Docker
            print(f"Warning: Service {service_name} on port {port} did not become healthy "
                  f"within {max_wait_seconds} seconds. Continuing anyway...")
        
        return instance
    
    def stop_service(self, port: int) -> None:
        """Stop a service running on the specified port using stop.sh."""
        if port not in self.instances:
            return
        
        instance = self.instances[port]
        
        print(f"Running stop.sh for {instance.service_name}...")
        self._run_script(instance.service_name, "stop.sh", timeout=60, show_output=True)
        
        del self.instances[port]
    
    def stop_all_services(self) -> None:
        """Stop all running service instances."""
        ports = list(self.instances.keys())
        for port in ports:
            self.stop_service(port)
    
    def restart_service(self, port: int) -> ServiceInstance:
        """Restart a service on the specified port."""
        if port not in self.instances:
            raise RuntimeError(f"No service running on port {port}")
        
        instance = self.instances[port]
        service_name = instance.service_name
        
        self.stop_service(port)
        return self.start_service(service_name, port)
    
    def get_instance(self, port: int) -> Optional[ServiceInstance]:
        """Get a service instance by port."""
        return self.instances.get(port)
    
    def call_reset_script(self, service_name: str, port: int = 8000) -> bool:
        """
        Call the reset script for a service to reset its database/state.
        
        This resets the database to a clean state before each test execution
        to ensure tests are independent and don't affect each other.
        
        Returns True if successful.
        """
        result = self._run_script(service_name, "reset.sh", timeout=60)
        self.wait_for_service_health(service_name, port)
        return result

    def wait_for_service_health(self, service_name: str, port: int, max_wait: float = 30.0) -> None:
        """
        Wait for the service to be healthy after a mutation is applied.
        
        Polls the health endpoint until it responds successfully.
        
        Args:
            service_name: Name of the service to check
            port: Port the service is running on
            max_wait: Maximum time to wait in seconds
        """
        config = get_service_config(service_name)
        health_url = f"http://localhost:{port}{config.health_endpoint}"
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)
        
        print(f"      Warning: Service did not become healthy within {max_wait}s")