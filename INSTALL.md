# 📦 INSTALL & USAGE GUIDE — GENTAHAX MCP

> **Who is this for?** A complete beginner ("person X") who just found this repo.
> Follow the steps in order — total time **~10 minutes**.
> Windows paths are shown by default; Android differences are marked separately.

<div align="center">
👑 <b>mr_berk</b> edition — v1.4.0 · 40 tools · 6832 real item IDs
</div>

---

## 🔍 What is this? (30 seconds)

GENTAHAX MCP turns your AI (Claude, Cursor, VS Code Copilot...) into a **Growtopia GENTAHAX v5.61 scripting expert**. After setup you can simply talk to your AI:

- 🎮 It **writes and runs Lua code in-game** for you (after analyzing ban risk!)
- 🔢 **"What ID is dirt?"** → correct answer from a real 6832-item database
- 🌍 **"How many dirt blocks are in my world?"** → scans the live game memory and returns the **real number**
- 📚 Knows the full GENTAHAX Lua API, variant lists, packet protocol — **never invents**

> 🇹🇷 Türkçe rehber: bkz. [KURULUM.md](KURULUM.md)

---

## ✅ Requirements (check before you start)

| # | What you need | How to check |
|---|---|---|
| 1 | **GENTAHAX v5.61** installed & running (Android APK or Windows) | Does the GENTAHAX menu open in Growtopia? |
| 2 | **Python 3.10+** | Run `python --version` in a terminal |
| 3 | An **MCP-capable AI client** | Claude Desktop *(recommended)*, Cursor, VS Code (Copilot) |
| 4 | *(For live data)* your GENTAHAX **Script folder path** | See "Step 0" below |

> ⚠️ **Know this first:** Growtopia's Terms of Service prohibit mods/cheats; your account **can be banned**. This MCP warns you and blocks high-risk code in safe mode, but the final decision and responsibility are yours. Don't use it on accounts with valuable items.

---

## Step 0 — Get GENTAHAX ready

The MCP sits **on top of** GENTAHAX; without it only the knowledge tools work.

