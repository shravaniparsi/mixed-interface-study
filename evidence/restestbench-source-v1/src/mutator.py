"""
Mutator module for applying code mutations to source files.

Supports two mutation modes:
1. Line-based: When 'line' is set, replaces only that specific line
2. Whole-file: When 'line' is null, does a string replacement across the entire file
"""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Mutant:
    """Represents a single code mutation."""
    file: str
    original: str
    mutated: str
    line: Optional[int] = None  # None means whole-file replacement
    
    @classmethod
    def from_dict(cls, data: dict) -> "Mutant":
        return cls(
            file=data["file"],
            original=data["original"],
            mutated=data["mutated"],
            line=data.get("line")  # Will be None if not present or null
        )
    
    def to_dict(self) -> dict:
        result = {
            "file": self.file,
            "original": self.original,
            "mutated": self.mutated,
        }
        if self.line is not None:
            result["line"] = self.line
        return result


@dataclass
class Requirement:
    """Represents a test requirement with its associated mutants."""
    id: int
    service: str
    requirement_vague: str
    requirement_precise: str
    mutants: list[Mutant]
    
    @classmethod
    def from_file(cls, filepath: str | Path) -> "Requirement":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            id=data["id"],
            service=data["service"],
            requirement_vague=data["requirement_vague"],
            requirement_precise=data["requirement_precise"],
            mutants=[Mutant.from_dict(m) for m in data["mutants"]]
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service": self.service,
            "requirement_vague": self.requirement_vague,
            "requirement_precise": self.requirement_precise,
            "mutants": [m.to_dict() for m in self.mutants]
        }


class Mutator:
    """
    Applies mutations to source files for mutation testing.
    
    Supports bidirectional testing:
    - inject_bug mode: Applies mutated code (introduces bugs)
    - fix_bug mode: Applies original code (fixes bugs / reverts)
    """
    
    def __init__(self, service_root: Path):
        """
        Initialize the mutator.
        
        Args:
            service_root: Root directory of the service under test
        """
        self.service_root = Path(service_root)
    
    def apply_mutation(
        self,
        mutant: Mutant,
        mode: str = "inject_bug"
    ) -> bool:
        """
        Apply a single mutation to a source file.
        
        Args:
            mutant: The mutation to apply
            mode: "inject_bug" to apply mutated code, "fix_bug" to apply original
            
        Returns:
            True if mutation was applied successfully
        """
        file_path = self.service_root / mutant.file
        
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")
        
        # Determine what to find and replace based on mode
        if mode == "inject_bug":
            find_str = mutant.original
            replace_str = mutant.mutated
        elif mode == "fix_bug":
            find_str = mutant.mutated
            replace_str = mutant.original
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'inject_bug' or 'fix_bug'")
        
        # Read file content
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        
        # Determine if this is a single-line or multi-line mutation
        is_multiline = '\n' in find_str.strip()
        
        if mutant.line is not None and not is_multiline:
            # Line-based replacement (only for single-line patterns)
            line_idx = mutant.line - 1  # Convert to 0-indexed
            
            if line_idx < 0 or line_idx >= len(lines):
                raise IndexError(f"Line {mutant.line} out of range for {file_path}")
            
            current_line = lines[line_idx].rstrip('\n\r')
            
            # Check if the expected string is in the line
            if find_str.strip() not in current_line:
                return False
            
            # Replace in the specific line
            new_line = current_line.replace(find_str.strip(), replace_str.strip())
            lines[line_idx] = new_line + '\n'
            
            new_content = ''.join(lines)
        else:
            # Whole-file replacement (for multi-line patterns, or when line is null)
            if find_str not in content:
                return False
            
            new_content = content.replace(find_str, replace_str, 1)
        
        # Write modified content
        file_path.write_text(new_content, encoding="utf-8")
        return True
