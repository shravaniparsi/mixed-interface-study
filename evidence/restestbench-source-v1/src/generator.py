"""
Test Generator module for generating tests on valid and mutated implementations.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .mutator import Requirement, Mutant
from .service_manager import ServiceManager


class GenerationMode(Enum):
    """Mode of test generation."""
    VALID = "valid"      # Generate test on valid (pristine) implementation
    MUTATED = "mutated"  # Generate test on mutated implementation


@dataclass
class GeneratedTest:
    """Represents a generated test."""
    requirement_id: int
    service_name: str
    mode: GenerationMode
    mutant_index: Optional[int]  # Only for MUTATED mode
    test_file: Path
    test_code: str
    generation_cost: Optional[float] = None
    generation_time_seconds: Optional[float] = None
    
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
            "requirement_id": self.requirement_id,
            "service_name": self.service_name,
            "mode": self.mode.value,
            "mutant_index": self.mutant_index,
            "test_file": test_file_str,
            "generation_cost": self.generation_cost,
            "generation_time_seconds": self.generation_time_seconds
        }


class TestGenerator:
    """
    Generates tests using configured LLM tool.
    
    Supports two modes:
    - VALID: Generate test on pristine (unmutated) service
    - MUTATED: Generate test on service with a specific mutation applied
    
    For non-interactive tools (INTERACTIVE=False), only VALID mode is used
    since the generated test would be identical regardless of service state.
    """
    
    def __init__(
        self,
        tool,  # TestGeneratorTool
        service_manager: ServiceManager,
        output_dir: Path
    ):
        self.tool = tool
        self.service_manager = service_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_test_output_path(
        self,
        requirement: Requirement,
        mode: GenerationMode,
        mutant_index: Optional[int] = None
    ) -> Path:
        """Get the output path for a generated test."""
        # Note: output_dir already includes service name from run_mutation_benchmark.py
        # So we don't add service subfolder here to avoid redundancy
        if mode == GenerationMode.VALID:
            test_dir = self.output_dir / f"req_{requirement.id}"
        else:
            test_dir = self.output_dir / f"req_{requirement.id}_mut_{mutant_index}"
        
        test_dir.mkdir(parents=True, exist_ok=True)
        return test_dir / self.tool.test_file_name
    
    def generate_test(
        self,
        requirement: Requirement,
        mode: GenerationMode,
        mutant_index: Optional[int] = None,
        port: int = 8000,
        use_precise: bool = True
    ) -> GeneratedTest:
        """
        Generate a single test for a requirement.
        
        Args:
            requirement: The requirement to generate a test for
            mode: VALID or MUTATED
            mutant_index: Index of mutation to apply (required for MUTATED mode)
            port: Port where service is running
            use_precise: Whether to use precise (True) or vague (False) requirement description
            
        Returns:
            GeneratedTest with the generated test info
        """
        if mode == GenerationMode.MUTATED and mutant_index is None:
            raise ValueError("mutant_index required for MUTATED mode")
        
        self.service_manager.call_reset_script(requirement.service)

        # Get paths
        test_file = self._get_test_output_path(requirement, mode, mutant_index)
        test_dir = test_file.parent
        spec_path = self.service_manager.get_spec_path(requirement.service)
        reset_script = self.service_manager.get_reset_script_path(requirement.service)
        
        # Get scenario description
        if use_precise:
            scenario = requirement.requirement_precise
        else:
            scenario = requirement.requirement_vague
        
        # Ensure service is in correct state
        self.service_manager.reset_working_copy(requirement.service)
        
        if mode == GenerationMode.MUTATED:
            mutant = requirement.mutants[mutant_index]
            applied = self.service_manager.apply_mutation(requirement.service, mutant)
            if not applied:
                print(f"    Could not apply mutation {mutant_index} for req {requirement.id}, creating placeholder")
                # Create placeholder test so the benchmark can continue
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.write_text("# Mutation could not be applied - placeholder test\n", encoding='utf-8')
                return GeneratedTest(
                    requirement_id=requirement.id,
                    service_name=requirement.service,
                    mode=mode,
                    mutant_index=mutant_index,
                    test_file=test_file,
                    test_code="# Mutation could not be applied - placeholder test\n",
                    generation_cost=0.0,
                    generation_time_seconds=0.0
                )
        
        # Generate the test
        service_url = f"http://localhost:{port}"
        
        import time
        start_time = time.time()
        
        # Update logger context before generation so all log entries for this
        # requirement are tagged correctly.
        logger = getattr(self.tool, 'logger', None)
        if logger:
            logger.set_context(service=requirement.service, requirement_id=requirement.id)

        try:
            result = self.tool.generate_test(
                scenario_description=scenario,
                test_file_path=str(test_file),
                test_dir_path=str(test_dir),
                spec_path=str(spec_path),
                reset_script_path=str(reset_script),
                service_base_url=service_url
            )
        except Exception as e:
            print(f"    Tool exception: {e}")
            print(f"    Creating empty test file to continue")
            logger = getattr(self.tool, 'logger', None)
            if logger:
                logger.error("tool_exception",
                    f"Unhandled exception in tool.generate_test: {type(e).__name__}: {str(e)[:300]}",
                    error_type=type(e).__name__, error_message=str(e)[:500])
            # Create empty/dummy test file so benchmark can continue
            Path(test_file).write_text("# Test generation failed\n", encoding='utf-8')
            result = None
            Path(test_file).write_text("# Test generation failed\n", encoding='utf-8')
            result = None
        
        generation_time = time.time() - start_time
        
        # Handle both old tools (return cost) and new tools (return dict with cost)
        if isinstance(result, dict):
            cost = result.get('cost')
        else:
            cost = result
        
        # Read the generated test
        if not test_file.exists():
            print(f"    Test file not found after generation: {test_file}")
            Path(test_file).write_text("# Test generation failed\n", encoding='utf-8')
        
        test_code = test_file.read_text(encoding="utf-8")
        
        return GeneratedTest(
            requirement_id=requirement.id,
            service_name=requirement.service,
            mode=mode,
            mutant_index=mutant_index,
            test_file=test_file,
            test_code=test_code,
            generation_cost=cost,
            generation_time_seconds=generation_time
        )
    
    def generate_all_for_requirement(
        self,
        requirement: Requirement,
        port: int = 8000,
        use_precise: bool = True
    ) -> list[GeneratedTest]:
        """
        Generate all tests for a requirement.
        
        For interactive tools:
        - 1 test on valid implementation
        - N tests on mutated implementations (one per mutant)
        
        For non-interactive tools:
        - Only 1 test on valid implementation (mutated tests would be identical)
        
        Returns:
            List of GeneratedTest objects
        """
        tests = []

        # Always generate valid test
        valid_test = self.generate_test(
            requirement=requirement,
            mode=GenerationMode.VALID,
            mutant_index=None,
            port=port,
            use_precise=use_precise
        )
        tests.append(valid_test)
        
        # Only generate mutated tests for interactive tools
        if self.tool.INTERACTIVE:
            for i in range(len(requirement.mutants)):
                mutated_test = self.generate_test(
                    requirement=requirement,
                    mode=GenerationMode.MUTATED,
                    mutant_index=i,
                    port=port,
                    use_precise=use_precise
                )
                tests.append(mutated_test)
        
        return tests
    
    def save_generation_manifest(
        self,
        tests: list[GeneratedTest],
        filepath: Path
    ) -> None:
        """Save a manifest of all generated tests."""
        output_dir = filepath.parent
        manifest = {
            "tool_name": type(self.tool).__name__,
            "interactive": self.tool.INTERACTIVE,
            "tests": [t.to_dict(output_dir) for t in tests]
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
