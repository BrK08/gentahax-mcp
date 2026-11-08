#!/usr/bin/env python3
"""
Adversarial Challenger Test Suite: Milestone 5
In-Game Lua Automation Script (gentahax_mass.lua) & Bridge Integration Hardening.

4-Tier E2E Stress Verification:
- Tier 1: Feature coverage (all 14 states, state transition table, pure ASCII compliance, static rules).
- Tier 2: Boundary & edge cases (0 tiles, 5,586 full world tiles, exactly 5,000 drop threshold overflow, corrupt tile inputs).
- Tier 3: Combinatorial & concurrency resilience (rapid concurrent HTTP /save_state, corrupt mass_state.json, atomic replacement, dt clamping, token bucket throttling).
- Tier 4: Real-world anti-ban & crash recovery simulation (moderator presence during planting/harvesting, client sudden restart mid-splicing with ground-truth tile reconciliation).

mr_berk edition
"""

import concurrent.futures
import json
import os
import re
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import bridge as B
import logistics as LOG

LUA_SCRIPT_PATH = REPO_ROOT / "scripts" / "gentahax_mass.lua"

try:
    import lupa
    HAS_LUPA = True
except ImportError:
    HAS_LUPA = False


def create_mock_gentahax_lua_runtime():
    """Initializes a sandboxed Lupa LuaRuntime with simulated GENTAHAX v5.61 engine APIs."""
    if not HAS_LUPA:
        raise unittest.SkipTest("lupa library is not installed in the environment.")

    lua = lupa.LuaRuntime(unpack_returned_tuples=True)

    setup_code = """
    _G._MOCK_STATE = {
        world_name = "GROW_FARM1",
        world_width = 100,
        world_height = 60,
        player_x = 1600,
        player_y = 736,
        tiles = {},
        extra_tiles = {},
        inventory = {
            {id = 3, amount = 300},
            {id = 5, amount = 300},
            {id = 101, amount = 0},
            {id = 100, amount = 0}
        },
        dropped_objects = {},
        packets_sent = {},
        hooks = {},
        toasts = {},
        console_logs = {},
        tile_changes = {},
        button_clicks = {},
        player_list = {
            {name = "mr_berk", status = "PLAYER"},
            {name = "Gamer123", status = "PLAYER"}
        }
    }

    -- Initialize empty tiles (100x60)
    for y = 0, 59 do
        for x = 0, 99 do
            local key = x .. "_" .. y
            _G._MOCK_STATE.tiles[key] = {
                fg = 0,
                bg = 8,
                isCollideable = (y == 20),
                x = x,
                y = y
            }
        end
    end

    AddHook = function(ev, label, fn)
        _G._MOCK_STATE.hooks[label] = {event = ev, fn = fn}
    end

    RemoveHook = function(label)
        _G._MOCK_STATE.hooks[label] = nil
    end

    getWorld = function()
        return {
            name = _G._MOCK_STATE.world_name,
            width = _G._MOCK_STATE.world_width,
            height = _G._MOCK_STATE.world_height
        }
    end

    getLocal = function()
        return {
            name = "mr_berk",
            pos = {x = _G._MOCK_STATE.player_x, y = _G._MOCK_STATE.player_y},
            gems = 15000
        }
    end

    GetLocal = getLocal

    getInventory = function()
        return _G._MOCK_STATE.inventory
    end

    GetInventory = getInventory

    checkTile = function(x, y)
        local key = x .. "_" .. y
        return _G._MOCK_STATE.tiles[key]
    end

    getExtraTile = function(x, y)
        local key = x .. "_" .. y
        return _G._MOCK_STATE.extra_tiles[key] or {ready = false, growth = 3600, fruitCount = 0}
    end

    getItemByID = function(id)
        if id == 3 then return {name = "Dirt Seed", growth = 31}
        elseif id == 5 then return {name = "Lava Seed", growth = 120}
        elseif id == 101 then return {name = "Wood Tree", growth = 220}
        elseif id == 100 then return {name = "Wood Block", growth = 0}
        end
        return {name = "Unknown Item", growth = 3600}
    end

    getWorldObject = function()
        return _G._MOCK_STATE.dropped_objects
    end

    findPath = function(x, y)
        _G._MOCK_STATE.player_x = x * 32
        _G._MOCK_STATE.player_y = y * 32
        return true
    end

    checkPath = function(x, y)
        return true
    end

    requestTileChange = function(x, y, item_id)
        local key = x .. "_" .. y
        table.insert(_G._MOCK_STATE.tile_changes, {x = x, y = y, id = item_id})
        if _G._MOCK_STATE.tiles[key] then
            _G._MOCK_STATE.tiles[key].fg = item_id
        end
    end

    requestCollect = function(x, y, item_id)
        return true
    end

    requestCollectByRange = function(range)
        return true
    end

    sendPacket = function(type_id, text)
        table.insert(_G._MOCK_STATE.packets_sent, {type = type_id, text = text})
    end

    SendPacket = sendPacket

    doToast = function(toastType, dismissTime, text)
        table.insert(_G._MOCK_STATE.toasts, {type = toastType, time = dismissTime, text = text})
    end

    logToConsole = function(text)
        table.insert(_G._MOCK_STATE.console_logs, text)
    end

    getPlayerlist = function()
        return _G._MOCK_STATE.player_list
    end

    ImGui = {
        Col = {Button = 0, ButtonHovered = 1, ButtonActive = 2},
        Begin = function(title) return true end,
        End = function() end,
        TextUnformatted = function(text) end,
        Separator = function() end,
        SameLine = function() end,
        ProgressBar = function(frac, size, overlay) end,
        Checkbox = function(label, current) return current end,
        Button = function(label) return _G._MOCK_STATE.button_clicks[label] == true end,
        PushStyleColor = function(col, val) end,
        PopStyleColor = function(count) end
    }
    """
    lua.execute(setup_code)
    return lua


