import unittest
from unittest.mock import MagicMock
from eldo_client import EldoClient

class TestEldoClientRunScript(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.connect.return_value = None
        self.mock_session.execute_command.return_value = (0, "Eldo simulation completed successfully.", "")
        self.client = EldoClient(session=self.mock_session)

    def test_run_script_requires_non_empty_script_path(self):
        res = self.client.run_script(script_path="")
        self.assertIn("Error: Netlist script path is required", res)

    def test_run_script_success(self):
        res = self.client.run_script(script_path="aoi32_tb.cir", work_dir="~/Desktop/eldo")
        self.assertIn("[Eldo Batch Simulation (Exit code 0)]", res)
        self.assertIn("Eldo simulation completed successfully.", res)
        self.assertEqual(self.client.workdir, "~/Desktop/eldo")

    def test_run_script_failure_auto_inspects_error_log(self):
        # Simulate non-zero exit code
        self.mock_session.execute_command.side_effect = [
            (0, "", ""), # mkdir -p & cd
            (1, "Eldo simulation failed with errors", ""), # eldo run
            (0, "sim_error.errm.log", ""), # ls -t *.errm.log
        ]
        self.mock_session.read_file.return_value = "ERROR 104: Invalid subcircuit syntax on line 12"

        res = self.client.run_script(script_path="broken_tb.cir")
        self.assertIn("Exit code 1", res)
        self.assertIn("--- ERROR LOG (sim_error.errm.log) ---", res)
        self.assertIn("ERROR 104: Invalid subcircuit syntax on line 12", res)

if __name__ == "__main__":
    unittest.main()
