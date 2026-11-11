"""Send market data to the approved Python runner over a local Unix socket."""
import json
import os
import socket
from pathlib import Path

MAX_BYTES = 256 * 1024
SOCKET_PATH = Path(os.getenv("ANALYSIS_SOCKET", "/sandbox-ipc/analysis.sock"))


def run_isolated(operation, payload):
    request = json.dumps({"operation": operation, "payload": payload}, allow_nan=False).encode()
    if len(request) >= MAX_BYTES:
        raise ValueError("Analysis input is too large.")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(SOCKET_PATH))
        connection.sendall(request + b"\n")
        with connection.makefile("rb") as reader:
            raw = reader.readline(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise RuntimeError("The Python sandbox returned an invalid response.")
    result = json.loads(raw)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result