# ==============================================================================
# TIER 1: FEATURE COVERAGE, STATE MACHINE & STATIC COMPLIANCE
# ==============================================================================

class TestM5Tier1FeatureCoverageAndStaticIntegrity(unittest.TestCase):
    """Tier 1: Probes static code constraints, ASCII validity, and all 14 state definitions."""

    def setUp(self):
        self.assertTrue(LUA_SCRIPT_PATH.exists(), f"Target script not found: {LUA_SCRIPT_PATH}")
        self.raw_bytes = LUA_SCRIPT_PATH.read_bytes()
        self.source_code = self.raw_bytes.decode("ascii")

    def test_pure_ascii_strict_byte_validation(self):
        """Validates that 100% of characters in gentahax_mass.lua are pure ASCII (0..127)."""
        non_ascii_bytes = [(idx, b) for idx, b in enumerate(self.raw_bytes) if b > 127]
        self.assertEqual(
            len(non_ascii_bytes), 0,
            f"Adversarial Failure: Found {len(non_ascii_bytes)} non-ASCII bytes. Strictly zero allowed."
        )

    def test_zero_turkish_characters_in_strings_and_comments(self):
        """Scans for all 12 Turkish characters (both lower and upper case)."""
        banned_turkish_chars = ["ğ", "ü", "ş", "ı", "ö", "ç", "İ", "Ğ", "Ü", "Ş", "Ö", "Ç"]
        found_violations = {}
        for ch in banned_turkish_chars:
            cnt = self.source_code.count(ch)
            if cnt > 0:
                found_violations[ch] = cnt

        self.assertEqual(
            len(found_violations), 0,
            f"Adversarial Failure: Turkish characters detected in Lua script: {found_violations}"
        )

    def test_mandatory_header_and_imgui_watermark(self):
        """Verifies exact mandatory repository header and ImGui watermark."""
        expected_header = "-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp"
        lines = self.source_code.strip().splitlines()
        self.assertEqual(lines[0], expected_header, "Script does not begin with mandatory repo header comment.")

        watermark_pattern = r'ImGui\.Separator\(\)\s*ImGui\.TextUnformatted\("By BrK \| Discord : mr_berk\."\)\s*ImGui\.End\(\)'
        self.assertRegex(self.source_code, watermark_pattern, "Mandatory ImGui watermark missing before ImGui.End().")

    def test_zero_concurrency_stack_violations_rule_7(self):
        """Verifies zero background runThread calls, zero sleep calls, and zero pcall protected calls."""
        clean_lines = [
            line.strip() for line in self.source_code.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        clean_code = "\n".join(clean_lines)

        self.assertNotIn("runThread", clean_code, "Rule 7 violation: runThread found in active code.")
        self.assertNotIn("sleep(", clean_code, "Rule 7 violation: sleep( found in active code.")
        self.assertNotIn("pcall(", clean_code, "Rule 7 violation: pcall( found in active code.")

    def test_all_14_states_contiguous_and_uniquely_indexed(self):
        """Validates that all 14 states (0 through 13) are defined and contiguous."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(self.source_code)

        for state_id in range(14):
            pattern = rf"local\s+STATE_{state_id}_\w+\s*=\s*{state_id}"
            self.assertRegex(self.source_code, pattern, f"State {state_id} constant definition missing.")

    def test_complete_state_machine_transition_table_cycle(self):
        """Simulates and verifies full state transitions across states 0..13."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(self.source_code)

        # 0 -> 1: Click start mass
        engine.active_state = 0
        lua.globals()._MOCK_STATE.button_clicks["[ Start Mass ]"] = True
        engine.on_render_hook(0.016)
        self.assertEqual(engine.active_state, 1, "Must transition from 0 (IDLE) to 1 (LOAD_PERSISTENCE)")

        # 1 -> 2: Load persistence without live farm world match
        lua.globals()._MOCK_STATE.world_name = "STORAGE_WORLD"
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 2, "Must transition from 1 to 2 (WARP_TARGET_SCAN)")

        # 2 -> 3: Warp to farm, stabilize and scan
        lua.globals()._MOCK_STATE.world_name = "GROW_FARM1"
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 3, "Must transition from 2 to 3 (WARP_STORAGE_A)")

        # 3 -> 4: Warp to Storage A, stabilize
        engine.storage_world_a = "VAULT_A"
        lua.globals()._MOCK_STATE.world_name = "VAULT_A"
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 4, "Must transition from 3 to 4 (COLLECT_SEED_A)")

        # 4 -> 5: Seed A satisfied (300 in inventory) -> warp to Storage B
        lua.globals()._MOCK_STATE.inventory = lua.eval('{{id = 3, amount = 300}, {id = 5, amount = 0}}')
        engine.required_seeds = 300
        engine.storage_world_b = "VAULT_B"
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 5, "Must transition from 4 to 5 (WARP_STORAGE_B)")

        # 5 -> 6: Seed B satisfied (300 in inventory) -> warp to Farm
        lua.globals()._MOCK_STATE.world_name = "VAULT_B"
        lua.globals()._MOCK_STATE.inventory = lua.eval('{{id = 3, amount = 300}, {id = 5, amount = 300}}')
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 6, "Must transition from 5 to 6 (WARP_FARM_PLANT_A)")

        # 6 -> 7: Stabilize in Farm -> begin planting Seed A
        lua.globals()._MOCK_STATE.world_name = "GROW_FARM1"
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 7, "Must transition from 6 to 7 (PLANTING_SEED_A)")

        # 7 -> 8: Finish planting Base Seed A -> transition to splicing Seed B
        engine.valid_tiles = lua.eval('{ {x = 10, y = 20} }')
        engine.plant_index = 2  # Already completed
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 8, "Must transition from 7 to 8 (SPLICING_SEED_B)")

        # 8 -> 9: Finish splicing Seed B -> transition to waiting maturation
        engine.planted_base_coords = lua.eval('{ {x = 10, y = 20} }')
        engine.splice_index = 2  # Already completed
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 9, "Must transition from 8 to 9 (WAIT_MATURATION)")

        # 9 -> 10: Countdown reaches 0 -> transition to ready to harvest
        engine.growth_remaining = 0.1
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 10, "Must transition from 9 to 10 (READY_TO_HARVEST)")

        # 10 -> 11: Operator clicks dynamic harvest button
        lua.globals()._MOCK_STATE.button_clicks["[ HARVEST ET ]"] = True
        engine.on_render_hook(0.016)
        self.assertEqual(engine.active_state, 11, "Must transition from 10 to 11 (HARVESTING)")

        # 11 -> 12: Finish harvesting trees -> transition to designated dropping
        engine.harvest_index = 2
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 12, "Must transition from 11 to 12 (DESIGNATED_DROPPING)")

        # 12 -> 13: Drop complete and no more trees -> mission complete
        engine.drop_zone.world = "GROW_FARM1"
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0
        lua.globals()._MOCK_STATE.inventory = lua.eval('{{id = 100, amount = 0}}')
        engine.harvest_index = 2
        engine.planted_base_coords = lua.eval('{ {x = 10, y = 20} }')
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 13, "Must transition from 12 to 13 (MISSION_COMPLETE)")

        # 13 -> 0: Mission complete resets to IDLE
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 0, "Must reset from 13 back to 0 (IDLE)")


