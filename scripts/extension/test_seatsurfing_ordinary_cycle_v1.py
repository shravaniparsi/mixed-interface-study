import unittest
from unittest.mock import Mock
from run_seatsurfing_ordinary_cycle_v1 import execute_stages

METHODS=['producer_stage','capture_checkpoint','warm_edit','restore_native_editor',
         'restored_native_edit','restore_api_inputs','restored_api_edit','compare_retained_requests',
         'stop_and_check_request_budgets','verify_write_transport']

class Cycle(unittest.TestCase):
    def coordinator(self):
        result=Mock()
        result.phase='ordinary_write_transport_verified_parent_gates_pending'
        return result
    def test_fixed_order_and_bracketing_inventory(self):
        coordinator=self.coordinator();inventory=Mock(return_value={'fixture':'private'});retain=Mock()
        completed=execute_stages(coordinator,'private-key',inventory,retain)
        self.assertEqual([call[0] for call in coordinator.method_calls],METHODS)
        self.assertEqual(len(completed),10);self.assertEqual(inventory.call_count,20)
        coordinator.capture_checkpoint.assert_called_once_with(private_key='private-key')
        coordinator.restore_api_inputs.assert_called_once_with(private_key='private-key')
        self.assertEqual([c.args[0] for c in retain.call_args_list],
                         [stage+suffix for stage in completed for suffix in ['-before','-after']])
    def test_each_failed_gate_stops_without_retry(self):
        for index,name in enumerate(METHODS):
            with self.subTest(stage=name):
                coordinator=self.coordinator();getattr(coordinator,name).side_effect=RuntimeError('gate unavailable')
                with self.assertRaisesRegex(RuntimeError,'gate unavailable'):
                    execute_stages(coordinator,'private-key',Mock(return_value={}),Mock())
                self.assertEqual([call[0] for call in coordinator.method_calls],METHODS[:index+1])
    def test_inventory_failure_prevents_next_action(self):
        coordinator=self.coordinator();inventory=Mock(side_effect=[{},ValueError('foreign client')])
        with self.assertRaisesRegex(ValueError,'foreign client'):execute_stages(coordinator,'key',inventory,Mock())
        self.assertEqual([call[0] for call in coordinator.method_calls],METHODS[:1])
    def test_wrong_terminal_phase_is_not_success(self):
        coordinator=self.coordinator();coordinator.phase='failed'
        with self.assertRaisesRegex(RuntimeError,'final comparison gate'):
            execute_stages(coordinator,'key',Mock(return_value={}),Mock())

if __name__=='__main__':unittest.main()
