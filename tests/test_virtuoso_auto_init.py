import unittest
from unittest.mock import MagicMock
from virtuoso_client import VirtuosoClient

class TestVirtuosoAutoInit(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.connect.return_value = None
        self.mock_session.execute_command.return_value = (0, "Success", "")
        self.mock_session.read_file.return_value = "RESULT: 5"
        self.client = VirtuosoClient(session=self.mock_session)

    def test_assisted_run_auto_initializes_when_workdir_is_none(self):
        self.assertIsNone(self.client.workdir)
        
        # Calling assisted_run without calling initialize() first
        res = self.client.assisted_run(skill_code="plus(2 3)", work_dir="~/Desktop/cmos65")
        
        # Verify self.workdir is now set to ~/Desktop/cmos65
        self.assertEqual(self.client.workdir, "~/Desktop/cmos65")
        self.assertEqual(res, "RESULT: 5")
        
        # Verify connect and cd command execution occurred
        self.mock_session.connect.assert_called()

    def test_assisted_run_uses_existing_workdir_if_already_initialized(self):
        self.client.initialize(work_dir="~/Desktop/custom_dir")
        self.assertEqual(self.client.workdir, "~/Desktop/custom_dir")
        
        res = self.client.assisted_run(skill_code="plus(3 4)")
        self.assertEqual(self.client.workdir, "~/Desktop/custom_dir")
        self.assertEqual(res, "RESULT: 5")

if __name__ == "__main__":
    unittest.main()
