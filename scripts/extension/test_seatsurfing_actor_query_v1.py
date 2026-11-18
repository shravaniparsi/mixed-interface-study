import unittest
from capture_seatsurfing_actor_database_v1 import actor_query


class ActorQuery(unittest.TestCase):
    def test_read_only_single_snapshot_and_original_relations(self):
        query = actor_query(*['00000000-0000-4000-8000-000000000001'] * 3)
        self.assertTrue(query.startswith('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;'))
        self.assertTrue(query.endswith('COMMIT;\n'))
        for table in ['users', 'sessions', 'refresh_tokens', 'user_roles', 'roles', 'role_permissions']:
            self.assertIn('FROM ' + table, query)
        for mutation in ['INSERT ', 'UPDATE ', 'DELETE ', 'CREATE ', 'ALTER ']:
            self.assertNotIn(mutation, query)

    def test_selectors_cannot_inject_sql(self):
        valid = '00000000-0000-4000-8000-000000000001'
        for slot in range(3):
            args = [valid] * 3
            args[slot] = "x'; DELETE FROM users; --"
            with self.assertRaises(ValueError): actor_query(*args)


if __name__ == '__main__': unittest.main()
