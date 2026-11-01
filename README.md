<div align="center">

# 🎮 GENTAHAX MCP

### AI-powered Lua tooling for Growtopia GENTAHAX v5.61 — Model Context Protocol

**Author watermark: `mr_berk`**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://gofastmcp.com)
[![Lua](https://img.shields.io/badge/Lua-5.4.6-orange.svg)](https://lua.org)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

**45 tools** · **6832 real item IDs** · **66 Android APIs** · **18 Windows APIs** · **14 templates** · **32 cheat codes** · **39 packet types** · **22 DLL-verified variant functions**

*NOT FAKE — BUILT FROM REAL DATA*

📚 Documentation:
- [INSTALL.md](INSTALL.md) — English setup guide
- [KURULUM.md](KURULUM.md) — Turkish setup guide
- [AGENTS.md](AGENTS.md) — AI instructions for assistants
- [AI_TRAINING.md](AI_TRAINING.md) — English training guide
- [AI_EGITIM.md](AI_EGITIM.md) — Turkish training guide

</div>

---

## What this project is

GENTAHAX MCP connects your AI assistant to the Growtopia GENTAHAX v5.61 scripting ecosystem through the Model Context Protocol (MCP).

After setup, your AI can:

- answer real Growtopia item ID questions
- inspect GENTAHAX Lua APIs and hook signatures
- read packet protocols and variant data
- generate code safely with ban-risk analysis
- check live world data, player info, and inventory information through the in-game bridge
- help you write and manage Lua scripts for GENTAHAX

This repo is not a cheat generator by itself. It is an AI toolchain that gives your assistant real knowledge plus safety checks.

---

## Quick start

### 1) Clone and install

```bash
git clone https://github.com/BrK08/gentahax-mcp.git
cd gentahax-mcp
pip install -r requirements.txt
```

### 2) Start the MCP server

```bash
python start_mcp.py
```

This can automatically detect your Growtopia `Script` folder, install the bridge script, and expose the MCP endpoint locally and via tunnel if available.

### 3) Connect your AI client

Use the generated MCP URL in your preferred client, such as:

- Claude Desktop
- Cursor
- VS Code (GitHub Copilot)
- Windsurf / other MCP-capable tools

For a direct terminal-based AI flow, see the usage examples in the docs and `chat.py`.

### 4) In-game bridge

In Growtopia, open GENTAHAX and run the bridge script, or use this executor command:

```lua
load(makeRequest("http://127.0.0.1:8809/bridge.lua","GET",{},"",5000).content)()
```

This is the bridge used for live world and device communication.

---

## Why this project exists

The goal is simple:

- give AI assistants access to real GENTAHAX knowledge
- expose verified API signatures and item data
- help generate safer scripts instead of random guesses
- reduce risky behavior through analysis before execution

The project is based on:

- official GENTA-HAX documentation and known public reference material
- GENTAHAX v5.61 binary analysis
- real item database data
- verified script patterns and API references

No fake item list, no made-up IDs, and no random function signatures.

---

## Data sources

| Source | What it provides |
|---|---|
| Official GENTA-HAX docs + community references | Android and Windows Lua API signatures, examples, patterns |
| GENTAHAX v5.61 binary analysis | Memory patch names, packet types, real variant-related data |
| Official example scripts and shaders | Real-world examples and benchmark references |
| items.dat-based real item database | 6832 actual item IDs |

> Engine: Lua 5.4.6
>
> Script paths: `Android/media/GENTAHAX/Script/*.lua` and `Script/*.lua`

---

## Included tools

The repo exposes 45 MCP tools organized by category.

### Knowledge tools

- `gh_about`
- `gh_api_search`
- `gh_api_list`
- `gh_api_detail`
- `gh_struct_info`
- `gh_hooks_list`
- `gh_cheats_list`
- `gh_packet_types`
- `gh_variant_guide`
- `gh_protocol_guide`
- `gh_imgui_api`
- `gh_examples_list` / `gh_example_get`
- `gh_templates_list` / `gh_template_get`
- `gh_item_lookup`
- `gh_item_db_search`
- `gh_item_db_info`
- `gh_snippet`
- `gh_learn_lua_gentahax`

### Safety tools

- `gh_code_analyze`
- `gh_ban_risk`
- `gh_safety_rules`
- `gh_safe_mode`

### Live bridge tools

- `gh_device_status`
- `gh_bridge_deploy`
- `gh_run_lua`
- `gh_world_snapshot`
- `gh_world_count_item`
- `gh_world_census`
- `gh_farm_script_gen`
- `gh_script_gen`
- `gh_auto_test`
- `gh_cheat_set`
- `gh_cheat_status`
- `gh_compat_check`
- `gh_player_info`
- `gh_inventory_dump`
- `gh_stop_scripts`

### Script management tools

- `gh_scripts_list`
- `gh_script_read`
- `gh_script_write`
- `gh_script_delete`
- `gh_logs_read`

---

## Safety and ban-risk system

Safety is a core part of the project.

Before running code, `gh_run_lua` analyzes the snippet for risky patterns such as:

- infinite loops without sleep
- packet spam
- invalid or abused action chains
- rapid world enter/exit loops
- HWID tampering patterns
- request loops in unsafe contexts

The system returns warnings and blocks high-risk execution in safe mode by default.

This means the toolchain tries to protect the user from obvious dangerous patterns while still helping with legitimate scripting and analysis.

> Read-only tools such as world counting and inventory read operations are intended to be safe inspection tools and do not depend on sending hostile packets.

---

## Live world helper example

The project includes a live world counting flow for questions like:

- “How many dirt blocks are in my world?”
- “How many peppers are around me?”
- “What items are common in this world?”

The flow works by identifying the item from the real database, then scanning the live in-game world state and returning the count with context.

This is useful for AI assistants because it avoids guesswork and provides grounded answers from real game state.

---

## Which AI clients can use this?

This works with any MCP-capable client, including:

- Claude Desktop
- Cursor
- VS Code / GitHub Copilot
- Windsurf / Zed / Cline / compatible tools

The repo also includes `chat.py`, which can connect to many model providers, including:

- OpenAI
- DeepSeek
- Gemini
- GLM
- OpenRouter
- Qwen
- Mistral
- Ollama / LM Studio
- custom OpenAI-compatible endpoints

---

## Architecture overview

```text
┌─────────────┐   MCP (stdio)   ┌──────────────┐   bridge_in.txt    ┌──────────────────┐
│  Claude /   │ ◄────────────► │  server.py   │ ─────────────────► │ gentahax_bridge  │
│  Cursor AI  │    45 tools     │  knowledge   │ ◄───────────────── │     .lua         │
└─────────────┘                 │  bridge      │   bridge_out.txt   │ (in-game thread) │
                                 └──────────────┘                    └──────────────────┘
```

- Knowledge tools work without a bridge
- Live tools use a local Lua bridge to read game state and execute guarded actions
- The model can ask for live data when the bridge is active

---

## Setup guides

This repository already contains the different language versions of the setup docs:

- [INSTALL.md](INSTALL.md) — English installation and usage guide
- [KURULUM.md](KURULUM.md) — Turkish installation and usage guide

If you are a new visitor, start with the main README here, then continue to the language-specific guide that matches your preference.

---

## Quick install commands

```bash
git clone https://github.com/BrK08/gentahax-mcp.git
cd gentahax-mcp
pip install -r requirements.txt
python start_mcp.py
```

If you want the full step-by-step flow for Windows, Android, or AI client setup, use the detailed guides linked above.

---

## Repository notes

- MIT License: [LICENSE](LICENSE)
- AI instructions: [AGENTS.md](AGENTS.md)
- English training guide: [AI_TRAINING.md](AI_TRAINING.md)
- Turkish training guide: [AI_EGITIM.md](AI_EGITIM.md)
- Benchmark notes: [BENCHMARK_V150.md](BENCHMARK_V150.md)

---

## Responsibility notice

This project is for research, learning, and tooling assistance.

Growtopia's rules can prohibit automation or cheating behavior. This repo includes safety checks, scoring, and warnings, but final responsibility for actual in-game usage remains with the user.

Use responsibly and within the rules of your environment.

---

<div align="center">

### 👑 mr_berk

`GENTAHAX MCP v1.5.0` — Real data, ban-risk warnings, 45 tools, 6832 real item IDs

*Built around real GENTAHAX data and offline knowledge tooling.*

</div>
