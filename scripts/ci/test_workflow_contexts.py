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
        self.assertEqual({path.name for path in paths}, {"unit.yml", "applications.yml", "petclinic_v3.yml", 'petclinic_timing_v1.yml', 'common_petclinic_v1.yml', 'common_generated_v1.yml', 'primary_diagnostics_v1.yml', 'quartz_correction_v1.yml', 'quartz_recovery_v1.yml', 'quartz_public_qualification_v1.yml', 'quartz_recovery_v2.yml', 'quartz_recovery_dispatch_v3.yml', 'production_extension_screen_v1.yml', 'production_extension_screen_v2.yml', 'linkding_extension_controls_v1.yml', 'linkding_extension_controls_v2.yml', 'linkding_extension_controls_v3.yml', 'linkding_extension_probes_v1.yml', 'linkding_extension_probes_v2.yml', 'linkding_cases_v1.yml', 'paperless_extension_controls_v1.yml', 'paperless_extension_controls_v2.yml', 'paperless_extension_probes_v1.yml', 'paperless_extension_probes_v2.yml', 'paperless_cases_v1.yml', 'grocy_extension_controls_v1.yml', 'grocy_extension_controls_v2.yml', 'grocy_extension_controls_v3.yml', 'grocy_cases_v1.yml', 'grocy_followups_v1.yml', 'memos_preference_controls_v1.yml', 'memos_preference_controls_v2.yml', 'memos_preference_controls_v3.yml', 'memos_preference_controls_v4.yml', 'memos_preference_controls_v5.yml', 'memos_memo_controls_v1.yml', 'memos_cases_v1.yml', 'vikunja_controls_v1.yml', 'vikunja_controls_v2.yml', 'vikunja_controls_v3.yml', 'vikunja_probes_v1.yml', 'vikunja_cases_v1.yml', 'vikunja_followups_v1.yml', 'gitea_controls_v1.yml', 'gitea_controls_v2.yml', 'gitea_controls_v3.yml', 'gitea_issue_controls_v1.yml', 'gitea_issue_controls_v2.yml', 'gitea_probes_v1.yml', 'gitea_cases_v1.yml', 'vikunja_task_controls_v1.yml', 'vikunja_task_controls_v2.yml', 'vikunja_task_controls_v3.yml', 'memos_followups_v1.yml', 'memos_memo_probe_v1.yml', 'memos_memo_probe_v2.yml', 'grocy_energy_v1.yml', 'grocy_extension_probes_v1.yml', 'grocy_product_controls_v1.yml', "realworld_v5.yml", "realworld_v6.yml", "realworld_identity_db.yml", "realworld_v7.yml", "realworld_v8.yml", "realworld_article_db.yml", "realworld_v9.yml", "realworld_v10.yml", "realworld_generated_v2.yml", "realworld_generated_v3.yml"})
        for path in paths:
            self.assertEqual(invalid_job_env_contexts(path.read_text()), [], path.name)


if __name__ == "__main__":
    unittest.main()
