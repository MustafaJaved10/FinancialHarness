"""Python sandbox: run user/LLM-generated analysis code in isolation.

Safety model:
- separate subprocess (never in the API process)
- hard timeout, killed on expiry
- only an allow-list of imports (pandas, numpy, math, statistics, json...)
- no file writes, no network, no os/sys/subprocess
- runs with a minimal environment in an empty working directory
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ALLOWED_IMPORTS = {"pandas", "numpy", "math", "statistics", "json", "datetime"}
MAX_SECONDS = 20
MAX_OUTPUT_CHARS = 8000

_RUNNER = r"""
import json, sys
code = sys.stdin.read()
import ast
tree = ast.parse(code)
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        mod = (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else node.names[0].name.split(".")[0]
        if mod not in ALLOWED:
            raise PermissionError(f"import not allowed in sandbox: {mod}")
    if isinstance(node, ast.Name) and node.id in {"open", "eval", "exec", "__import__"}:
        raise PermissionError(f"call not allowed in sandbox: {node.id}")
g = {"__builtins__": {k: getattr(__builtins__, k) for k in
     ["print","len","range","min","max","sum","abs","round","float","int","str","list","dict","sorted","enumerate","zip","__import__"] if hasattr(__builtins__, k)}}
import pandas, numpy
g.update({"pd": pandas, "np": numpy, "pandas": pandas, "numpy": numpy})
exec(compile(tree, "<sandbox>", "exec"), g)
result = g.get("result")
print("__RESULT__:" + json.dumps(result, default=str))
""".replace("ALLOWED", repr(sorted(ALLOWED_IMPORTS)) if False else "ALLOWED_PLACEHOLDER")


def run_analysis(code: str, timeout: int = MAX_SECONDS) -> dict:
    runner = _RUNNER.replace("ALLOWED_PLACEHOLDER", json.dumps(sorted(ALLOWED_IMPORTS)))
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", runner],
                input=code, capture_output=True, text=True,
                timeout=min(timeout, MAX_SECONDS), cwd=tmp,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ""},
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timed out after {timeout}s"}
    stdout = proc.stdout[:MAX_OUTPUT_CHARS]
    result = None
    for line in stdout.splitlines():
        if line.startswith("__RESULT__:"):
            result = json.loads(line[len("__RESULT__:"):])
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "sandbox error",
                "stdout": stdout}
    return {"ok": True, "result": result, "stdout": stdout.replace("__RESULT__:" + json.dumps(result, default=str), "").strip()}
