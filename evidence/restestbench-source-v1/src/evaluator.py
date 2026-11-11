"""
Evaluator module for scoring test quality based on execution results.

Scoring Logic:
--------------
All tests are evaluated by:
- Must PASS on valid implementation to earn any points
- Score = number of killed mutations (test FAILS on mutated implementation)
- Max score per test = number of mutations

Per-requirement scoring (reported separately):
1. Valid-generated test: score = mutations killed by this single test
2. Mutated-generated tests: score = average mutations killed across all mutated tests

This allows comparing the quality of tests generated on valid vs mutated implementations.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .generator import GenerationMode
from .executor import ExecutionResult


@dataclass
class TestScore:
    """Score for a single generated test."""
    requirement_id: int
    generation_mode: GenerationMode
    mutant_index: Optional[int]  # Which mutant was active during generation (if any)
    
    passes_on_valid: bool = False
    mutants_killed: list[int] = field(default_factory=list)
    mutants_survived: list[int] = field(default_factory=list)
    score: int = 0
    
    def to_dict(self) -> dict:
        result = {
            "requirement_id": self.requirement_id,
            "generation_mode": self.generation_mode.value,
            "passes_on_valid": self.passes_on_valid,
            "mutants_killed": self.mutants_killed,
            "mutants_survived": self.mutants_survived,
            "score": self.score,
        }
        if self.mutant_index is not None:
            result["generated_on_mutant"] = self.mutant_index
        return result


class Evaluator:
    """Evaluates test quality based on execution results."""
    
    def evaluate_test(
        self,
        results: list[ExecutionResult],
        num_mutants: int,
        generation_mode: GenerationMode = GenerationMode.VALID,
        mutant_index: Optional[int] = None
    ) -> TestScore:
        """
        Evaluate a single test's execution results.
        
        Args:
            results: Execution results for this test
            num_mutants: Total number of mutants for the requirement
            generation_mode: How the test was generated (VALID or MUTATED)
            mutant_index: Which mutant was active during generation (if MUTATED mode)
            
        Returns:
            TestScore with killed/survived mutants and final score
        """
        if not results:
            return TestScore(
                requirement_id=-1,
                generation_mode=generation_mode,
                mutant_index=mutant_index,
                score=0
            )
        
        first_result = results[0]
        score = TestScore(
            requirement_id=first_result.requirement_id,
            generation_mode=generation_mode,
            mutant_index=mutant_index
        )
        
        # Check if test passes on valid implementation
        valid_result = next(
            (r for r in results if r.execution_context == "valid"),
            None
        )
        if valid_result:
            score.passes_on_valid = valid_result.passed
        
        # Check each mutant execution
        for i in range(num_mutants):
            mutant_result = next(
                (r for r in results if r.execution_context == f"mutated_{i}"),
                None
            )
            if mutant_result:
                # Mutant is killed if test FAILS on mutated code
                if not mutant_result.passed:
                    score.mutants_killed.append(i)
                else:
                    score.mutants_survived.append(i)
            else:
                # No result for this mutant - counts as survived
                score.mutants_survived.append(i)
        
        # Calculate score: mutations killed, but only if test passes on valid
        if not score.passes_on_valid:
            score.mutants_survived = list(range(num_mutants))
            score.mutants_killed = []
            score.score = 0
        else:
            score.score = len(score.mutants_killed)
        
        return score
    
    def evaluate_all(
        self,
        results_by_test: dict[str, list[ExecutionResult]],
        requirement_mutant_counts: dict[int, int],
        test_metadata: dict[str, dict]
    ) -> list[TestScore]:
        """
        Evaluate all tests.
        
        Args:
            results_by_test: Mapping of test file path to its execution results
            requirement_mutant_counts: Number of mutants per requirement ID
            test_metadata: Metadata about each test {mode, mutant_index}
            
        Returns:
            List of TestScores for all tests
        """
        scores = []
        
        for test_file, results in results_by_test.items():
            if not results:
                continue
            
            metadata = test_metadata.get(test_file, {})
            mode_str = metadata.get("mode", "valid")
            mode = GenerationMode.VALID if mode_str == "valid" else GenerationMode.MUTATED
            mutant_index = metadata.get("mutant_index")
            req_id = results[0].requirement_id
            num_mutants = requirement_mutant_counts.get(req_id, 0)
            
            score = self.evaluate_test(results, num_mutants, mode, mutant_index)
            scores.append(score)
        
        return scores
    
    def aggregate_scores(self, scores: list[TestScore]) -> dict:
        """
        Aggregate scores into final benchmark results.
        
        Separates valid-generated and mutated-generated test scores:
        - valid_score: score from test generated on valid implementation
        - mutated_score: average score from tests generated on mutated implementations
        
        Each has its own max_score and percentage.
        
        Returns:
            Dictionary with summary and per-requirement details
        """
        if not scores:
            return {
                "summary": {
                    "valid_score": 0,
                    "valid_max_score": 0,
                    "valid_percentage": 0.0,
                    "mutated_score": 0.0,
                    "mutated_max_score": 0,
                    "mutated_percentage": 0.0,
                    "total_requirements": 0,
                    "total_tests": 0
                },
                "requirements": []
            }
        
        req_ids = sorted(set(s.requirement_id for s in scores))
        
        total_valid_score = 0
        total_valid_max_score = 0
        total_mutated_score = 0.0
        total_mutated_max_score = 0
        requirements = []
        
        for req_id in req_ids:
            req_scores = [s for s in scores if s.requirement_id == req_id]
            if not req_scores:
                continue
            
            # Separate valid and mutated tests
            valid_tests = [s for s in req_scores if s.generation_mode == GenerationMode.VALID]
            mutated_tests = [s for s in req_scores if s.generation_mode == GenerationMode.MUTATED]
            
            # Get number of mutants (from any score, they should all have same count)
            num_mutants = len(req_scores[0].mutants_killed) + len(req_scores[0].mutants_survived)
            
            # Valid test score (should be 0 or 1 test)
            valid_score = valid_tests[0].score if valid_tests else 0
            total_valid_score += valid_score
            total_valid_max_score += num_mutants
            
            # Mutated tests average score
            if mutated_tests:
                mutated_avg = sum(s.score for s in mutated_tests) / len(mutated_tests)
                total_mutated_max_score += num_mutants
            else:
                mutated_avg = 0.0
            total_mutated_score += mutated_avg
            
            # Build requirement details
            req_data = {
                "requirement_id": req_id,
                "num_mutants": num_mutants,
                "valid_test": None,
                "mutated_tests": {
                    "count": len(mutated_tests),
                    "average_score": round(mutated_avg, 2),
                    "max_score": num_mutants,
                    "tests": []
                }
            }
            
            # Add valid test details
            if valid_tests:
                vt = valid_tests[0]
                req_data["valid_test"] = {
                    "passes_on_valid": vt.passes_on_valid,
                    "mutants_killed": vt.mutants_killed,
                    "mutants_survived": vt.mutants_survived,
                    "score": vt.score,
                    "max_score": num_mutants
                }
            
            # Add mutated test details
            for mt in mutated_tests:
                req_data["mutated_tests"]["tests"].append({
                    "generated_on_mutant": mt.mutant_index,
                    "passes_on_valid": mt.passes_on_valid,
                    "mutants_killed": mt.mutants_killed,
                    "mutants_survived": mt.mutants_survived,
                    "score": mt.score,
                    "max_score": num_mutants
                })
            
            requirements.append(req_data)
        
        # Calculate percentages separately for valid and mutated
        valid_percentage = round(total_valid_score / total_valid_max_score * 100, 2) if total_valid_max_score > 0 else 0.0
        mutated_percentage = round(total_mutated_score / total_mutated_max_score * 100, 2) if total_mutated_max_score > 0 else 0.0
        
        return {
            "summary": {
                "valid_score": total_valid_score,
                "valid_max_score": total_valid_max_score,
                "valid_percentage": valid_percentage,
                "mutated_score": round(total_mutated_score, 2),
                "mutated_max_score": total_mutated_max_score,
                "mutated_percentage": mutated_percentage,
                "total_requirements": len(req_ids),
                "total_tests": len(scores)
            },
            "requirements": requirements
        }
    
    def save_evaluation(self, aggregated: dict, filepath: Path) -> None:
        """Save evaluation results to a JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(aggregated, f, indent=2)
