"""
CSV Results Writer for benchmark runs.

Creates and appends to a central CSV file tracking all benchmark results.
Each row represents one service from one benchmark run.
"""

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


# CSV file location (in output directory)
RESULTS_CSV_FILENAME = "benchmark_results.csv"

# Column headers for the CSV
CSV_COLUMNS = [
    "run_id",
    "tool",
    "model",
    "service_name",
    "generation_context",        # "valid" or "mutated" - which implementation was used for generation
    "precise_description",
    "interactive",
    "num_requirements",
    "total_executions",
    # Test results (applies to both interactive and non-interactive modes)
    "tests_count",
    "passed_on_valid (TN)",      # TN - test passes on valid (good for non-interactive)
    "failed_on_valid (FP)",      # FP - test fails on valid (broken test)
    "killed_mutations (TP)",     # TP - test kills mutations (good)
    "missed_mutations (FN)",     # FN - mutations survived (bad)
    "skipped_mutations",         # Mutations skipped (test failed on valid)
    "score",
    "max_score",
    "percentage",
    "sum_cost",
    "avg_generation_time_seconds",
    "output_folder"
]


@dataclass
class BenchmarkResultRow:
    """Single row of benchmark results for one service."""
    run_id: str
    tool: str
    model: str
    service_name: str
    generation_context: str      # "valid" or "mutated"
    precise_description: bool
    interactive: bool
    num_requirements: int
    total_executions: int
    # Test results (applies to both interactive and non-interactive modes)
    tests_count: int
    passed_on_valid: int      # TN - test passes on valid
    failed_on_valid: int      # FP - test fails on valid (broken test)
    killed_mutations: int     # TP - test kills mutations (good)
    missed_mutations: int     # FN - mutations survived (bad)
    skipped_mutations: int    # Mutations skipped due to test failing on valid
    score: int
    max_score: int
    percentage: float
    sum_cost: float
    avg_generation_time_seconds: float
    output_folder: str

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV writing."""
        return {
            "run_id": self.run_id,
            "tool": self.tool,
            "model": self.model,
            "service_name": self.service_name,
            "generation_context": self.generation_context,
            "precise_description": str(self.precise_description).lower(),
            "interactive": str(self.interactive).lower(),
            "num_requirements": self.num_requirements,
            "total_executions": self.total_executions,
            # Test results - must match CSV_COLUMNS exactly
            "tests_count": self.tests_count,
            "passed_on_valid (TN)": self.passed_on_valid,
            "failed_on_valid (FP)": self.failed_on_valid,
            "killed_mutations (TP)": self.killed_mutations,
            "missed_mutations (FN)": self.missed_mutations,
            "skipped_mutations": self.skipped_mutations,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": f"{self.percentage:.2f}",
            "sum_cost": f"{self.sum_cost:.6f}",
            "avg_generation_time_seconds": f"{self.avg_generation_time_seconds:.2f}",
            "output_folder": self.output_folder
        }


def parse_tool_name(tool_name: str, model_override: Optional[str] = None) -> tuple[str, str]:
    """
    Parse tool name into tool and model components.
    
    Examples:
        "llama4scout_single-step" -> ("single-step", "llama-4-scout-17b")  # with model_override
        "llama4scout_refinement" -> ("refinement", "llama-4-scout-17b")  # with model_override
        "gpt5nano_single-step" -> ("single-step", "gpt5nano")
        "golden_tests" -> ("golden_tests", "n/a")
    
    Args:
        tool_name: Name of the tool (e.g., "llama4scout_single-step")
        model_override: If provided, use this as the model name (full model ID)
    
    Returns:
        Tuple of (tool/approach, model)
    """
    # Known approach suffixes
    approach_suffixes = [
        "_single-step", "_single_step", "_zero-shot", "_zero_shot",
        "_refinement", "_refinement-loop",
        "_chain-of-thought", "_few-shot", "_cot", "_react", "_interactive"
    ]
    
    for suffix in approach_suffixes:
        if tool_name.endswith(suffix) or suffix in tool_name:
            # Extract approach name from suffix
            approach = suffix.lstrip("_").replace("_", "-")  # Normalize: single_step -> single-step
            model = model_override if model_override else tool_name.replace(suffix, "")
            return approach, model
    
    # If model_override is provided and no suffix matched, use it with tool_name as tool
    if model_override:
        return tool_name, model_override
    
    # Check if it starts with known model prefixes
    model_prefixes = ["gpt", "claude", "gemini", "llama", "mistral"]
    for prefix in model_prefixes:
        if tool_name.lower().startswith(prefix):
            # Try to find underscore separator
            if "_" in tool_name:
                parts = tool_name.rsplit("_", 1)
                return parts[1], parts[0]
    
    # Fallback: treat entire name as tool, no model
    return tool_name, "n/a"


class ResultsCSVWriter:
    """Writes benchmark results to a CSV file."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize the CSV writer.
        
        Args:
            output_dir: Root output directory where CSV file will be stored
        """
        self.output_dir = Path(output_dir)
        self.csv_path = self.output_dir / RESULTS_CSV_FILENAME
        
    def _ensure_csv_exists(self) -> None:
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_path.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
    
    def append_result(self, row: BenchmarkResultRow) -> None:
        """
        Append a single result row to the CSV file.
        
        Args:
            row: The benchmark result row to append
        """
        self._ensure_csv_exists()
        
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row.to_dict())
    
    def append_results(self, rows: list[BenchmarkResultRow]) -> None:
        """
        Append multiple result rows to the CSV file.
        
        Args:
            rows: List of benchmark result rows to append
        """
        self._ensure_csv_exists()
        
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            for row in rows:
                writer.writerow(row.to_dict())


def generate_run_id() -> str:
    """
    Generate a unique run ID based on current date and time.
    
    Format: YYYYMMDD_HHMMSS
    
    Returns:
        String run ID
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def collect_service_results(
    run_id: str,
    tool_name: str,
    service_name: str,
    use_precise: bool,
    interactive: bool,
    service_output_dir: Path,
    output_folder_name: str,
    model_override: Optional[str] = None
) -> list[BenchmarkResultRow]:
    """
    Collect all results for a service and create result row(s).
    
    For non-interactive tools: returns one row (valid-generated tests only)
    For interactive tools: returns TWO rows (one for valid, one for mutated)
    
    Args:
        run_id: Unique identifier for this benchmark run
        tool_name: Name of the tool used (e.g., "gpt5nano_single-step")
        service_name: Name of the service (e.g., "fastapi")
        use_precise: Whether precise descriptions were used
        interactive: Whether tool is interactive
        service_output_dir: Path to service's output directory
        output_folder_name: Name of the output folder (relative)
        model_override: If provided, use this as the model name instead of parsing tool_name
    
    Returns:
        List of BenchmarkResultRow (1 for non-interactive, 2 for interactive)
    """
    import json
    
    # Parse tool name into tool and model
    tool, model = parse_tool_name(tool_name, model_override)
    
    # Load generation manifest
    manifest_file = service_output_dir / "generation_manifest.json"
    if not manifest_file.exists():
        return []
    
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Load execution results
    results_file = service_output_dir / "execution_results.json"
    if not results_file.exists():
        return []
    
    with open(results_file, "r", encoding="utf-8") as f:
        execution_data = json.load(f)
    
    # Load evaluation results
    eval_file = service_output_dir / "evaluation_results.json"
    if not eval_file.exists():
        return []
    
    with open(eval_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)
    
    # Extract metrics
    summary = eval_data.get("summary", {})
    
    # Count tests by generation mode
    tests = manifest.get("tests", [])
    valid_tests = [t for t in tests if t.get("mode") == "valid"]
    mutated_tests = [t for t in tests if t.get("mode") == "mutated"]
    
    # Count requirement numbers
    num_requirements = summary.get("total_requirements", 0)
    
    # Process execution results
    results = execution_data.get("results", [])
    total_executions = len(results)
    skipped_mutations = execution_data.get("skipped_mutations", 0)
    
    rows = []
    
    # --- ROW 1: Valid-generated tests ---
    valid_tests_count = len(valid_tests)
    valid_cost = sum(t.get("generation_cost", 0) or 0 for t in valid_tests)
    valid_gen_times = [t.get("generation_time_seconds", 0) or 0 for t in valid_tests]
    valid_avg_time = sum(valid_gen_times) / len(valid_gen_times) if valid_gen_times else 0.0
    
    # Count valid test execution results (for FP/TN breakdown)
    valid_passed_on_valid = 0
    valid_failed_on_valid = 0
    valid_executions = 0
    
    for result in results:
        if result.get("generation_mode", "valid") != "valid":
            continue
        valid_executions += 1
        execution_context = result.get("execution_context", "")
        passed = result.get("passed", False)
        
        if execution_context == "valid":
            if passed:
                valid_passed_on_valid += 1
            else:
                valid_failed_on_valid += 1
    
    # Use scores directly from evaluation.json (already calculated by evaluator.py)
    valid_score = summary.get("valid_score", 0)
    valid_max_score = summary.get("valid_max_score", 0)
    valid_percentage = summary.get("valid_percentage", 0.0)
    
    # Calculate killed/missed from score and max_score
    valid_killed = valid_score
    valid_missed = valid_max_score - valid_score - skipped_mutations
    
    valid_row = BenchmarkResultRow(
        run_id=run_id,
        tool=tool,
        model=model,
        service_name=service_name,
        generation_context="valid",
        precise_description=use_precise,
        interactive=interactive,
        num_requirements=num_requirements,
        total_executions=valid_executions,
        tests_count=valid_tests_count,
        passed_on_valid=valid_passed_on_valid,
        failed_on_valid=valid_failed_on_valid,
        killed_mutations=valid_killed,
        missed_mutations=valid_missed,
        skipped_mutations=skipped_mutations,
        score=valid_score,
        max_score=valid_max_score,
        percentage=valid_percentage,
        sum_cost=valid_cost,
        avg_generation_time_seconds=valid_avg_time,
        output_folder=output_folder_name
    )
    rows.append(valid_row)
    
    # --- ROW 2: Mutated-generated tests (only for interactive tools) ---
    if interactive and mutated_tests:
        mutated_tests_count = len(mutated_tests)
        mutated_cost = sum(t.get("generation_cost", 0) or 0 for t in mutated_tests)
        mutated_gen_times = [t.get("generation_time_seconds", 0) or 0 for t in mutated_tests]
        mutated_avg_time = sum(mutated_gen_times) / len(mutated_gen_times) if mutated_gen_times else 0.0
        
        # Count mutated test execution results (for FP/TN breakdown)
        mutated_passed_on_valid = 0
        mutated_failed_on_valid = 0
        mutated_executions = 0
        
        for result in results:
            if result.get("generation_mode", "valid") != "mutated":
                continue
            mutated_executions += 1
            execution_context = result.get("execution_context", "")
            passed = result.get("passed", False)
            
            if execution_context == "valid":
                if passed:
                    mutated_passed_on_valid += 1
                else:
                    mutated_failed_on_valid += 1
        
        # Use scores directly from evaluation.json (already calculated by evaluator.py)
        mutated_score = summary.get("mutated_score", 0.0)
        mutated_max_score = summary.get("mutated_max_score", 0)
        mutated_percentage = summary.get("mutated_percentage", 0.0)
        
        # For mutated tests, we need to aggregate actual TP/FN from all requirements
        # because mutated_score is sum of averages, not a simple count
        mutated_killed_total = 0
        mutated_survived_total = 0
        
        requirements = eval_data.get("requirements", [])
        for req in requirements:
            mutated_tests_data = req.get("mutated_tests", {})
            for test in mutated_tests_data.get("tests", []):
                if test.get("passes_on_valid", False):
                    # Only count if test passes on valid (valid tests earn points)
                    mutated_killed_total += len(test.get("mutants_killed", []))
                    mutated_survived_total += len(test.get("mutants_survived", []))
        
        mutated_killed = mutated_killed_total
        mutated_missed = mutated_survived_total
        
        mutated_row = BenchmarkResultRow(
            run_id=run_id,
            tool=tool,
            model=model,
            service_name=service_name,
            generation_context="mutated",
            precise_description=use_precise,
            interactive=interactive,
            num_requirements=num_requirements,
            total_executions=mutated_executions,
            tests_count=mutated_tests_count,
            passed_on_valid=mutated_passed_on_valid,
            failed_on_valid=mutated_failed_on_valid,
            killed_mutations=mutated_killed,
            missed_mutations=mutated_missed,
            skipped_mutations=0,  # N/A for mutated tests
            score=mutated_score,
            max_score=mutated_max_score,
            percentage=mutated_percentage,
            sum_cost=mutated_cost,
            avg_generation_time_seconds=mutated_avg_time,
            output_folder=output_folder_name
        )
        rows.append(mutated_row)
    
    return rows
