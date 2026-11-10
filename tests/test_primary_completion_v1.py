"""An initial report alone cannot pass completion when repeats were selected."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verify_primary_results_v1 as module


class CompletionTests(unittest.TestCase):
    def test_missing_selected_second_phase_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(module, 'ROOT', Path(folder)), patch.object(module, 'units', return_value=[{'batch_id': 'selected'}]):
            with self.assertRaisesRegex(ValueError, 'second repetitions'):
                module.verify()

    def test_missing_selected_third_phase_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'manifests').mkdir()
            (root / 'manifests/primary-repeat2-runtime-v1.json').write_text('{}')
            with patch.object(module, 'ROOT', root), patch.object(module, 'units', return_value=[{'batch_id': 'selected'}]):
                with self.assertRaisesRegex(ValueError, 'third repetitions'):
                    module.verify()


if __name__ == '__main__':
    unittest.main()
