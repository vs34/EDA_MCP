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

            # 2. Test action='run_script'
            print("\nTesting eldo action='run_script' with command='test_netlist.cir'...")
            script_res = await session.call_tool(
                name="eldo",
                arguments={"action": "run_script", "command": "test_netlist.cir", "work_dir": "~"}
            )
            script_text = script_res.content[0].text if script_res.content else ""
            print(f"Run Script Response: {script_text.strip()}")

            # 3. Test action='run_interactive'
            print("\nTesting eldo action='run_interactive' with command='echo $PATH'...")
            interact_res = await session.call_tool(
                name="eldo",
                arguments={"action": "run_interactive", "command": "echo $PATH", "work_dir": "~"}
            )
            interact_text = interact_res.content[0].text if interact_res.content else ""
            print(f"Run Interactive Response: {interact_text.strip()}")
            print("\nEldo Tool Verification Successful!")

if __name__ == "__main__":
    asyncio.run(run_eldo_test())
