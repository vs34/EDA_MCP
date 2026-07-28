import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_virtuoso_test():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(base_dir, "server.py")
    
    print(f"Target Server Script: {server_script}")
    if not os.path.exists(server_script):
        print(f"ERROR: server.py not found at {server_script}", file=sys.stderr)
        sys.exit(1)

    server_params = StdioServerParameters(
        command="python3",
        args=[server_script]
    )

    print("Connecting to EDA_MCP server...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("Initializing session...")
                await session.initialize()
                print("Initialization successful!")

                print("\n==========================================")
                print("Calling 'virtuoso' tool (action='initialize')...")
                print("==========================================")
                
                response = await session.call_tool(
                    name="virtuoso",
                    arguments={
                        "action": "initialize",
                        "work_dir": "~/Desktop/cmos65"
                    }
                )
                
                print("\n--- Virtuoso Initialization Output ---")
                for content in response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                    else:
                        print(content)
                print("--------------------------------------")

                print("\nTesting virtuoso action='start_interactive'...")
                interact_start = await session.call_tool(
                    name="virtuoso",
                    arguments={"action": "start_interactive", "work_dir": "~/Desktop/cmos65"}
                )
                print(f"Start Interactive Response:\n{interact_start.content[0].text if interact_start.content else ''}")

                print("\nTesting virtuoso action='run_interactive' with SKILL command...")
                interact_run = await session.call_tool(
                    name="virtuoso",
                    arguments={"action": "run_interactive", "command": "plus(2 3)"}
                )
                print(f"Run Interactive Response:\n{interact_run.content[0].text if interact_run.content else ''}")

                print("\nTesting virtuoso action='stop_interactive'...")
                interact_stop = await session.call_tool(
                    name="virtuoso",
                    arguments={"action": "stop_interactive"}
                )
                print(f"Stop Interactive Response:\n{interact_stop.content[0].text if interact_stop.content else ''}")

    except Exception as e:
        print(f"\nERROR: Virtuoso test failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_virtuoso_test())