# ==============================================================================
# TIER 2: BOUNDARY & EXTREME EDGE CASES
# ==============================================================================

class TestM5Tier2BoundaryAndEdgeCases(unittest.TestCase):
    """Tier 2: Probes 0 tiles, 5,586 full world tiles, exactly 5,000 drop threshold, invalid tile inputs."""

    @classmethod
    def setUpClass(cls):
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        cls.lua = create_mock_gentahax_lua_runtime()
        cls.engine = cls.lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

    def test_zero_capacity_world_transitions_safely(self):
        """When farm capacity is 0 (no valid soil), engine must not crash or infinite loop."""
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))
        # Script preloads mass_state.json on launch (crash recovery); earlier tests
        # may have left one behind, so start this scenario from a clean slate.
        engine.planted_base_coords = lua.table()
        engine.valid_tiles = lua.table()

        # Empty air world with only_above_block = true -> 0 tiles found
        for y in range(60):
            for x in range(100):
                lua.globals()._MOCK_STATE.tiles[f"{x}_{y}"] = lua.table(fg=0, bg=0, isCollideable=False, x=x, y=y)

        engine.active_state = 2  # WARP_TARGET_SCAN
        engine.farm_world = "GROW_FARM1"
        lua.globals()._MOCK_STATE.world_name = "GROW_FARM1"
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0

        engine.on_tick_step(0.500)

        self.assertEqual(engine.scanned_capacity, 0, "Capacity must be exactly 0.")
        self.assertEqual(len(engine.valid_tiles), 0, "Valid tiles list must be empty.")
        self.assertEqual(engine.active_state, 3, "Must advance to State 3 safely.")

        # Progress through States 7 and 8 with 0 tiles
        engine.active_state = 7  # PLANTING_SEED_A
        engine.plant_index = 1
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 8, "State 7 with 0 tiles must advance immediately to State 8.")

        engine.splice_index = 1
        engine.on_tick_step(0.500)
        self.assertEqual(engine.active_state, 9, "State 8 with 0 tiles must advance immediately to State 9.")

    def test_full_world_5586_tiles_scan_and_json_roundtrip(self):
        """Scans max world grid (98 x 57 = 5,586 tiles) and verifies JSON encode/decode integrity and speed."""
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        # Setup all 98 x 57 interior tiles as empty air with only_above_block = false
        cap, tiles = engine.scan_farm_grid(False)
        self.assertEqual(cap, 5586, f"Full interior world must yield exactly 5,586 tiles (got {cap}).")
        self.assertEqual(len(tiles), 5586)

        # Benchmark JSON encode of 5,586 tiles
        start_t = time.perf_counter()
        engine.valid_tiles = tiles
        serialized = engine.json_encode(tiles)
        encode_duration = time.perf_counter() - start_t

        self.assertLess(encode_duration, 0.100, f"JSON encoding 5,586 tiles took {encode_duration:.4f}s (> 100ms benchmark).")
        self.assertTrue(serialized.startswith("["), "Encoded JSON must be an array.")
        self.assertTrue(serialized.endswith("]"), "Encoded JSON must end with bracket.")

        # Benchmark JSON decode of 5,586 tiles
        start_decode_t = time.perf_counter()
        decoded = engine.json_decode(serialized)
        decode_duration = time.perf_counter() - start_decode_t

        self.assertLess(decode_duration, 0.100, f"JSON decoding 5,586 tiles took {decode_duration:.4f}s (> 100ms benchmark).")
        self.assertEqual(len(decoded), 5586, "Decoded array must contain exactly 5,586 tile elements.")
        self.assertEqual(decoded[1].x, 1)
        self.assertEqual(decoded[1].y, 1)

    def test_exactly_5000_drop_threshold_multi_overflow(self):
        """
        Adversarial drop overflow test:
        - Tile at 4,950 items.
        - Bot holds 100 items.
        - First action drops exactly 50 items (4,950 + 50 = 5,000 threshold reached).
        - Next tick detects 5,000 limit, advances to (x + 1, y), and resets count to 0.
        - Subsequent action drops remaining 50 items on new tile (count = 50).
        """
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 12  # DESIGNATED_DROPPING
        engine.drop_zone.world = "DROP_VAULT"
        engine.drop_zone.x = 50
        engine.drop_zone.y = 23
        engine.drop_zone.count = 4950
        engine.drop_zone.limit = 5000
        engine.target_block_id = 100
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0
        lua.globals()._MOCK_STATE.world_name = "DROP_VAULT"

        # Inventory holds 100 blocks
        lua.globals()._MOCK_STATE.inventory = lua.eval('{{id = 100, amount = 100}}')

        # Tick 1: drops min(100, 5000 - 4950) = 50 items
        engine.on_tick_step(0.500)
        self.assertEqual(engine.drop_zone.count, 5000, "Count must reach exactly 5,000.")
        self.assertEqual(engine.drop_zone.x, 50, "Coordinate must not advance yet on same tick.")

        # Mock inventory update: 50 items were dropped, 50 remain
        lua.globals()._MOCK_STATE.inventory = lua.eval('{{id = 100, amount = 50}}')

        # Tick 2: detects count >= limit (5000 >= 5000) -> advances x to 51, resets count to 0
        engine.on_tick_step(0.500)
        self.assertEqual(engine.drop_zone.x, 51, "Coordinate must advance to 51 upon reaching threshold.")
        self.assertEqual(engine.drop_zone.count, 0, "Count must be reset to 0.")

        # Tick 3: drops remaining 50 items on new tile (51, 23)
        engine.on_tick_step(0.500)
        self.assertEqual(engine.drop_zone.x, 51)
        self.assertEqual(engine.drop_zone.count, 50, "New tile count must reflect 50 dropped items.")

    def test_corrupt_tile_inputs_gracefully_handled(self):
        """Probes engine resilience against malformed checkTile and getExtraTile responses."""
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_extras = lua.globals()._MOCK_STATE.extra_tiles

        # Corrupted tile entries: nil, number, string, missing fg, missing isCollideable
        mock_tiles["10_20"] = None
        mock_tiles["11_20"] = 12345
        mock_tiles["12_20"] = "corrupt_string"
        mock_tiles["13_20"] = lua.table(bg=8)  # missing fg
        mock_tiles["14_20"] = lua.table(fg=2)  # missing isCollideable

        mock_extras["10_20"] = None
        mock_extras["11_20"] = 99999

        # Ensure is_valid_soil_block handles these without throwing Lua errors
        self.assertFalse(engine.is_valid_soil_block(10, 19))
        self.assertFalse(engine.is_valid_soil_block(11, 19))
        self.assertFalse(engine.is_valid_soil_block(12, 19))
        self.assertFalse(engine.is_valid_soil_block(13, 19))
        self.assertTrue(engine.is_valid_soil_block(14, 19))  # fg=2 defaults to valid when isCollideable is nil


