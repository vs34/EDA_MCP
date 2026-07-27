import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_eldo_test():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(base_dir, "server.py")
    
    server_params = StdioServerParameters(
        command="python3",
        args=[server_script]
    )

    print("Launching MCP server to test Eldo tool integration...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Initialization successful!")

            # 1. List tools and verify 'eldo' tool presence
            tools_resp = await session.list_tools()
            tool_names = [t.name for t in tools_resp.tools]
            print(f"Exposed Tools: {tool_names}")
            assert "eldo" in tool_names, "'eldo' tool was not found in server tools!"

            # 2. Test action='initialize'
            print("\nTesting eldo action='initialize'...")
            init_res = await session.call_tool(
                name="eldo",
                arguments={"action": "initialize", "work_dir": "~"}
            )
            init_text = init_res.content[0].text if init_res.content else ""
            print(f"Initialize Response: {init_text.strip()}")

            # 3. Test action='run'
            print("\nTesting eldo action='run' with command='which eldo'...")
            run_res = await session.call_tool(
                name="eldo",
                arguments={"action": "run", "command": "echo $PATH"}
            )
            run_text = run_res.content[0].text if run_res.content else ""
            print(f"Run Response: {run_text.strip()}")

            # 4. Test action='exit'
            print("\nTesting eldo action='exit'...")
            exit_res = await session.call_tool(
                name="eldo",
                arguments={"action": "exit"}
            )
            exit_text = exit_res.content[0].text if exit_res.content else ""
            print(f"Exit Response: {exit_text.strip()}")
            print("\nEldo Tool Verification Successful!")

if __name__ == "__main__":
    asyncio.run(run_eldo_test())
