"""Network-disabled service for fixed, approved Python calculations."""
import json
import os
import socketserver
import subprocess
import sys

from .isolated_analysis import MAX_BYTES, SOCKET_PATH


class AnalysisRequest(socketserver.StreamRequestHandler):
    timeout = 12

    def handle(self):
        request = self.rfile.readline(MAX_BYTES + 1)
        if not request or len(request) > MAX_BYTES:
            return
        try:
            process = subprocess.run(
                [sys.executable, "-m", "stock_assistant.analysis_worker", "--calculate"],
                input=request, capture_output=True, timeout=8,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            if process.returncode or not process.stdout or len(process.stdout) > MAX_BYTES:
                output = b'{"error":"Sandbox calculation failed."}\n'
            else:
                output = process.stdout
        except subprocess.TimeoutExpired:
            output = b'{"error":"Sandbox calculation timed out."}\n'
        self.wfile.write(output)


def main():
    if sys.argv[1:] == ["--calculate"]:
        from .approved_analysis import calculate

        request = json.load(sys.stdin)
        print(json.dumps(calculate(request["operation"], request["payload"]), allow_nan=False))
        return
    SOCKET_PATH.unlink(missing_ok=True)
    with socketserver.UnixStreamServer(str(SOCKET_PATH), AnalysisRequest) as server:
        os.chmod(SOCKET_PATH, 0o660)
        server.serve_forever()


if __name__ == "__main__":
    main()
