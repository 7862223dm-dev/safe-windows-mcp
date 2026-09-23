"""Check that the frozen server starts and exits cleanly on stdin EOF."""

import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
(root / "dist" / "config.json").write_text(
    json.dumps({"allowed_roots": [str(root)], "max_read_bytes": 1024}),
    encoding="utf-8",
)
result = subprocess.run(
    [str(root / "dist" / "SafeWindowsMCP.exe")],
    input=b"",
    capture_output=True,
    timeout=45,
    check=False,
)
assert result.returncode == 0, result.stderr.decode(errors="replace")
assert b"Safe Windows MCP is running locally" in result.stderr, result.stderr.decode(errors="replace")
