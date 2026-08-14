import os
import subprocess
import shlex
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("EDA_MCP.IssueReporter")

class IssueReporter:
    """
    Helper utility for Agent A (Chip Design Consumer) to report tool issues, 
    bugs, or feature requests to GitHub without needing context of EDA_MCP code.
    """

    @staticmethod
    def format_issue_body(
        agent_name: str,
        session_id: str,
        domain_intent: str,
        tool_name: str,
        tool_action: str,
        error_message: str,
        expected_behavior: str = ""
    ) -> str:
        """Formats a structured GitHub issue body tailored for Agent B consumption."""
        body_parts = [
            f"> 🤖 **Reported by Agent:** {agent_name} (Chip Design Consumer)",
            f"> 🆔 **Session ID:** `{session_id}`",
            "---",
            "",
            "### 🎨 Chip Design Intent",
            domain_intent.strip() or "No domain intent provided.",
            "",
            "### 🛠️ MCP Tool Call Executed",
            f"- **Tool:** `{tool_name}`",
            f"- **Action:** `{tool_action}`",
            "",
            "### ❌ Observed Tool Error / Output",
            "```text",
            error_message.strip() or "No error output provided.",
            "```"
        ]

        if expected_behavior.strip():
            body_parts.extend([
                "",
                "### 🎯 Expected Behavior / Requirement",
                expected_behavior.strip()
            ])

        return "\n".join(body_parts)

    @classmethod
    def create_issue(
        cls,
        title: str,
        agent_name: str = "Antigravity",
        session_id: str = "unknown",
        domain_intent: str = "",
        tool_name: str = "",
        tool_action: str = "",
        error_message: str = "",
        expected_behavior: str = "",
        label: str = "bug",
        cwd: Optional[str] = None
    ) -> str:
        """
        Creates a GitHub issue via the gh CLI tool.
        
        Returns:
            The URL of the created issue or an error message.
        """
        body = cls.format_issue_body(
            agent_name=agent_name,
            session_id=session_id,
            domain_intent=domain_intent,
            tool_name=tool_name,
            tool_action=tool_action,
            error_message=error_message,
            expected_behavior=expected_behavior
        )

        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--label", label,
            "--body", body
        ]

        logger.info(f"Creating GitHub issue: title={title!r}, label={label!r}, agent={agent_name!r}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=cwd
            )
            issue_url = result.stdout.strip()
            logger.info(f"Successfully created GitHub issue: {issue_url}")
            return f"Successfully created GitHub issue: {issue_url}"
        except FileNotFoundError:
            err_msg = "Error: 'gh' CLI tool is not installed or not found in PATH."
            logger.error(err_msg)
            return err_msg
        except subprocess.CalledProcessError as e:
            err_msg = f"Error creating GitHub issue via gh CLI (exit code {e.returncode}):\n{e.stderr.strip()}"
            logger.error(err_msg)
            return err_msg