1. **Open GENTAHAX** (Windows: `GH Loader.exe` → enter the game · Android: the GENTAHAX APK).
2. If it asks for a **license key** on first launch: type **anything** — the license system is local and accepts every input (known working key: `R0VOVEEgSEFY`). It never contacts a server.
3. **Note the full path of the Script folder:**
   - 🪟 **Windows:** the `Script\` subfolder next to `GH Loader.exe`
     *(e.g. `C:\Users\Alex\GENTAHAX\Script` — create it if missing)*
   - 🤖 **Android:** `/storage/emulated/0/Android/media/GENTAHAX/Script/`
4. Quick test: make sure the GENTAHAX menu → **Lua Executor** is present and working.

---

## Step 1 — Install Python (if you don't have it)

1. https://www.python.org/downloads/ → **Download Python 3.1x** → install.
2. In the installer, **check "Add python.exe to PATH" ✅** (the most forgotten step!).
3. Verify in a new terminal (Win+R → `cmd`):

```bat
python --version
:: Python 3.10.x or newer = OK
```

---

## Step 2 — Download this repo

**Option A — ZIP (easiest):**
On GitHub: green **`<> Code`** → **`Download ZIP`** → extract.
Recommended location: `C:\gentahax-mcp`

**Option B — git:**

```bat
git clone https://github.com/BrK08/gentahax-mcp.git C:\gentahax-mcp
```

---

## Step 3 — Install the dependency (one package)

```bat
cd C:\gentahax-mcp
pip install -r requirements.txt
```

> `requirements.txt` contains only `fastmcp`. If it fails: `pip install fastmcp`

Optional verification:

```bat
python tests\test_gentahax_mcp.py
:: RESULT: 41 passed, 0 failed  (also: tests\test_mcp_protocol.py, tests\test_world_count_e2e.py)
```

---

## Step 4 — Register it with your AI client

### 🖥️ Claude Desktop (recommended)

1. https://claude.ai/download → install, open once.
2. Edit this file:
   - 🪟 **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
     *(type `%APPDATA%\Claude` in Explorer's address bar)*
   - 🍎 **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Paste — **with your own paths**:

```json
{
  "mcpServers": {
    "gentahax": {
      "command": "python",
      "args": ["C:\\gentahax-mcp\\server.py"],
      "env": {
        "GENTAHAX_SCRIPT_DIR": "C:\\Users\\ALEX\\GENTAHAX\\Script"
      }
    }
  }
}
```

> 🪟 Use **double backslashes** (`\\`) in paths. `GENTAHAX_SCRIPT_DIR` = the Script folder from Step 0.

4. **Fully quit and restart** Claude Desktop (Exit from system tray).
5. Click the **🔧 Tools** icon in the chat box → the **gentahax** server should list `gh_about`, `gh_run_lua`, `gh_world_count_item`... If visible: **installation complete** 🎉

### 🖱️ Cursor

`.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "gentahax": {
      "command": "python",
      "args": ["C:\\gentahax-mcp\\server.py"],
      "env": { "GENTAHAX_SCRIPT_DIR": "C:\\Users\\ALEX\\GENTAHAX\\Script" }
    }
  }
}
```

### 🧩 VS Code (GitHub Copilot)

`.vscode/mcp.json` (same content; VS Code ≥ 1.99 supports MCP).

### 🤖 Android users — special section

The MCP server runs **on your PC** and reaches the phone over **USB (adb)**:

1. On the phone: **Developer options → USB debugging** ✅
2. Install adb on the PC ([platform-tools](https://developer.android.com/tools/releases/platform-tools)), connect via USB.
3. Verify: `adb devices` → your device must be listed.
4. Change the `env` block in the config:

```json
"env": {
  "GENTAHAX_TARGET": "adb",
  "GENTAHAX_ADB_DIR": "/storage/emulated/0/Android/media/GENTAHAX/Script"
}
```

> Claude Desktop stays open **on the PC**; while the phone is connected over USB, the AI can access your game live.

### 🤖 Step 4B — No Claude Desktop? Use ANY AI you want

Don't want a config file? **`chat.py`** connects ChatGPT, Gemini, GLM, DeepSeek, Qwen, Mistral, OpenRouter — even **keyless free local AI (Ollama/LM Studio)**:

```bat
cd C:\gentahax-mcp

:: 1) Test the MCP side first (NO KEY NEEDED — verifies your setup):
python chat.py --check

:: 2) List supported AIs:
python chat.py --list-ai

:: 3) Connect your AI (examples):
python chat.py --provider deepseek --api-key sk-... --ask "what's the ID of dirt?"
python chat.py --provider gemini   --api-key AIza...              :: interactive chat
python chat.py --provider ollama   --model llama3.1               :: FREE, local, no key

:: 4) Or persist settings (skip --api-key every time):
set GENTAHAX_AI_PROVIDER=deepseek
set DEEPSEEK_API_KEY=sk-...
python chat.py --ask "how many dirt blocks are in my world?"
```

| Provider | Key from | Note |
|---|---|---|
| `deepseek` | platform.deepseek.com | one of the cheapest |
| `gemini` | aistudio.google.com | **free** key |
| `glm` | bigmodel.cn | glm-4-flash free tier |
| `openrouter` | openrouter.ai | 300+ models, one key |
| `ollama` | **NO KEY** | ollama.com → `ollama pull llama3.1` — fully local |
| `lmstudio` | **NO KEY** | lmstudio.ai → Developer → start server |
| `custom` | your endpoint | any OpenAI-compatible service via `--base-url` + `--model` |

> In the `chat.py` chat, `/tools` lists the 40 tools, `/exit` quits. Same safety: the AI cannot run high-risk code without passing `gh_code_analyze` first.

### 📱 Step 4C — Directly inside the APP (ChatGPT web · Claude web/mobile)

No API key, no config file: start the server in **HTTP mode** → turn it into HTTPS with a free tunnel → add it in the app's **Plugins/Connectors**. Then ask from the app's own UI: *"how many dirt blocks are in my world?"*

**1) Start the server in HTTP mode** (keep the terminal open):
```bat
cd C:\gentahax-mcp
python server.py --http --port 8808
:: → listens on http://127.0.0.1:8808/mcp (40 tools ready)
```

**2) Open a free HTTPS tunnel** (ChatGPT/Claude only accept HTTPS endpoints):
- Download [cloudflared](https://github.com/cloudflare/cloudflared/releases) (`cloudflared-windows-amd64.exe`) → run in a **second terminal**:
```bat
cloudflared-windows-amd64.exe tunnel --url http://localhost:8808
:: → output shows: https://xxxx-xxxx-xxxx.trycloudflare.com  (changes each run)
```
- **Your MCP endpoint**: `https://xxxx-xxxx-xxxx.trycloudflare.com/mcp` (append `/mcp`!)

