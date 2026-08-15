import unittest
from unittest.mock import patch, MagicMock
import subprocess
from issue_reporter import IssueReporter

class TestIssueReporter(unittest.TestCase):

    def test_format_issue_body(self):
        body = IssueReporter.format_issue_body(
            body="## Problem\nTimeout waiting for output file lock",
            agent_name="Antigravity",
            agent_model="gemini-3.6-flash",
            session_id="test-session-123",
            log_file="eda_mcp_20260815_120000_999.log"
        )

        self.assertIn("> **Reported by Agent:** Antigravity (`gemini-3.6-flash`) (Chip Design Consumer)", body)
        self.assertIn("> **Session ID:** `test-session-123`", body)
        self.assertIn("> **MCP Log File:** `temp/eda_mcp_20260815_120000_999.log` (created in `temp/` folder)", body)
        self.assertIn("## Problem\nTimeout waiting for output file lock", body)

    def test_format_issue_body_freeform_markdown(self):
        freeform_md = """## Feature Request: Add Spectre Netlist Parser

Please add support for parsing Cadence Spectre netlist files `.scs` directly.

### User Benefits
- Allows automated extraction of transistor device models
- Enables automated corner sweep configuration
"""
        result = IssueReporter.format_issue_body(
            body=freeform_md,
            agent_name="Antigravity",
            agent_model="gemini-3.6-flash",
            session_id="test-session-456",
            log_file="eda_mcp_20260815_120000_999.log"
        )

        self.assertIn("> **Reported by Agent:** Antigravity (`gemini-3.6-flash`) (Chip Design Consumer)", result)
        self.assertIn("> **Session ID:** `test-session-456`", result)
        self.assertIn("## Feature Request: Add Spectre Netlist Parser", result)
        self.assertIn("- Allows automated extraction of transistor device models", result)

    @patch("subprocess.run")
    def test_ensure_label_exists_creates_missing_label(self, mock_run):
        # Mock gh label list output without 'Claude'
        mock_run.side_effect = [
            MagicMock(stdout="bug\tdescription\t#d73a4a\nAntigravity\tdescription\t#5319e7\n", returncode=0), # list
            MagicMock(stdout="", returncode=0) # create
        ]

        created = IssueReporter.ensure_label_exists("Claude")
        self.assertTrue(created)
        self.assertEqual(mock_run.call_count, 2)
        
        # Verify second call was gh label create Claude
        create_args = mock_run.call_args_list[1][0][0]
        self.assertEqual(create_args[:4], ["gh", "label", "create", "Claude"])

    @patch.object(IssueReporter, "ensure_label_exists", return_value=True)
    @patch("subprocess.run")
    def test_create_issue_success(self, mock_run, mock_ensure_label):
        mock_run.return_value = MagicMock(
            stdout="https://github.com/vs34/EDA_MCP/issues/42\n",
            returncode=0
        )

        result = IssueReporter.create_issue(
            title="Eldo timeout on file lock",
            body="## Bug Details\nEldo script timed out after 600s",
            label="bug",
            agent_model="gemini-3.6-flash",
            session_id="test-session-123",
            agent_name="Claude"
        )

        self.assertIn("Successfully created GitHub issue: https://github.com/vs34/EDA_MCP/issues/42", result)
        mock_ensure_label.assert_called_once_with("Claude", cwd=None)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertEqual(cmd[0], "gh")
        self.assertEqual(cmd[1], "issue")
        self.assertEqual(cmd[2], "create")
        self.assertIn("--title", cmd)
        self.assertIn("Eldo timeout on file lock", cmd)
        self.assertIn("--label", cmd)
        self.assertIn("bug", cmd)
        self.assertIn("Claude", cmd)

if __name__ == "__main__":
    unittest.main()
