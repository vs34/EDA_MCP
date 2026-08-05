import unittest
import os
import shutil
import tempfile
from workboard_client import WorkBoardClient

class MockSession:
    """Mock RemoteSession for offline WorkBoard unit testing."""
    def __init__(self):
        self.files = {
            "~/Desktop/eldo/inv.cir": ".param W=1u L=65n\nM0 vout vin vdd vdd psvtgp\n",
            "/tmp/wave.tr0": b"\x00\x01\x02\x03\x04WAVEFORM_BINARY_DATA\x00\x01"
        }

    def read_file_bytes(self, remote_path, timeout=30.0):
        val = self.files.get(remote_path)
        if val is None:
            raise FileNotFoundError(f"Remote file not found: {remote_path}")
        if isinstance(val, str):
            return val.encode('utf-8')
        return val

    def write_file_bytes(self, remote_path, content, timeout=30.0):
        self.files[remote_path] = content

class TestWorkBoardClient(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_workboard_")
        self.session = MockSession()
        self.client = WorkBoardClient(session=self.session, base_workboard_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialize(self):
        res = self.client.initialize(workboard_name="inv_tb")
        self.assertIn("Initialized WorkBoard 'inv_tb'", res)
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        self.assertTrue(os.path.exists(os.path.join(wb_dir, ".git")))
        self.assertTrue(os.path.exists(os.path.join(wb_dir, ".workboard.json")))

    def test_add_and_status(self):
        res_add = self.client.add(
            remote_path="~/Desktop/eldo/inv.cir",
            local_path="netlists/inv.cir",
            workboard_name="inv_tb"
        )
        self.assertIn("Successfully added", res_add)
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        local_file = os.path.join(wb_dir, "netlists/inv.cir")
        self.assertTrue(os.path.exists(local_file))

        res_status = self.client.status(workboard_name="inv_tb")
        self.assertIn("netlists/inv.cir -> ~/Desktop/eldo/inv.cir [IN_SYNC]", res_status)

    def test_binary_file_transfer(self):
        res_add = self.client.add(
            remote_path="/tmp/wave.tr0",
            local_path="results/wave.tr0",
            workboard_name="inv_tb"
        )
        self.assertIn("Successfully added", res_add)
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        local_file = os.path.join(wb_dir, "results/wave.tr0")
        with open(local_file, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"\x00\x01\x02\x03\x04WAVEFORM_BINARY_DATA\x00\x01")

if __name__ == "__main__":
    unittest.main()
