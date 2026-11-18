import sys
import unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'extension'))
from dependency_queue_v1 import new_queue, transition


def entry(path):
    return dict(path=path, blob='a' * 40, reason='Explicit import')


class DependencyQueueTests(unittest.TestCase):
    def start(self, cap=4):
        return new_queue('owner/repo', 'b' * 40, [entry('z'), entry('a')], cap)

    def finish(self, q, path, children=()):
        q = transition(q, 'publish', freeze='c' * 40)
        q = transition(q, 'observe', path=path, outcome='collected', sha256='d' * 64)
        q = transition(q, 'discover', parent=path, entries=[entry(c) for c in children])
        return transition(q, 'seal', discovery_complete=True)

    def test_breadth_before_child_even_when_child_sorts_first(self):
        q = transition(self.start(), 'schedule', limit=1)
        self.assertEqual(q['batches'][-1]['paths'], ['a'])
        q = self.finish(q, 'a', ['0-child'])
        q = transition(q, 'schedule', limit=3)
        self.assertEqual(q['batches'][-1]['paths'], ['z'])
        q = self.finish(q, 'z', ['0-child'])
        q = transition(q, 'schedule', limit=3)
        self.assertEqual(q['batches'][-1]['paths'], ['0-child'])
        self.assertEqual(len(q['nodes']['0-child']['edges']), 2)

    def test_freeze_and_terminal_batch_required(self):
        q = transition(self.start(), 'schedule', limit=2)
        before = deepcopy(q)
        for action, args in [('observe', dict(path='a', outcome='unavailable')),
                             ('seal', dict(discovery_complete=True)),
                             ('schedule', dict(limit=1))]:
            with self.assertRaises(ValueError):
                transition(q, action, **args)
            self.assertEqual(q, before)

    def test_failure_consumes_cap_and_cannot_retry(self):
        q = transition(self.start(cap=1), 'schedule', limit=5)
        q = transition(q, 'publish', freeze='c' * 40)
        q = transition(q, 'observe', path='a', outcome='unavailable')
        with self.assertRaises(ValueError):
            transition(q, 'observe', path='a', outcome='unavailable')
        q = transition(q, 'seal', discovery_complete=True)
        with self.assertRaises(ValueError):
            transition(q, 'schedule', limit=1)
        self.assertEqual(q['nodes']['z']['status'], 'pending')

    def test_conflicting_discovery_is_atomic(self):
        q = transition(self.start(), 'schedule', limit=1)
        q = transition(q, 'publish', freeze='c' * 40)
        q = transition(q, 'observe', path='a', outcome='collected', sha256='d' * 64)
        before = deepcopy(q)
        with self.assertRaises(ValueError):
            transition(q, 'discover', parent='a', entries=[entry('child'), dict(entry('z'), blob='e'*40)])
        self.assertEqual(q, before)

if __name__ == '__main__':
    unittest.main()
