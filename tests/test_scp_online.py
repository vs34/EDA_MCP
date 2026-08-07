import time
import os
import sys
import logging

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scp_client import SCPClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_scp_online")

def run_online_scp_test():
    print("=" * 70)
    print("🚀 STARTING ONLINE SCP CLIENT INTEGRATION & PERFORMANCE TEST")
    print("=" * 70)

    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config_scp.json")
    print(f"📄 Config Path: {config_path}")

    try:
        client = SCPClient(config_path=config_path)
        print(f"✅ SCPClient Initialized - Host: '{client.host}', User: '{client.user}', Port: {client.port}, SSH Config: '{client.ssh_config_path}'")
        print(f"🛠️ Base SCP Command: {' '.join(client._get_base_scp_cmd())}\n")
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # --- TEST 1: DOWNLOAD FILE ---
    remote_file = "/home/vaibhav22555/Desktop/eldo/test1.cir"
    local_target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp", "test1_scp_download.cir")
    
    print("-" * 70)
    print(f"📥 TEST 1: Downloading Remote File")
    print(f"   Remote Source: {remote_file}")
    print(f"   Local Target:  {local_target}")
    
    t0 = time.time()
    try:
        res = client.download(remote_file, local_target, timeout=30.0)
        t_download = time.time() - t0
        print(f"   Status: SUCCESS in {t_download:.3f} seconds")
        print(f"   Message: {res}")

        if os.path.exists(local_target):
            file_size = os.path.getsize(local_target)
            print(f"   Downloaded File Size: {file_size} bytes")
            with open(local_target, "r", encoding="utf-8", errors="replace") as f:
                content_preview = f.read(300)
            print(f"   Content Preview:\n{'-'*40}\n{content_preview.strip()}\n{'-'*40}")
        else:
            print("   ⚠️ Error: Target file was not found on local disk after download!")
    except Exception as e:
        t_download = time.time() - t0
        print(f"   ❌ DOWNLOAD FAILED after {t_download:.3f} seconds: {e}")

    # --- TEST 2: UPLOAD FILE ---
    local_sample = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp", "test1_scp_upload_sample.txt")
    remote_upload_dest = "/home/vaibhav22555/Desktop/eldo/test1_mcp_upload_test.txt"

    os.makedirs(os.path.dirname(local_sample), exist_ok=True)
    with open(local_sample, "w", encoding="utf-8") as f:
        f.write(f"* EDA_MCP Online SCP Performance Test Sample\n* Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n.PARAM R1=1k C1=10p\n.END\n")

    print("\n" + "-" * 70)
    print(f"📤 TEST 2: Uploading Sample File")
    print(f"   Local Source:  {local_sample}")
    print(f"   Remote Target: {remote_upload_dest}")

    t0 = time.time()
    try:
        res = client.upload(local_sample, remote_upload_dest, timeout=30.0)
        t_upload = time.time() - t0
        print(f"   Status: SUCCESS in {t_upload:.3f} seconds")
        print(f"   Message: {res}")
    except Exception as e:
        t_upload = time.time() - t0
        print(f"   ❌ UPLOAD FAILED after {t_upload:.3f} seconds: {e}")

    # --- TEST 3: READ BYTES ---
    print("\n" + "-" * 70)
    print(f"📖 TEST 3: Reading Remote Bytes (Memory Transfer)")
    print(f"   Remote Source: {remote_file}")
    t0 = time.time()
    try:
        raw_bytes = client.read_bytes(remote_file, timeout=30.0)
        t_bytes = time.time() - t0
        print(f"   Status: SUCCESS in {t_bytes:.3f} seconds")
        print(f"   Raw Bytes Received: {len(raw_bytes)} bytes")
    except Exception as e:
        t_bytes = time.time() - t0
        print(f"   ❌ READ BYTES FAILED after {t_bytes:.3f} seconds: {e}")

    print("=" * 70)
    print("📊 TEST SUMMARY & PERFORMANCE RESULTS")
    print("=" * 70)

if __name__ == "__main__":
    run_online_scp_test()
