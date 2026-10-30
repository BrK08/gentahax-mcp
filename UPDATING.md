# 🔄 What Happens When the GENTAHAX APK Updates? — GENTAHAX MCP

> **Short answer:** most updates change nothing — everything keeps working.
> Run the 5-minute checklist below to be sure. Even on breaking changes, fixing the
> MCP means **swapping plain data files, not rewriting code**.

<div align="center">
👑 <b>mr_berk</b> edition — v1.5.0 · 45 tools · 6832 real item IDs
</div>

---

## 📊 The 3 Scenarios

| Scenario | What happens | Likelihood | What you do |
|---|---|---|---|
| **A — Minor update** (Lua API unchanged) | **Everything keeps working.** The MCP does not live inside the APK — it talks through bridge files at the Lua level, which is version-independent | Most common | 5-min checklist → all green = done |
| **B — Some functions changed/removed** | Templates/scripts using those functions error out; **everything else keeps working** | Occasionally (major versions) | Call `gh_compat_check` → missing functions and affected templates are listed → update `data/api_*.json` |
| **C — Bridge mechanism broken** (injection/file layout changed) | Scripts can't reach the device (`gh_device_status` → no PONG) | Rare | Re-analyze the new APK → update `data/*.json` → redeploy the bridge |

**Architecture guarantee:** everything the MCP knows (57 Android + 18 Windows API
signatures, 32 cheat codes, 6832 item IDs, templates, ban rules) lives in **plain JSON
files under `data/`** — not hardcoded. Adapting to a new APK means **updating files,
not rewriting code**.

**The item database is APK-independent:** the 6832-item list is compiled from
Growtopia's own `items.dat` — it stays valid no matter which GENTAHAX version you run.

---

## ✅ 5-Minute Checklist (after every update)

```
1) Open the game, enter a world, run gentahax_bridge.lua from the Lua Executor
2) gh_device_status   → does it answer PONG?      → yes = Scenario A ✓
3) gh_compat_check    → how many functions found? → 57/57 = FULLY COMPATIBLE ✓
4) Optional mini live test:
   gh_run_lua("return getWorld() and getWorld().name or 'ERR|NO_WORLD'")
   → the world name coming back means the whole live chain works ✓
```

All green → **nothing else needed.**

---

## 🗂️ Data File Map (what each file holds, how to refresh it)

| File | Contents | How to refresh |
|---|---|---|
| `data/api_android.json` | 57 Android Lua API functions (signature, description, example, risk) | New APK/DLL analysis (gh_code_analyze workflow) |
| `data/api_windows.json` | 18 Windows Lua API functions | Same |
| `data/structs_hooks_enums.json` | Structs (NetAvatar...), 10 hooks, 32 CheatCodes, 19 memory patches, 39 packet types | Same |
| `data/items.json` | 6832 real item IDs (items.dat based) | Re-pull when the game adds items |
| `data/protocol.json` | Text packet protocol + verified variant functions | New DLL analysis |
| `data/ban_rules.json` | Ban risk classification rules | Manually as needed |
| `data/templates.json` | 9 verified script templates | Update when functions change |
| `AI_EGITIM.md` / `AI_TRAINING.md` | AI training packs | `python scripts/gen_training_pack.py` (regenerates AUTOMATICALLY from the data files) |

> 🔁 **Remember the loop:** after updating anything in `data/`, regenerate the training
> pack — it is built automatically from those files:
> ```bat
> python scripts\gen_training_pack.py
> ```

---

## 🧪 Scenario B example: a function changed

1. Call `gh_compat_check` → e.g. `PARTIAL — 2/57 functions missing: oldFn, otherFn`
   + "affected templates: dirt_farm, auto_collect"
2. Find the **new function name** in the updated APK (official GENTA-HAX-DOCS /
   DLL string analysis) → add/fix it in `data/api_android.json`
3. Update the affected templates in `data/templates.json` with the new name
4. `python scripts/gen_training_pack.py` → training pack refreshed
5. `gh_compat_check` again → FULLY COMPATIBLE ✓

---

## ⬆️ Updating the MCP itself (git pull)

```bat
cd C:\gentahax-mcp
git pull
```
Pulls the latest release (data files + tools together). If you modified `data/`
yourself, back it up first (`git stash` keeps your changes).

## 📜 Version History

| Version | What landed |
|---|---|
| v1.5.0 | Built-in mod control (gh_cheat_set/gh_cheat_status) · auto-test loop (gh_auto_test) · APK compat check (gh_compat_check) · general script generator (gh_script_gen) · AI training pack |
| v1.4.0 | App mode: `server.py --http` + ChatGPT Plugins / Claude Connectors |
| v1.3.0 | `chat.py` — chat with ANY AI (10 providers, keyless local included) |
| v1.2.0 | `gh_farm_script_gen` — off-template request generator |
| v1.1.0 | Real item ID database (6832 items) + world item counting |

## 👑 mr_berk

`GENTAHAX MCP v1.5.0` — Trained on real data · Ban-risk warning system · 45 tools

*Data: OFFICIAL GENTA-HAX-DOCS + GENTAHAX v5.61 DLL verification (Lua 5.4.6) + real items.dat-based item ID list*