# ==============================================================================
# TIER 3: CONCURRENCY & COMBINATORIAL RESILIENCE
# ==============================================================================

class TestM5Tier3CombinatorialAndConcurrencyResilience(unittest.TestCase):
    """Tier 3: Rapid concurrent /save_state requests, corrupt JSON, atomic replacement, dt clamping."""

    @classmethod
    def setUpClass(cls):
        cls.port = 8845
        B.start_http_relay(port=cls.port)

    def test_rapid_concurrent_save_state_requests(self):
        """Blasts /save_state with 50 concurrent worker threads to verify atomic replacement without corruption."""
        url = f"http://127.0.0.1:{self.port}/save_state"

        def send_state_worker(worker_id: int):
            payload = {
                "worker_id": worker_id,
                "world": f"FARM_THREAD_{worker_id}",
                "active_state": 7,
                "scanned_capacity": 300 + worker_id,
                "timestamp": time.time()
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return resp.status, body

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_state_worker, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All 50 requests must succeed with HTTP 200 and ok=True
        for status, body in results:
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertTrue(body.get("atomic"))

        # Verify disk mass_state.json exists and is 100% valid JSON
        req_get = urllib.request.Request(f"http://127.0.0.1:{self.port}/get_state")
        with urllib.request.urlopen(req_get, timeout=3.0) as resp_get:
            self.assertEqual(resp_get.status, 200)
            data_on_disk = json.loads(resp_get.read().decode("utf-8"))
            self.assertIn("FARM_THREAD_", data_on_disk.get("world", ""))

    def test_corrupt_json_persistence_graceful_recovery(self):
        """Probes Lua json_decode with corrupt, truncated, and binary inputs."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        malformed_inputs = [
            "",
            "{",
            "{\"farm_world\": \"UNFINISHED",
            "[1, 2, ",
            "{\"capacity\": not_a_number}",
            "null",
            "--- INVALID LUA COMMENTS ---",
            "{'single_quotes': 1}",
            "\x00\x01\x02\x03\xff\xfe"
        ]

        for bad in malformed_inputs:
            # Must return nil or empty table without throwing Lua syntax/stack errors
            try:
                res = engine.json_decode(bad)
                # Success: decoded safely without exception
            except Exception as e:
                self.fail(f"Adversarial failure: json_decode crashed on input '{bad[:20]}': {e}")

    def test_extreme_dt_clamping_in_on_render_hook(self):
        """Validates that negative dt, 0 dt, or massive lag spike dt (>0.5s) are safely clamped to 0.016s."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        initial_timer = engine.tick_timer

        # Massive 10.0s lag spike
        engine.on_render_hook(10.0)
        self.assertAlmostEqual(engine.tick_timer, initial_timer + 0.016, delta=0.001)

        # Negative dt (-0.5s)
        engine.on_render_hook(-0.5)
        self.assertAlmostEqual(engine.tick_timer, initial_timer + 0.032, delta=0.001)

        # Zero dt
        engine.on_render_hook(0.0)
        self.assertAlmostEqual(engine.tick_timer, initial_timer + 0.048, delta=0.001)

    def test_token_bucket_burst_packet_flood_suppression(self):
        """Simulates 20 rapid packet dispatch attempts; must strictly throttle to <= 3.5 packets/sec."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        lua.globals()._MOCK_STATE.packets_sent = lua.table()

        # Engine starts with 3.5 tokens and last_packet_time = 0
        # Start burst test at t = 1.000s (initial packet allowed, subsequent burst within 100ms throttled)
        dispatched_count = 0
        base_t = 1.000
        for i in range(10):
            t = base_t + (i * 0.010)  # 10ms increments (violates 220ms minimum spacing)
            # Execute token bucket check through Lua state
            ok = lua.eval(f"""
            (function()
                return GH_MASS_ENGINE.anti_ban.tokens >= 1.0 and ({t} - GH_MASS_ENGINE.anti_ban.last_packet_time) >= GH_MASS_ENGINE.anti_ban.min_inter_packet_delay
            end)()
            """)
            if ok:
                dispatched_count += 1
                engine.anti_ban.tokens = engine.anti_ban.tokens - 1.0
                engine.anti_ban.last_packet_time = t

        # Even with 3.5 initial tokens, only 1 packet can be sent because min_inter_packet_delay is 220ms!
        self.assertEqual(dispatched_count, 1, "Inter-packet delay (< 220ms) must block all burst packets.")


# ==============================================================================
# TIER 4: REAL-WORLD ANTI-BAN & CRASH RECOVERY SIMULATION
# ==============================================================================

class TestM5Tier4RealWorldSimulationAndAntiBan(unittest.TestCase):
    """Tier 4: Moderator entrance during planting/harvesting, client restart mid-splicing with map reconciliation."""

    def test_moderator_entrance_during_planting_triggers_immediate_halt(self):
        """
        Adversarial Test:
        While in STATE_7_PLANTING_SEED_A, a moderator joins the world.
        Engine must immediately halt to STATE_0_IDLE and dispatch zero further tile changes.
        """
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        # Setup solid soil at y=20 so tile (10, 19) is plantable
        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_tiles["10_20"] = lua.table(fg=2, bg=8, isCollideable=True, x=10, y=20)
        mock_tiles["11_20"] = lua.table(fg=2, bg=8, isCollideable=True, x=11, y=20)
        mock_tiles["12_20"] = lua.table(fg=2, bg=8, isCollideable=True, x=12, y=20)

        engine.active_state = 7  # PLANTING_SEED_A
        engine.plant_index = 1
        engine.valid_tiles = lua.eval('{ {x = 10, y = 19}, {x = 11, y = 19}, {x = 12, y = 19} }')

        # Plant first tile normally
        engine.on_tick_step(0.500)
        self.assertEqual(len(lua.globals()._MOCK_STATE.tile_changes), 1)

        # Moderator enters the world!
        lua.globals()._MOCK_STATE.player_list = lua.eval('{ {name = "mr_berk"}, {name = "`4[MOD] @UbisoftAdmin"} }')

        # Run next tick step
        engine.on_tick_step(0.500)

        # Engine must be halted in STATE_0_IDLE
        self.assertEqual(engine.active_state, 0, "Moderator detection must halt active state to 0.")
        self.assertTrue(engine.anti_ban.mod_detected, "mod_detected flag must be true.")
        self.assertIn("EMERGENCY HALT", engine.status_message)

        # Tile changes must NOT have increased!
        self.assertEqual(len(lua.globals()._MOCK_STATE.tile_changes), 1, "Zero further tile actions permitted.")

    def test_client_sudden_restart_mid_splicing_reconciles_and_skips_duplicates(self):
        """
        Adversarial Stress Test:
        - 300 Base Seed A saplings planted.
        - 142 trees spliced with Seed B before client crashes.
        - Client restarts: engine re-initialized from scratch.
        - Ground truth reconciliation scans map:
          - Detects 142 spliced trees (fg = 101).
          - Detects 158 unspliced Base Seed A saplings (fg = 3).
        - State machine resumes at STATE_8_SPLICING_SEED_B.
        - Iterates over tiles:
          - Tiles 1..142: c.fg == 101 -> skipped!
          - Tiles 143..300: c.fg == 3 -> spliced!
        - Total spliced actions = exactly 158! Zero double-splicing!
        """
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.farm_world = "GROW_FARM1"
        engine.seed_a_id = 3
        engine.seed_b_id = 5
        engine.target_tree_id = 101

        # Build 300 test tiles
        valid_tiles_lua = "{"
        mock_tiles = lua.globals()._MOCK_STATE.tiles
        for i in range(1, 301):
            x = (i % 50) + 1
            y = (i // 50) + 10
            key = f"{x}_{y}"
            valid_tiles_lua += f"{{x = {x}, y = {y}}},"

            if i <= 142:
                # 142 already spliced trees
                mock_tiles[key] = lua.table(fg=101, bg=8, isCollideable=False, x=x, y=y)
            else:
                # 158 unspliced Base Seed A saplings
                mock_tiles[key] = lua.table(fg=3, bg=8, isCollideable=False, x=x, y=y)

        valid_tiles_lua += "}"
        engine.valid_tiles = lua.eval(valid_tiles_lua)

        # Execute Ground-Truth Tile Reconciliation
        ok, phase = engine.reconcile_live_tiles()

        self.assertTrue(ok)
        self.assertEqual(phase, "SPLICING_SEED_B")
        self.assertEqual(engine.active_state, 8, "Must reconcile to STATE_8_SPLICING_SEED_B.")
        self.assertEqual(len(engine.planted_base_coords), 300)

        # Clear tile change tracking
        lua.globals()._MOCK_STATE.tile_changes = lua.table()

        # Step through the 300 tiles
        for step in range(300):
            if engine.active_state != 8:
                break
            engine.on_tick_step(0.500)

        # Count how many tile placements were dispatched
        tile_changes = list(lua.globals()._MOCK_STATE.tile_changes.values())
        spliced_placements = [tc for tc in tile_changes if tc.id == 5]

        self.assertEqual(
            len(spliced_placements), 158,
            f"Adversarial Failure: Expected exactly 158 Seed B placements, got {len(spliced_placements)}."
        )

        # Verify that all 300 tiles now have target_tree_id or Seed B placed
        for i in range(1, 301):
            x = (i % 50) + 1
            y = (i // 50) + 10
            key = f"{x}_{y}"
            fg = mock_tiles[key].fg
            self.assertIn(fg, (5, 101), f"Tile ({x}, {y}) was not spliced (fg={fg}).")

    def test_sudden_restart_with_mature_trees_reconciles_to_state_10(self):
        """When client restarts and trees are already mature, reconciles directly to STATE_10_READY_TO_HARVEST."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.farm_world = "GROW_FARM1"
        engine.target_tree_id = 101
        engine.valid_tiles = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20} }')

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_extras = lua.globals()._MOCK_STATE.extra_tiles

        mock_tiles["10_20"] = lua.table(fg=101, bg=8, isCollideable=False, x=10, y=20)
        mock_extras["10_20"] = lua.table(ready=True, growth=0)

        mock_tiles["11_20"] = lua.table(fg=101, bg=8, isCollideable=False, x=11, y=20)
        mock_extras["11_20"] = lua.table(ready=True, growth=0)

        ok, phase = engine.reconcile_live_tiles()

        self.assertTrue(ok)
        self.assertEqual(phase, "READY_TO_HARVEST")
        self.assertEqual(engine.active_state, 10, "Must reconcile directly to State 10.")
        self.assertTrue(engine.ready_to_harvest)

    def test_moderator_entrance_during_harvesting_halts_engine(self):
        """When moderator enters during STATE_11_HARVESTING, engine halts immediately to STATE_0_IDLE."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 11  # HARVESTING
        engine.harvest_index = 1
        engine.planted_base_coords = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20} }')

        # Moderator enters the world
        lua.globals()._MOCK_STATE.player_list = lua.eval('{ {name = "mr_berk"}, {name = "UbisoftGuardian"} }')

        engine.on_tick_step(0.500)

        self.assertEqual(engine.active_state, 0, "Moderator entrance must halt harvesting to STATE_0_IDLE.")
        self.assertTrue(engine.anti_ban.mod_detected)
        self.assertIn("EMERGENCY HALT", engine.status_message)

    def test_no_false_positive_moderator_detection_on_normal_players(self):
        """Normal players with substrings like 'mod' in their name must NOT trigger false positive halts."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        # Setup solid soil at y=20 so tile (10, 19) is plantable
        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_tiles["10_20"] = lua.table(fg=2, bg=8, isCollideable=True, x=10, y=20)
        mock_tiles["11_20"] = lua.table(fg=2, bg=8, isCollideable=True, x=11, y=20)

        engine.active_state = 7  # PLANTING_SEED_A
        engine.plant_index = 1
        engine.valid_tiles = lua.eval('{ {x = 10, y = 19}, {x = 11, y = 19} }')

        # Innocent players containing 'mod' substrings (ModernGamer, Commodore64, ModelWorker)
        lua.globals()._MOCK_STATE.player_list = lua.eval('{ {name = "mr_berk", status = "PLAYER"}, {name = "ModernGamer", status = "PLAYER"}, {name = "Commodore64", status = "PLAYER"}, {name = "ModelWorker", status = "PLAYER"} }')

        engine.on_tick_step(0.500)

        # Engine must NOT halt
        self.assertFalse(engine.anti_ban.mod_detected, "Normal player names must not trigger false positive mod detection.")
        self.assertIn(engine.active_state, (7, 8), "Engine must continue normal operation.")

    def test_console_varlist_moderator_broadcast_halts_engine(self):
        """OnVarlist console messages with [MOD], Moderator, Guardian must trigger emergency halt."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        test_messages = [
            "`4[MOD] `oUbisoft Moderator entered world.",
            "`cModerator `4Gamer `ois inspecting the area.",
            "`2A Guardian `ohas entered to protect this realm."
        ]

        for msg in test_messages:
            engine.active_state = 7
            engine.anti_ban.mod_detected = False
            varlist = lua.eval(f'{{[0] = "OnConsoleMessage", [1] = "{msg}"}}')
            engine.on_varlist_handler(varlist)

            self.assertEqual(engine.active_state, 0, f"Message '{msg}' failed to halt engine.")
            self.assertTrue(engine.anti_ban.mod_detected)

    def test_destroyed_sapling_mid_splicing_skipped_without_waste(self):
        """In STATE_8_SPLICING_SEED_B, if a tile's Base Seed A was broken (fg=0), it must be skipped without placing Seed B."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 8  # SPLICING_SEED_B
        engine.splice_index = 1
        engine.seed_a_id = 3
        engine.seed_b_id = 5
        engine.target_tree_id = 101

        # Tile 1: valid Seed A (fg = 3)
        # Tile 2: broken/empty (fg = 0)
        # Tile 3: valid Seed A (fg = 3)
        engine.planted_base_coords = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20}, {x = 12, y = 20} }')

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_tiles["10_20"] = lua.table(fg=3, bg=8, isCollideable=False, x=10, y=20)
        mock_tiles["11_20"] = lua.table(fg=0, bg=8, isCollideable=False, x=11, y=20)  # Broken!
        mock_tiles["12_20"] = lua.table(fg=3, bg=8, isCollideable=False, x=12, y=20)

        lua.globals()._MOCK_STATE.tile_changes = lua.table()

        # Step 1: Tile 1 (spliced with Seed B)
        engine.on_tick_step(0.500)
        self.assertEqual(len(lua.globals()._MOCK_STATE.tile_changes), 1)

        # Step 2: Tile 2 (Seed A missing -> must skip without tile change!)
        engine.on_tick_step(0.500)
        self.assertEqual(len(lua.globals()._MOCK_STATE.tile_changes), 1, "Tile 2 (fg=0) must be skipped without dispatching placement.")

        # Step 3: Tile 3 (valid Seed A -> spliced with Seed B)
        engine.on_tick_step(0.500)
        self.assertEqual(len(lua.globals()._MOCK_STATE.tile_changes), 2, "Tile 3 must be spliced normally.")

    def test_boustrophedon_snake_sweep_ordering(self):
        """Farm capacity scan must follow snake order: Row 1 L->R (1..98), Row 2 R->L (98..1), Row 3 L->R."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        cap, tiles = engine.scan_farm_grid(False)

        # Row 1 (y = 1) must have x starting at 1 and ending at 98
        self.assertEqual(tiles[1].x, 1)
        self.assertEqual(tiles[1].y, 1)
        self.assertEqual(tiles[98].x, 98)
        self.assertEqual(tiles[98].y, 1)

        # Row 2 (y = 2) must have x starting at 98 and ending at 1
        self.assertEqual(tiles[99].x, 98)
        self.assertEqual(tiles[99].y, 2)
        self.assertEqual(tiles[196].x, 1)
        self.assertEqual(tiles[196].y, 2)

        # Row 3 (y = 3) must reverse back: starting at 1
        self.assertEqual(tiles[197].x, 1)
        self.assertEqual(tiles[197].y, 3)

    def test_concurrent_save_and_get_state_no_race_condition(self):
        """Simultaneous concurrent reads and writes to /save_state and /get_state never return corrupt JSON."""
        port = 8846
        B.start_http_relay(port=port)

        url_save = f"http://127.0.0.1:{port}/save_state"
        url_get = f"http://127.0.0.1:{port}/get_state"

        def writer(idx: int):
            payload = {"write_id": idx, "world": f"WORLD_{idx}", "active_state": 7, "capacity": idx * 10}
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url_save, data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status == 200

        def reader(idx: int):
            req = urllib.request.Request(url_get)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw)
                return isinstance(parsed, dict)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            write_futures = [executor.submit(writer, i) for i in range(25)]
            read_futures = [executor.submit(reader, i) for i in range(25)]

            for wf in concurrent.futures.as_completed(write_futures):
                self.assertTrue(wf.result())

            for rf in concurrent.futures.as_completed(read_futures):
                self.assertTrue(rf.result(), "Concurrent get_state read returned invalid or unparseable JSON.")

    def test_save_state_corrupt_payload_handling(self):
        """Posting invalid or empty JSON to /save_state returns HTTP 200 with ok=False without crashing relay."""
        port = 8847
        B.start_http_relay(port=port)

        url_save = f"http://127.0.0.1:{port}/save_state"

        corrupt_payloads = [
            b"",
            b"not_json",
            b"{\"unclosed\":",
            b"null"
        ]

        for payload in corrupt_payloads:
            req = urllib.request.Request(url_save, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertFalse(body.get("ok"), "Corrupt payload must result in ok: False response.")


if __name__ == "__main__":
    unittest.main()

