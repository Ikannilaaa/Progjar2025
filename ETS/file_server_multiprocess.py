# file_server_multiprocess.py
import socket
import logging
import os
import base64
import json
from concurrent.futures import ProcessPoolExecutor

end_marker = b"\r\n\r\n"
max_workers = int(os.getenv("MAX_WORKERS", 5))
filepath = "server_files"

def handle_client(filedata):
    sock = socket.fromfd(filedata, socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(300)
    try:
        data_received = b""
        while end_marker not in data_received:
            chunk = sock.recv(2**20)
            if not chunk:
                break
            data_received += chunk
        request_data = data_received.split(end_marker)[0].decode()
        tokens = request_data.split(" ", 2)
        command = tokens[0]
        
        if command == "LIST":
            response = {"status": "OK", "data": os.listdir(filepath)}
        elif command == "GET":
            filename = tokens[1]
            data = base64.b64encode(open(os.path.join(filepath, filename), "rb").read()).decode()
            response = {"status": "OK", "data": data}
        elif command == "UPLOAD":
            filename, b64data = tokens[1], tokens[2]
            with open(os.path.join(filepath, filename), "wb") as f:
                f.write(base64.b64decode(b64data))
            response = {"status": "OK", "data": "Uploaded"}
        else:
            response = {"status": "ERROR", "data": "Unknown command"}

    except Exception as e:
        print(f"[!] Error: {e}")
        response = {"status": "ERROR", "data": str(e)}

    sock.sendall((json.dumps(response)).encode() + end_marker)
    sock.close()
    os.close(filedata)

def main():
    port = 7777
    os.makedirs(filepath, exist_ok=True)
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen()
    logging.info(f"[MPROCESS] port={port} workers={max_workers}")

    with ProcessPoolExecutor(max_workers) as pool:
        while True:
            sock, _ = server_socket.accept()
            filedata = os.dup(sock.fileno())
            pool.submit(handle_client, filedata)
            sock.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