**3A) In ChatGPT** *(web: chatgpt.com — Plus/Pro/Business/Enterprise plans; NOT in the mobile app)*:
1. Settings → **Connectors** → Advanced → enable **Developer mode**
2. **chatgpt.com/plugins** → **+** → **Add custom MCP server**
3. Name: `GENTAHAX` · URL: your tunnel URL + `/mcp` → acknowledge the risk warning → **Create**
4. Tools are scanned (you should see 40 tools) → ask in chat: *"what's the ID of dirt?"*
> Note: if your plan limits write actions, tools run read-only (counting, ID lookups still work); test in your own account.

**3B) In Claude** *(web + mobile + Desktop — even the FREE plan gets 1 custom connector)*:
1. **claude.ai** → **Customize** → **Connectors** → **+ Add custom connector**
2. URL: your tunnel URL + `/mcp` → Continue → Authentication: **"No sign in"** → **Add**
3. In a chat, click **+** (bottom left) → **Connectors** → enable GENTAHAX → ask: *"how many dirt blocks are in my world?"*
> Claude connectors also work in the **mobile app** — you can ask from your phone.

**⚠️ Security notes:**
- While the tunnel is open, ANYONE who knows the URL can call your tools. The trycloudflare address is random and temporary — still, close the tunnel and server with **Ctrl+C** when done.
- `gh_run_lua` keeps its safe-mode + risk-analysis protection — the ⚠️ ban warning applies even when called from inside an app.
- "Can't connect"? Are the terminals from steps 1–2 still open? The tunnel URL CHANGES on every restart → update it in the app.

---

## Step 5 — Set up the live bridge (for world/inventory data)

Knowledge tools (item DB, API docs, risk analysis) work **without the bridge**.
Live tools (world counting, player list, running code) need the bridge — **2 minutes**:

1. Type in your AI chat:
   > *"Deploy the bridge to my device"* (tool: `gh_bridge_deploy`)
   → writes `gentahax_bridge.lua` into the Script folder.
2. **In game:** GENTAHAX menu → **Lua Executor** → pick `gentahax_bridge.lua` → **Execute**.
3. Type in your AI chat:
   > *"Check device status"* (tool: `gh_device_status`)
   → seeing `"bridge_responding": true` / `PONG` means **you're ready** 🎉

**How does the bridge work?** It's a silent Lua thread running inside the game:
it reads commands written to `bridge_in.txt` → executes → writes results to `bridge_out.txt`.
It never contacts any server; everything stays **on your device**.

---

## 🎮 USAGE — things to say to your AI

After setup, you don't need to do anything special — **just talk**:

| 👤 You say... | 🤖 The AI does |
|---|---|
| "What's the ID of dirt? And its seed?" | Real DB: **Dirt = ID 2**, Dirt Seed = ID 3 (of 6832 items) |
| "Write me an auto collect script" | Writes it from the template → adds a **"⚠️ THIS HAS BAN RISK"** warning + risk score |
| **"How many dirt blocks are in my world?"** | Live RAM scan → *"264 Dirt (ID 2) — foreground: 214, background: 50"* — the **REAL number** |
| "List everyone in my world" | `gh_player_info` → live player list |
| "Dump my inventory" | `gh_inventory_dump` → live inventory |
| "Will this code get me banned: `while true do ... end`" | `gh_code_analyze` → risk score + which line is risky + how to fix |
| "Can I do ESP without getting banned?" | Writes a low-risk ImGui-based ESP (visual layer = no packets sent) |
| "How do I read variant lists? Show an example" | Guide with DLL-verified real variant functions + code |
| "What is ID 112?" | **112 = Gems** ⭐ (ID questions work in reverse too) |
| "Save my fishing script" | `gh_script_write` → saves it to the Script folder → run it in-game via Execute |

