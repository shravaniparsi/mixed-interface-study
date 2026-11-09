"""Narrow regression guard for these workflows' job-env context availability.

This is not a general YAML or GitHub expression validator. The repository uses
two-space indentation; this check covers its block-style job-level env mappings.
Reference: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability
"""
from pathlib import Path
import re
import unittest


PROJECT = Path(__file__).resolve().parents[2]
ALLOWED = {"github", "needs", "strategy", "matrix", "vars", "secrets", "inputs"}
CONTEXT = re.compile(r"\b(github|env|vars|job|jobs|steps|runner|secrets|strategy|matrix|needs|inputs)\s*(?=\.|\[)")


def invalid_job_env_contexts(text):
    invalid = []
    in_env = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.fullmatch(r"    env:\s*", line):
            in_env = True
            continue
        if in_env and len(line) - len(line.lstrip()) <= 4:
            in_env = False
        if in_env:
            for expression in re.findall(r"\$\{\{(.*?)\}\}", line):
                invalid.extend(name for name in CONTEXT.findall(expression) if name not in ALLOWED)
    return invalid


class WorkflowContextTests(unittest.TestCase):
    def test_runner_is_rejected_in_job_env_but_not_step_artifact_inputs(self):
        text = "jobs:\n  unit:\n    env:\n      BAD: ${{ runner.temp }}\n    steps:\n      - with:\n          path: ${{ runner.temp }}/artifacts\n"
        self.assertEqual(invalid_job_env_contexts(text), ["runner"])

    def test_shell_exports_and_allowed_dispatch_context_pass(self):
        text = "jobs:\n  app:\n    env:\n      SUITE: ${{ inputs.suite }}\n    steps:\n      - run: |\n          printf 'OUTPUT=%s\\n' \"$RUNNER_TEMP/evidence\" >> \"$GITHUB_ENV\"\n"
        self.assertEqual(invalid_job_env_contexts(text), [])

    def test_checked_in_workflows_do_not_use_runner_in_job_env(self):
        paths = sorted((PROJECT / ".github/workflows").glob("*.yml"))
        self.assertEqual({path.name for path in paths}, {"unit.yml", "applications.yml", "petclinic_v3.yml", "realworld_v5.yml"})
        for path in paths:
            self.assertEqual(invalid_job_env_contexts(path.read_text()), [], path.name)


if __name__ == "__main__":
    unittest.main()
