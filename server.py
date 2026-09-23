"""Local, read-only Windows MCP helper with per-action desktop approval."""

from __future__ import annotations

import ctypes
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyautogui
from mcp.server.fastmcp import FastMCP, Image


APP_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
STATE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SafeWindowsMCP"
STOP_PATH = STATE_DIR / "STOP"
AUDIT_PATH = STATE_DIR / "audit.jsonl"
MAX_READ_LIMIT = 65536
MAX_TEXT = 200
mcp = FastMCP("Safe Windows MCP")
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


def _audit(action: str, status: str, detail: str = "") -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    record = {"at": datetime.now(timezone.utc).isoformat(), "action": action,
              "status": status, "detail": detail[:250]}
    with AUDIT_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ready() -> None:
    if STOP_PATH.exists():
        raise PermissionError(f"Emergency STOP is active: {STOP_PATH}")


def _settings() -> tuple[list[Path], int]:
    if not CONFIG_PATH.is_file():
        raise RuntimeError(f"Create config.json beside the EXE from config.example.json: {CONFIG_PATH}")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    names = config.get("allowed_roots")
    if not isinstance(names, list) or not names or not all(isinstance(x, str) and x for x in names):
        raise ValueError("allowed_roots must contain at least one folder")
    roots = [Path(os.path.expandvars(os.path.expanduser(x))).resolve(strict=True) for x in names]
    if any(not root.is_dir() or root.parent == root for root in roots):
        raise ValueError("Each allowed root must be an existing, specific folder")
    limit = config.get("max_read_bytes", MAX_READ_LIMIT)
    if type(limit) is not int or not 1 <= limit <= MAX_READ_LIMIT:
        raise ValueError(f"max_read_bytes must be 1..{MAX_READ_LIMIT}")
    return roots, limit


def _allowed(path: str) -> tuple[Path, int]:
    _ready()
    roots, limit = _settings()
    target = Path(path).resolve(strict=True)
    if not any(target == root or root in target.parents for root in roots):
        raise PermissionError("Path is outside allowed_roots")
    return target, limit


def _approve(description: str) -> bool:
    # The Windows desktop of the current user must approve each individual action.
    if sys.platform != "win32":
        raise RuntimeError("Desktop approval requires Windows")
    MB_YESNO = 0x00000004
    MB_ICONWARNING = 0x00000030
    MB_DEFBUTTON2 = 0x00000100
    return ctypes.windll.user32.MessageBoxW(
        0, description, "Safe Windows MCP: allow one action?",
        MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2,
    ) == 6


@mcp.tool()
def list_files(folder: str) -> list[str]:
    """List names in an allowed folder (at most 100 entries)."""
    try:
        target, _ = _allowed(folder)
        if not target.is_dir():
            raise NotADirectoryError(folder)
        entries = sorted(target.iterdir(), key=lambda p: p.name.casefold())[:100]
        result = [p.name + ("/" if p.is_dir() else "") for p in entries]
        _audit("list_files", "ok", str(target))
        return result
    except Exception as exc:
        _audit("list_files", "denied", type(exc).__name__)
        raise


@mcp.tool()
def read_text(path: str) -> str:
    """Read a small UTF-8 text file from an allowed folder."""
    try:
        target, limit = _allowed(path)
        if not target.is_file() or target.stat().st_size > limit:
            raise ValueError("File is not a regular small file")
        with target.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("File exceeds the configured size limit")
        result = data.decode("utf-8")
        _audit("read_text", "ok", str(target))
        return result
    except Exception as exc:
        _audit("read_text", "denied", type(exc).__name__)
        raise


@mcp.tool()
def screenshot() -> Image:
    """Capture the primary desktop once, after local confirmation."""
    _ready()
    if not _approve("Capture the primary screen once?"):
        _audit("screenshot", "rejected")
        raise PermissionError("Local user rejected screenshot")
    _ready()
    import io
    output = io.BytesIO()
    pyautogui.screenshot().save(output, format="PNG")
    _audit("screenshot", "ok")
    return Image(data=output.getvalue(), format="png")


@mcp.tool()
def click(x: int, y: int) -> str:
    """Perform one left click on the primary screen, after local confirmation."""
    _ready()
    width, height = pyautogui.size()
    if type(x) is not int or type(y) is not int or not (0 <= x < width and 0 <= y < height):
        raise ValueError("Coordinates are outside the primary screen")
    if not _approve(f"Click once at ({x}, {y})?"):
        _audit("click", "rejected", f"{x},{y}")
        raise PermissionError("Local user rejected click")
    _ready()
    pyautogui.click(x=x, y=y, button="left", clicks=1)
    _audit("click", "ok", f"{x},{y}")
    return "Clicked once"


@mcp.tool()
def type_text(text: str) -> str:
    """Type at most 200 printable ASCII characters after local confirmation."""
    _ready()
    if not isinstance(text, str) or not 1 <= len(text) <= MAX_TEXT or any(not 32 <= ord(c) <= 126 for c in text):
        raise ValueError("Only 1..200 printable ASCII characters are allowed")
    if not _approve(f"Type this text once?\n\n{text}"):
        _audit("type_text", "rejected")
        raise PermissionError("Local user rejected typing")
    _ready()
    pyautogui.write(text, interval=0.02)
    _audit("type_text", "ok", f"length={len(text)}")
    return "Typed once"


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("This application requires Windows 10 or 11")
    _settings()  # Reject missing or unsafe configuration before serving requests.
    _ready()
    print("Safe Windows MCP is running locally over stdio. Close this window to stop.", file=sys.stderr)
    mcp.run(transport="stdio")
