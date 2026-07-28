import sys
import os

# Add parent directory to sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from ssh_client import RemoteSession

def main():
    print("==========================================")
    print("Testing RemoteSession.execute_interactive_stream()")
    print("==========================================")
    sys.stdout.flush()

    session = RemoteSession(config_path="config/config_remote_control.json")
    session.connect()

    print("\n1. Starting interactive Python REPL on remote host...")
    sys.stdout.flush()
    code, stdout, stderr = session.execute_interactive_stream("python -i", prompt_regex=r">>>\s*$", timeout=5.0)
    print(f"[Initial REPL Prompt Output]:\n{stdout.strip()}")
    sys.stdout.flush()

    print("\n2. Executing python function definition in REPL...")
    sys.stdout.flush()
    c, out, err = session.execute_interactive_stream("def add_numbers(a, b): return a + b", prompt_regex=r"(>>>|\.\.\.)\s*$", timeout=5.0)
    print(f"[Function Line Output]:\n{out.strip()}")
    sys.stdout.flush()

    # Extra newline to finish block in Python REPL
    c, out, err = session.execute_interactive_stream("", prompt_regex=r">>>\s*$", timeout=5.0)
    print(f"[Finalized Block Output]:\n{out.strip()}")
    sys.stdout.flush()

    print("\n3. Executing function call: add_numbers(15, 27)...")
    sys.stdout.flush()
    c, out, err = session.execute_interactive_stream("print add_numbers(15, 27)", prompt_regex=r">>>\s*$", timeout=5.0)
    print(f"[Function Call Output]:\n{out.strip()}")
    sys.stdout.flush()

    print("\n4. Executing a loop in REPL...")
    sys.stdout.flush()
    c, out, err = session.execute_interactive_stream("for i in range(3): print 'Count:', i", prompt_regex=r"(>>>|\.\.\.)\s*$", timeout=5.0)
    print(f"[Loop Line Output]:\n{out.strip()}")
    sys.stdout.flush()

    c, out, err = session.execute_interactive_stream("", prompt_regex=r">>>\s*$", timeout=5.0)
    print(f"[Finalized Loop Output]:\n{out.strip()}")
    sys.stdout.flush()

    print("\n5. Exiting interactive Python REPL...")
    sys.stdout.flush()
    c, out, err = session.execute_interactive_stream("exit()", prompt_regex=r"(%|>|\$)\s*$", timeout=5.0)
    print(f"[Exit REPL Output]:\n{out.strip()}")
    sys.stdout.flush()

    session.close()
    print("\n==========================================")
    print("Test finished successfully!")
    print("==========================================")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
