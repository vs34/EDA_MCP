import time
import os
import sys
import logging

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workboard_client import WorkBoardClient

def run_workboard_online_test():
    print("=" * 70)
    print("🚀 STARTING WORKBOARD ONLINE CLIENT INTEGRATION TEST")
    print("=" * 70)

    base_wb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workboard")
    wb_client = WorkBoardClient(base_workboard_dir=base_wb_dir)

    wb_name = "test1_tb"
    remote_file = "/home/vaibhav22555/Desktop/eldo/test1.cir"
    local_file = "test1.cir"

    # 1. Initialize
    print("\n1️⃣ ACTION: initialize")
    res = wb_client.initialize(workboard_name=wb_name)
    print(res)

    # 2. Add
    print("\n2️⃣ ACTION: add")
    t0 = time.time()
    res = wb_client.add(remote_path=remote_file, local_path=local_file, workboard_name=wb_name)
    t_add = time.time() - t0
    print(f"Time taken: {t_add:.3f}s")
    print(res)

    # 3. Status
    print("\n3️⃣ ACTION: status")
    res = wb_client.status(workboard_name=wb_name)
    print(res)

    # 4. Diff
    print("\n4️⃣ ACTION: diff")
    t0 = time.time()
    res = wb_client.diff(local_path=local_file, workboard_name=wb_name)
    t_diff = time.time() - t0
    print(f"Time taken: {t_diff:.3f}s")
    print(res)

    # 5. Pull
    print("\n5️⃣ ACTION: pull")
    t0 = time.time()
    res = wb_client.pull(local_path=local_file, workboard_name=wb_name)
    t_pull = time.time() - t0
    print(f"Time taken: {t_pull:.3f}s")
    print(res)

    # 6. Export
    export_local = "test_export_netlist.cir"
    export_remote = "/home/vaibhav22555/Desktop/eldo/test_export_netlist.cir"
    wb_dir = wb_client._get_workboard_dir(wb_name)
    with open(os.path.join(wb_dir, export_local), "w") as f:
        f.write("* WorkBoard Online Export Test\n.PARAM R1=100 C1=1p\n.END\n")

    print("\n6️⃣ ACTION: export")
    t0 = time.time()
    res = wb_client.export(local_path=export_local, remote_path=export_remote, workboard_name=wb_name)
    t_export = time.time() - t0
    print(f"Time taken: {t_export:.3f}s")
    print(res)

if __name__ == "__main__":
    run_workboard_online_test()
