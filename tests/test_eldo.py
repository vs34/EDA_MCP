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

            # 2. Test action='initialize' with default work_dir (~/Desktop/eldo)
            print("\nTesting eldo action='initialize' (default ~/Desktop/eldo)...")
            init_res = await session.call_tool(
                name="eldo",
                arguments={"action": "initialize"}
            )
            init_text = init_res.content[0].text if init_res.content else ""
            print(f"Initialize Default Response: {init_text.strip()}")

            # 3. Test action='run_script'
            print("\nTesting eldo action='run_script' with command='test_netlist.cir'...")
            script_res = await session.call_tool(
                name="eldo",
                arguments={"action": "run_script", "command": "test_netlist.cir"}
            )
            script_text = script_res.content[0].text if script_res.content else ""
            print(f"Run Script Response: {script_text.strip()}")

            # 4. Test action='run_interactive' when no process is running
            print("\nTesting eldo action='run_interactive' without active PID...")
            interact_res = await session.call_tool(
                name="eldo",
                arguments={"action": "run_interactive", "command": "help"}
            )
            interact_text = interact_res.content[0].text if interact_res.content else ""
            print(f"Run Interactive (No PID) Response:\n{interact_text.strip()}")

            # 5. Test action='start_interactive'
            print("\nTesting eldo action='start_interactive' with netlist 'test_netlist.cir'...")
            start_res = await session.call_tool(
                name="eldo",
                arguments={"action": "start_interactive", "command": "test_netlist.cir"}
            )
            start_text = start_res.content[0].text if start_res.content else ""
            print(f"Start Interactive Response:\n{start_text.strip()}")

            # 6. Test action='stop_interactive'
            print("\nTesting eldo action='stop_interactive'...")
            stop_res = await session.call_tool(
                name="eldo",
                arguments={"action": "stop_interactive"}
            )
            stop_text = stop_res.content[0].text if stop_res.content else ""
            print(f"Stop Interactive Response:\n{stop_text.strip()}")

            # 7. Test action='read_extract'
            print("\nTesting eldo action='read_extract'...")
            extract_res = await session.call_tool(
                name="eldo",
                arguments={"action": "read_extract"}
            )
            extract_text = extract_res.content[0].text if extract_res.content else ""
            print(f"Read Extract Response: {extract_text.strip()}")
            print("\nEldo Tool Verification Successful!")

if __name__ == "__main__":
    asyncio.run(run_eldo_test())
