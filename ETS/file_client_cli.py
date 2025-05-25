# file_client_cli.py
import socket
import json
import base64
import logging
import os

server_address = ('127.0.0.1', 7777)
end_marker = "\r\n\r\n"

def send_command(command_str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect(server_address)
    logging.warning(f"Connecting to {server_address}")

    try:
        if not command_str.endswith(end_marker):
            command_str += end_marker
        sock.sendall(command_str.encode())

        data_received = ""
        while True:
            data = sock.recv(4096)
            if data:
                data_received += data.decode()
                if end_marker in data_received:
                    break
            else:
                break
        hasil = json.loads(data_received.strip().split(end_marker)[0])
        return hasil
    except (socket.timeout, ConnectionResetError) as e:
        print(f"Client send exception: {e}")
        return {"status": "ERROR", "data": str(e)}
    except Exception as e:
        print(f"Client unexpected exception: {e}")
        return {"status": "ERROR", "data": str(e)}
    finally:
        sock.close()

def remote_list():
    return send_command("LIST")

def remote_get(filename=""):
    hasil = send_command(f"GET {filename}")
    if hasil and hasil.get('status') == 'OK':
        isifile = base64.b64decode(hasil['data'])
        with open(f"dl_{filename}", "wb") as fp:
            fp.write(isifile)
        return True, len(isifile)
    return False, 0

def remote_upload(filepath):
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    command_str = send_command(f"UPLOAD {filename} {data}")
    return command_str.get("status") == "OK", 0
