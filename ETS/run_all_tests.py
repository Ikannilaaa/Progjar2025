#!/usr/bin/env python3
import os
import json
import subprocess
import platform
import time
import signal
import csv

IS_WINDOWS = platform.system() == "Windows"

MODES         = {"thread": "file_server_multithreadpool.py", "process": "file_server_multiprocesspool.py"}
SERVER_COUNTS = [1, 5, 50]
CLIENT_COUNTS = [1, 5, 50]
FILE_SIZES    = [10, 50, 100]
OPERATIONS    = ["upload", "download"]
CSV_NAME      = "results.csv"

def spawn_server(mode: str, workers: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["MAX_WORKERS"] = str(workers)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0
    return subprocess.Popen(
        ["python", MODES[mode]],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags
    )

def stop_server(proc: subprocess.Popen):
    try:
        if IS_WINDOWS:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # type: ignore
        proc.wait(timeout=5)
    except Exception as err:
        print(f"[!] Error saat mematikan server: {err}")
        proc.terminate()

def run_client_stress(operation: str, size_mb: int, client_workers: int) -> dict:
    env = os.environ.copy()
    env.update({
        "STRESS_OP": operation,
        "FILE_SIZE_MB": str(size_mb),
        "CLIENT_POOL": str(client_workers)
    })

    result = subprocess.run(["python", "stress_test.py"], capture_output=True, text=True, env=env)
    return json.loads(result.stdout)

def setup_csv(file_path: str):
    headers = [
        "No", "Model concurrency", "Operasi", "Volume",
        "Jumlah client worker pool", "Jumlah server worker pool",
        "Waktu total per client", "Throughput per client",
        "Jumlah client sukses", "Jumlah client gagal",
        "Jumlah server sukses", "Jumlah server gagal"
    ]
    f = open(file_path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    return f, writer

def record_result(writer, index: int, mode, op, size, cw, sw, result):
    writer.writerow({
        "No": index,
        "Model concurrency": mode,
        "Operasi": op,
        "Volume": f"{size} MB",
        "Jumlah client worker pool": cw,
        "Jumlah server worker pool": sw,
        "Waktu total per client": result.get("total_time_s", 0),
        "Throughput per client": result.get("throughput_Bps", 0),
        "Jumlah client sukses": result.get("succeed", 0),
        "Jumlah client gagal": result.get("failed", cw),
        "Jumlah server sukses": sw,
        "Jumlah server gagal": 0
    })

def run_experiments():
    csv_file, writer = setup_csv(CSV_NAME)
    experiment_id = 1

    for mode in MODES:
        for server_pool in SERVER_COUNTS:
            print(f"> Menyalakan server: mode={mode}, worker={server_pool}")
            server_proc = spawn_server(mode, server_pool)
            time.sleep(1.5)

            for op in OPERATIONS:
                for size in FILE_SIZES:
                    for client_pool in CLIENT_COUNTS:
                        print(f"  • {mode} | {op} | {size}MB | client×{client_pool}")
                        try:
                            result = run_client_stress(op, size, client_pool)
                        except Exception as e:
                            print(f"  ✖ Error: {e}")
                            result = {
                                "total_time_s": 0,
                                "throughput_Bps": 0,
                                "succeed": 0,
                                "failed": client_pool
                            }

                        record_result(writer, experiment_id, mode, op, size, client_pool, server_pool, result)
                        csv_file.flush()
                        experiment_id += 1

            stop_server(server_proc)
            time.sleep(0.5)

    csv_file.close()
    print(f"Eksperimen selesai — hasil disimpan di '{CSV_NAME}'")

if __name__ == "__main__":
    run_experiments()
