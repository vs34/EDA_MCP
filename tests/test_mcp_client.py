import asyncio
import os
import sys
import uuid
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_mcp_client_test():
    # Get the absolute path to server.py in the same directory structure
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(base_dir, "server.py")
    
    print(f"Target Server Script: {server_script}")
    if not os.path.exists(server_script):
        print(f"ERROR: server.py not found at {server_script}", file=sys.stderr)
        sys.exit(1)

    # Configure server execution parameters (launches server.py via stdio)
    server_params = StdioServerParameters(
        command="python3",
        args=[server_script]
    )

    print("Launching MCP server in stdio client mode...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Initialize the session with the server
                print("Initializing session...")
                await session.initialize()
                print("Initialization successful!")

                # 2. List tools exposed by the server
                print("\nListing available tools...")
                response = await session.list_tools()
                print(f"Found {len(response.tools)} tools:")
                for tool in response.tools:
                    print(f" - Tool Name: {tool.name}")
                    print(f"   Description: {tool.description.strip().splitlines()[0] if tool.description else 'No description'}")
                    print(f"   Parameters: {list(tool.inputSchema.get('properties', {}).keys())}")

                # 3. Test calling 'remote_control' with action='run_command'
                print("\nCalling 'remote_control' with action='run_command', command='whoami'...")
                tool_call_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "run_command", "command": "whoami"}
                )
                
                print("Tool Response:")
                for content in tool_call_response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                    else:
                        print(content)


                print("\nCalling 'remote_control' with action='run_command', command='pwd'...")
                tool_call_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "run_command", "command": "pwd"}
                )
                
                print("Tool Response:")
                for content in tool_call_response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                    else:
                        print(content)

                print("\nCalling 'remote_control' with action='run_command', command='cd .. && pwd'...")
                tool_call_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "run_command", "command": "cd .. && pwd"}
                )
                
                print("Tool Response:")
                for content in tool_call_response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                    else:
                        print(content)

                # 4. Test remote_control with write_file and read_file actions
                unique_id = uuid.uuid4().hex
                temp_file_path = f"/tmp/eda_mcp_test_{unique_id}.txt"
                test_content = f"Hello from Antigravity test run {unique_id}"
                
                print(f"\nVerifying file does not already exist: {temp_file_path}")
                check_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "run_command", "command": f"test -e {temp_file_path}"}
                )
                check_output = ""
                for content in check_response.content:
                    if hasattr(content, "text"):
                        check_output += content.text
                    else:
                        check_output += str(content)
                if "Exit Status: 0" in check_output:
                    raise RuntimeError(f"Safety violation: Test file {temp_file_path} already exists on remote!")

                print(f"\nCalling 'remote_control' with action='write_file' to path={temp_file_path}...")
                write_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "write_file", "path": temp_file_path, "content": test_content}
                )
                print("Write Response:")
                for content in write_response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                    else:
                        print(content)

                print(f"\nCalling 'remote_control' with action='read_file' from path={temp_file_path}...")
                read_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "read_file", "path": temp_file_path}
                )
                print("Read Response:")
                read_text = ""
                for content in read_response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                        read_text += content.text
                    else:
                        print(content)
                        read_text += str(content)

                if test_content not in read_text:
                    raise AssertionError(f"Expected content '{test_content}' was not found in read response: '{read_text}'")
                print("Verification successful: written content matches read content!")

                print(f"\nCleaning up: deleting remote file {temp_file_path} via remote_control...")
                delete_response = await session.call_tool(
                    name="remote_control",
                    arguments={"action": "run_command", "command": f"rm {temp_file_path}"}
                )
                print("Delete Response:")
                delete_output = ""
                for content in delete_response.content:
                    if hasattr(content, "text"):
                        print(content.text)
                        delete_output += content.text
                    else:
                        print(content)
                        delete_output += str(content)
                
                if "Exit Status: 0" not in delete_output:
                    raise RuntimeError(f"Failed to delete test file {temp_file_path}")
                print("Cleanup successful!")

                # 5. Test calling 'workboard' with action='status'
                print("\nCalling 'workboard' with action='status'...")
                wb_response = await session.call_tool(
                    name="workboard",
                    arguments={"action": "status", "workboard_name": "default"}
                )
                wb_text = ""
                for content in wb_response.content:
                    if hasattr(content, "text"):
                        wb_text += content.text
                    else:
                        wb_text += str(content)
                print(f"WorkBoard Status Response:\n{wb_text}")
                if "WorkBoard Name: default" not in wb_text:
                    raise AssertionError(f"WorkBoard tool call failed: {wb_text}")
                print("WorkBoard tool verification successful!")
    except Exception as e:
        print(f"\nERROR: MCP client test failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Ensure correct asyncio event loop policy on macOS if needed, but standard run is fine
    asyncio.run(run_mcp_client_test())
