# stress_test_client.py
import time
import os
import json
from file_client_cli import remote_upload, remote_get
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

operation = os.getenv("STRESS_OP", "download").upper()
size_mb = int(os.getenv("FILE_SIZE_MB", 10))
client_workers = int(os.getenv("CLIENT_POOL", 1))
pool_type = os.getenv("CLIENT_POOL_TYPE", "thread").lower()
filename = f"dummy_{size_mb}MB.bin"

def worker(_):
    start = time.time()
    try:
        if operation == 'UPLOAD':
            ok, result = remote_upload(filename)
        else:
            ok, _ = remote_get(filename)
            result = size_mb * 1024 * 1024 if ok else 0
    except Exception as e:
        print(f"Worker exception: {e}")
        ok, result = False, 0
    end = time.time()
    duration = end - start
    return {"ok": ok, "time": duration, "bytes": result}

def run_stress_test():
    os.makedirs("logs", exist_ok=True)
    filepath = os.path.join("server_files", filename)
    if not os.path.exists(filepath):
        with open(filepath,"wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
    if operation == 'UPLOAD':
        if not os.path.exists(filename):
            with open(filepath,"rb") as fn, open(filename,"wb") as cf:
                cf.write(fn.read())

    
def main():    
    run_stress_test()
    Executor = ProcessPoolExecutor if pool_type == "process" else ThreadPoolExecutor

    with Executor(max_workers=client_workers) as executor:
        results = list(executor.map(worker, range(client_workers)))

    total_time = sum(r['time'] for r in results) / client_workers
    total_throughput = sum(r['bytes'] / r['time'] if r['time'] > 0 else 0 for r in results) / client_workers
    successes = sum(1 for r in results if r['ok'])
    failures = client_workers - successes

    output = {
        "operation": operation,
        "volume": size_mb,
        "pool": pool_type,
        "client_workers": client_workers,
        "total_time": total_time,
        "throughput": total_throughput,
        "server_success": successes,  # asumsi sama dengan client success
        "server_fail": failures
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
