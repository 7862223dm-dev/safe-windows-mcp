# Safe Windows MCP

A local Windows 10/11 MCP server over **stdio**. It can list and read small UTF-8 files inside folders you explicitly allow, capture the primary screen, perform one left click, and type up to 200 printable ASCII characters. Every screen capture, click, and typing request requires a separate visible Windows confirmation. The confirmation defaults to **No**.

There is no shell tool, file write or delete tool, startup registration, or network listener. Run it as a normal desktop user, never as administrator. MCP clients can receive the content of allowed files and approved screenshots, so choose folders and clients carefully.

## Download and first run

1. Download the `SafeWindowsMCP-windows` artifact from the latest successful [Build Windows EXE](https://github.com/7862223dm-dev/safe-windows-mcp/actions/workflows/build-windows.yml) run. It contains `SafeWindowsMCP.exe`, `SafeWindowsMCP.exe.sha256`, this README, and `config.example.json`.
2. Verify the SHA-256 in PowerShell: `Get-FileHash .\SafeWindowsMCP.exe -Algorithm SHA256`. Compare it with the checksum file.
3. Copy `config.example.json` to `config.json` beside the EXE. Replace the sample `allowed_roots` path with an existing, specific folder that you are willing to expose to your MCP client. Do not allow a whole drive, your entire profile, or folders with secrets. You can lower `max_read_bytes` (maximum 65536).
4. Configure your MCP client to launch the absolute path to `SafeWindowsMCP.exe` as a **stdio** server. Keep the process in your interactive desktop session so Windows confirmation dialogs are visible. No port or firewall rule is needed.

Closing the process stops the server. If the local confirmation dialog is unexpected, choose **No**. Moving the mouse to the upper-left corner activates PyAutoGUI's fail-safe.

## Emergency stop and audit

Create `%LOCALAPPDATA%\SafeWindowsMCP\STOP` to reject new requests. For example, in PowerShell:

```powershell
New-Item "$env:LOCALAPPDATA\SafeWindowsMCP\STOP" -ItemType File -Force
```

The audit log is `%LOCALAPPDATA%\SafeWindowsMCP\audit.jsonl`. To resume, inspect it and remove the STOP file manually. The log records action, outcome, time, and file paths or click coordinates, but never typed text, file contents, or screenshot pixels.

## Development

On Windows with Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt pyinstaller
Copy-Item config.example.json config.json
.\.venv\Scripts\python server.py
```

The GitHub Actions workflow builds the Windows EXE using PyInstaller and uploads it with a SHA-256 checksum. This artifact is unsigned; Windows may show a publisher warning. Review the code and checksum before running it.
