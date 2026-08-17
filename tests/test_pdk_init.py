import unittest
import os

class TestPdkInitSpec(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.mcp_setup_path = os.path.join(self.base_dir, "server_side", "virtuoso", "MCP_setup.il")
        self.skill_guide_path = os.path.join(self.base_dir, "context", "designer", "virtuoso_skill_guide.md")

    def test_mcp_setup_contains_pdk_helpers(self):
        self.assertTrue(os.path.exists(self.mcp_setup_path), f"File missing: {self.mcp_setup_path}")
        with open(self.mcp_setup_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for procedure definitions
        self.assertIn("procedure( initPdkLibrary(libName)", content)
        self.assertIn("procedure( initMosTransistor(inst wMicrons lMicrons)", content)

        # Check for PDK auto-init and senseChoices fallback
        self.assertIn('initPdkLibrary("cmos065")', content)
        self.assertIn("senseChoices = list(", content)
        self.assertIn("DK_CBmos('w)", content)

    def test_skill_guide_uses_init_mos_transistor(self):
        self.assertTrue(os.path.exists(self.skill_guide_path), f"File missing: {self.skill_guide_path}")
        with open(self.skill_guide_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that initMosTransistor is used in Template A
        self.assertIn('initMosTransistor(pInst "2.0" "0.065")', content)
        self.assertIn('initMosTransistor(nInst "1.0" "0.065")', content)
        # Verify the warning comment discouraging raw float meters is present
        self.assertIn("Do NOT assign raw float meters", content)

if __name__ == "__main__":
    unittest.main()
