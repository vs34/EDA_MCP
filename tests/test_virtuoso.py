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

    except Exception as e:
        print(f"\nERROR: Virtuoso test failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_virtuoso_test())