**What it's smart about:** 57 Android + 18 Windows Lua functions, 10 hooks, 32 cheat codes, 39 packet types, 22 DLL-verified variant functions, 15 structs, 62 ImGui functions, 7 ready templates, 19 ban-risk rules.

---

## 🛡️ Ban-risk system — how it protects you

`gh_run_lua` analyzes every snippet **before running it**:

```
🔴 HIGH risk → DOES NOT RUN. Returns "⚠️ THIS HAS BAN RISK" + reasons + fixes.
🟡 MEDIUM   → Runs but warns you.
🟢 LOW      → Runs cleanly.
```

- High-risk examples: infinite loops without sleep, packet spam, `action|enter_game` spam, rapid world enter/exit, HWID changing (`randomGid`, `setMac`...), `requestTileChange` inside loops.
- **Safe mode is ON by default.** If you deliberately want to run high-risk code:
  1. Fix the code (recommended — the AI tells you how), **or**
  2. Set `"GENTAHAX_SAFE_MODE": "0"` in the config + call with `force=true` (your call).
- **Read-only tools never send packets:** `gh_world_count_item`, `gh_world_census`, `gh_world_snapshot`, `gh_player_info`, `gh_inventory_dump` → read from RAM → **ZERO ban risk**.

---

## 🔧 Troubleshooting

| Symptom | Fix |
|---|---|
| `'python' not found` | You forgot "Add to PATH" during install — reinstall Python with the box checked, or try `py`. |
| No 🔧 tools in Claude | 1) JSON typo (comma/quote) — validate at jsonlint.com. 2) Are the paths real? 3) Fully quit & restart Claude from the tray. 4) Check `%APPDATA%\Claude\logs\mcp*.log`. |
| `ModuleNotFoundError: fastmcp` | `pip install fastmcp` — or give the full Python path as `command` in the config (`C:\\Python312\\python.exe`). |
| `gh_device_status` → `configured: false` | `GENTAHAX_SCRIPT_DIR` missing/wrong (Windows) or `GENTAHAX_TARGET=adb` missing (Android). |
| `bridge_responding: false` | 1) Did you Execute `gentahax_bridge.lua` in game? 2) Are you inside a world (not the menu)? 3) Wait 10 s and retry. 4) Check whether `bridge_in.txt`/`bridge_out.txt` exist in the Script folder. |
| `adb devices` empty | USB debugging off / cable is charge-only / approve the popup on the phone. |
| High-risk code "didn't run" | That's safe mode. Deliberately: `GENTAHAX_SAFE_MODE=0` + `force=true`. Try the AI's suggested fix first. |
| Answers not in my language | Just tell the AI "answer in Turkish/English" — the MCP works with both. |

---

## ❓ FAQ

**Is it paid?** No. MIT license, fully open source.

**Does it need internet?** Knowledge tools work fully **offline**. The live bridge works over local files/USB. Only the AI client itself (Claude etc.) uses the internet.

**Will I be banned?** Using mods violates the game's ToS — the risk is **always yours**. This MCP's job is to make risk **visible**: it refuses high-risk code, explains why, and suggests fixes. Read-only tools (world counting etc.) send no packets and are safe.

**Does it work with other AIs?** Any MCP-capable client: Claude Desktop, Cursor, VS Code Copilot, Windsurf, Zed...

**Where does the data come from?** The GENTAHAX developer's official documentation + GTInternal.dll binary analysis + a real items.dat-based list of 6832 items. **No fake data** — on ambiguous queries the AI never guesses, it lists candidates.

**Where do I get GENTAHAX?** This repo is only the MCP tool; the mod itself is not included. It's for people who already use the mod.

---

## 👑 mr_berk

```
GENTAHAX MCP v1.4.0 — mr_berk edition
Trained on real data · Ban-risk warning system · 40 tools · 6832 real item IDs
```

*Found it useful? Leave a ⭐ on the repo. Stuck? Open an [Issue](https://github.com/BrK08/gentahax-mcp/issues).*
