import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_session_isolation_test():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(base_dir, "server.py")
    
    server_params = StdioServerParameters(
        command="python3",
        args=[server_script]
    )

    print("Launching MCP server to test session isolation...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Initialization successful!")

            # Check working directory of remote_control
            rc_res = await session.call_tool(
                name="remote_control",
                arguments={"action": "run_command", "command": "pwd"}
            )
            rc_pwd = rc_res.content[0].text if rc_res.content else ""
            print(f"remote_control pwd: {rc_pwd.strip()}")

            # Change directory in remote_control session to /tmp
            await session.call_tool(
                name="remote_control",
                arguments={"action": "run_command", "command": "cd /tmp"}
            )
            
            rc_res_after = await session.call_tool(
                name="remote_control",
                arguments={"action": "run_command", "command": "pwd"}
            )
            rc_pwd_after = rc_res_after.content[0].text if rc_res_after.content else ""
            print(f"remote_control pwd after cd /tmp: {rc_pwd_after.strip()}")
            assert "/tmp" in rc_pwd_after, "remote_control failed to change directory to /tmp"

            # Execute virtuoso terminal command in a different directory (~/Desktop/cmos65)
            v_res = await session.call_tool(
                name="virtuoso",
                arguments={"action": "run_terminal_command", "command": "pwd", "work_dir": "~/Desktop/cmos65"}
            )
            print(f"virtuoso output: {v_res.content[0].text.strip() if v_res.content else ''}")

            # Verify remote_control is STILL in /tmp (proving sessions are isolated)
            rc_verify = await session.call_tool(
                name="remote_control",
                arguments={"action": "run_command", "command": "pwd"}
            )
            rc_verify_pwd = rc_verify.content[0].text if rc_verify.content else ""
            print(f"remote_control pwd after virtuoso init: {rc_verify_pwd.strip()}")

            if "/tmp" in rc_verify_pwd:
                print("SUCCESS: Sessions are fully isolated! Changing state in virtuoso session did not affect remote_control session.")
            else:
                raise AssertionError("Session isolation failed! State bled across sessions.")

if __name__ == "__main__":
    asyncio.run(run_session_isolation_test())
