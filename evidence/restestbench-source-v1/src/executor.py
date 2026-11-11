"""
Test Executor module for running tests against service instances.
"""

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .mutator import Requirement
from .service_manager import ServiceManager
from .generator import GeneratedTest, GenerationMode


@dataclass
class ExecutionResult:
    """Result of a single test execution."""
    test_file: Path
    requirement_id: int
    generation_mode: GenerationMode  # How was this test generated?
    mutant_index_generated: Optional[int]  # Mutation applied during generation (if any)
    execution_context: str  # "valid" or "mutated_{index}"
    mutant_index_executed: Optional[int]  # Mutation applied during execution (if any)
    passed: bool
    output: str
    return_code: int
    duration_ms: float
    
    def to_dict(self, output_dir: Optional[Path] = None) -> dict:
        """Convert to dict. If output_dir is provided, test_file will be relative to it."""
        if output_dir:
            try:
                # Use POSIX-style paths (forward slashes) for cross-platform compatibility
                test_file_str = self.test_file.relative_to(output_dir).as_posix()
            except ValueError:
                test_file_str = str(self.test_file)  # Keep absolute if not relative to output_dir
        else:
            test_file_str = str(self.test_file)
        
        return {
            "test_file": test_file_str,
            "requirement_id": self.requirement_id,
            "generation_mode": self.generation_mode.value,
            "mutant_index_generated": self.mutant_index_generated,
            "execution_context": self.execution_context,
            "mutant_index_executed": self.mutant_index_executed,
            "passed": self.passed,
            "return_code": self.return_code,
            "duration_ms": self.duration_ms,
            "output": self.output[:2000] if len(self.output) > 2000 else self.output
        }


class TestExecutor:
    """
    Executes tests against service instances.
    
    Workflow for each test:
    1. Reset service to valid state
    2. Optionally apply a mutation
    3. Run the test
    4. Record result
    """
    
    def __init__(
        self,
        tool,  # TestGeneratorTool
        service_manager: ServiceManager
    ):
        self.tool = tool
        self.service_manager = service_manager
    
    def execute_test(
        self,
        test_file: Path,
        timeout: int = 60
    ) -> tuple[bool, str, int, float]:
        """
        Execute a single test file.
        
        Args:
            test_file: Path to the test file
            timeout: Test execution timeout
        
        Returns:
            Tuple of (passed, output, return_code, duration_ms)
        """
        # Get the test command from the tool
        test_command = self.tool.get_test_command(str(test_file))
        
        start_time = time.time()
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(test_file.parent)
            )
            duration_ms = (time.time() - start_time) * 1000
            
            passed = result.returncode == 0
            output = result.stdout + result.stderr
            
            return passed, output, result.returncode, duration_ms
            
        except subprocess.TimeoutExpired:
            duration_ms = timeout * 1000
            return False, f"Test timed out after {timeout}s", -1, duration_ms
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return False, f"Execution error: {str(e)}", -1, duration_ms
    
    def execute_full(
        self,
        test: GeneratedTest,
        requirement: Requirement,
        port: int = 8000
    ) -> list[ExecutionResult]:
        """
        Execute a test against valid and all mutated implementations.
        
        Execution plan:
        1. Run on valid service (should PASS)
        2. For each mutant: apply mutation, run test (should FAIL to kill mutant)
        
        Returns:
            1 + N results (1 valid + N mutant executions)
        """
        results = []
        
        # Execute on valid service
        self.service_manager.reset_working_copy(requirement.service)
        self.service_manager.wait_for_service_health(requirement.service, port)
        self.service_manager.call_reset_script(requirement.service, port)
        passed, output, rc, duration = self.execute_test(test.test_file)
        status = "\033[92mPASSED\033[0m" if passed else "\033[91mFAILED\033[0m"
        print(f"      Test {status} on valid implementation")
        
        results.append(ExecutionResult(
            test_file=test.test_file,
            requirement_id=requirement.id,
            generation_mode=test.mode,
            mutant_index_generated=test.mutant_index,
            execution_context="valid",
            mutant_index_executed=None,
            passed=passed,
            output=output,
            return_code=rc,
            duration_ms=duration
        ))
        
        # Skip mutation tests if test already fails on valid implementation
        # If it fails here, it will obviously fail on all mutations too
        if not passed:
            print(f"      Skipping {len(requirement.mutants)} mutations (failed on valid)")
            return results
        
        # Execute on each mutated service
        for i, mutant in enumerate(requirement.mutants):
            # Reset and apply this mutation
            self.service_manager.reset_working_copy(requirement.service)
            applied = self.service_manager.apply_mutation(requirement.service, mutant)
            
            if not applied:
                results.append(ExecutionResult(
                    test_file=test.test_file,
                    requirement_id=requirement.id,
                    generation_mode=test.mode,
                    mutant_index_generated=test.mutant_index,
                    execution_context=f"mutated_{i}",
                    mutant_index_executed=i,
                    passed=False,
                    output="Mutation could not be applied",
                    return_code=-1,
                    duration_ms=0
                ))
                continue
            
            self.service_manager.wait_for_service_health(requirement.service, port)
            self.service_manager.call_reset_script(requirement.service, port)
            
            # Run test against mutated service
            passed, output, rc, duration = self.execute_test(test.test_file)
            # For mutations: FAILED is good (mutation killed), PASSED is bad (mutation survived)
            status = "\033[91mPASSED\033[0m" if passed else "\033[92mFAILED\033[0m"
            print(f"      Test {status} on mutated_{i}")
            
            results.append(ExecutionResult(
                test_file=test.test_file,
                requirement_id=requirement.id,
                generation_mode=test.mode,
                mutant_index_generated=test.mutant_index,
                execution_context=f"mutated_{i}",
                mutant_index_executed=i,
                passed=passed,
                output=output,
                return_code=rc,
                duration_ms=duration
            ))
        
        # Restore service to valid state
        self.service_manager.reset_working_copy(requirement.service)
        self.service_manager.wait_for_service_health(requirement.service, port)
        self.service_manager.call_reset_script(requirement.service, port)
        
        return results
    
    def execute_all_for_test(
        self,
        test: GeneratedTest,
        requirement: Requirement,
        port: int = 8000
    ) -> list[ExecutionResult]:
        """
        Execute all test scenarios for a generated test.
        
        Runs the test on valid implementation and all mutated implementations,
        regardless of how the test was generated.
        """
        return self.execute_full(test, requirement, port)
    
    def save_execution_results(
        self,
        results: list[ExecutionResult],
        filepath: Path,
        skipped_mutations: int = 0
    ) -> None:
        """Save execution results to a JSON file."""
        output_dir = filepath.parent
        data = {
            "total_executions": len(results),
            "skipped_mutations": skipped_mutations,
            "results": [r.to_dict(output_dir) for r in results]
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
