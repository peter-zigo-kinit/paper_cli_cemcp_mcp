# Installing MCP Servers on Windows

The `install.sh` script requires a Unix-like environment (Linux/macOS). On Windows, you have several options:

## Option 1: Install WSL (Windows Subsystem for Linux) - Recommended

### Quick Install:

1. **Open PowerShell as Administrator** (Right-click PowerShell → "Run as Administrator")

2. **Install WSL:**
   ```powershell
   wsl --install
   ```

3. **Restart your computer** when prompted

4. **After restart, open Ubuntu** from the Start menu (or type `wsl` in PowerShell)

5. **Navigate to your project and run install.sh:**
   ```bash
   cd /mnt/c/Users/user/PycharmProjects/MCP_Research/mcp-bench/mcp_servers
   bash install.sh
   ```

**Note**: In WSL, Windows drives are at `/mnt/c/`, `/mnt/d/`, etc.

---

## Option 2: Use Git Bash (If you have Git for Windows)

If you already have Git for Windows installed:

1. **Open Git Bash** (search for "Git Bash" in Start menu)

2. **Navigate to the directory:**
   ```bash
   cd /c/Users/user/PycharmProjects/MCP_Research/mcp-bench/mcp_servers
   bash install.sh
   ```

---

## Option 3: Install Just the Server You Need (Simpler)

If you only need specific servers (like Wikipedia), you can install them manually:

### For Wikipedia Server (Example):

1. **Make sure you have Python and uv installed:**
   ```powershell
   python --version  # Should be 3.10+
   uv --version      # Install with: pip install uv
   ```

2. **Navigate to the Wikipedia server directory:**
   ```powershell
   cd mcp-bench\mcp_servers\wikipedia-mcp
   ```

3. **Install dependencies:**
   ```powershell
   uv sync
   # or if that doesn't work:
   uv pip install -e .
   # or:
   pip install -r requirements.txt
   ```

4. **Test it works:**
   ```powershell
   uv run python -m wikipedia_mcp
   ```
   (Press Ctrl+C to stop it)

### For Other Servers:

Check `commands.json` to see what command each server uses, then:
- **Python servers**: Install with `pip install -r requirements.txt` or `uv sync`
- **Node.js servers**: Install with `npm install` in the server directory

---

## Option 4: Manual Full Installation

If you want to install all servers manually on Windows:

### Prerequisites:

1. **Node.js** (v18+): https://nodejs.org/
2. **Python** (v3.10+): https://www.python.org/downloads/
3. **uv**: `pip install uv`

### Then for each server in `commands.json`:

1. Navigate to the server directory
2. Install dependencies based on what the server needs:
   - If it has `requirements.txt`: `pip install -r requirements.txt`
   - If it has `package.json`: `npm install`
   - If it has `pyproject.toml` or `uv.lock`: `uv sync`

---

## Recommended: Use WSL

**I strongly recommend Option 1 (WSL)** because:
- ✅ The install script works as-is
- ✅ Servers are designed for Unix-like environments
- ✅ Easier to troubleshoot
- ✅ One command installs everything

### WSL Installation Troubleshooting:

If `wsl --install` doesn't work, try:

1. **Enable WSL feature manually:**
   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```
   Then restart and run `wsl --install`

2. **Or install a specific distribution:**
   ```powershell
   wsl --list --online    # See available distributions
   wsl --install Ubuntu  # Install Ubuntu
   ```

---

## After Installation (Any Method)

1. **Set up API keys** in `mcp-bench/mcp_servers/api_key` (if needed)

2. **Set your OpenAI API key:**
   ```powershell
   $env:OPENAI_API_KEY="sk-your-key-here"
   ```

3. **Test the bridge:**
   ```powershell
   python mcp-bench/run_with_aicode_agents.py --agent code_execution --servers Wikipedia
   ```

---

## Quick Test: Do You Really Need install.sh?

If you only need a few servers, you might not need to run the full install script. Try installing just the server you need first:

```powershell
# Example: Just install Wikipedia
cd mcp-bench\mcp_servers\wikipedia-mcp
uv sync
```

If that works, you can skip the full install script!
