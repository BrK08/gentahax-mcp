#!/usr/bin/env python3
"""
Comprehensive Unit and Simulation Test Suite for GENTAHAX-MCP Milestone 3 & 4:
In-Game Lua Automation Script (gentahax_mass.lua), 14-State Machine, ImGui HUD,
Anti-Ban Matrix, Crash Recovery, Two-Stage Splicing & Designated Dropping.

mr_berk edition
"""

import json
import os
import re
import sys
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Set up workspace path
REPO_ROOT = Path(__file__).resolve().parent.parent
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

    # Establish mock game environment
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
            {id = 100, amount = 0}
        },
        dropped_objects = {},
        packets_sent = {},
        hooks = {},
        toasts = {},
        console_logs = {},
        imgui_render_calls = 0,
        button_clicks = {}
    }

    -- Initialize empty tiles
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
        return _G._MOCK_STATE.tiles[key] or {fg = 0, bg = 0, isCollideable = false, x = x, y = y}
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
        return {
            {name = "mr_berk", status = "PLAYER"},
            {name = "Gamer123", status = "PLAYER"}
        }
    end

    ImGui = {
        Col = {Button = 0, ButtonHovered = 1, ButtonActive = 2},
        Begin = function(title) return true end,
        End = function() end,
        TextUnformatted = function(text) end,
        Separator = function() end,
        SameLine = function() end,
        ProgressBar = function(frac, size, overlay) end,
        Checkbox = function(label, current)
            return current
        end,
        Button = function(label)
            return _G._MOCK_STATE.button_clicks[label] == true
        end,
        PushStyleColor = function(col, val) end,
        PopStyleColor = function(count) end
    }
    """
    lua.execute(setup_code)
    return lua


class TestScriptStaticIntegrity(unittest.TestCase):
    """Verifies strict static code constraints, ASCII compliance, and watermarks."""

    def setUp(self):
        self.assertTrue(LUA_SCRIPT_PATH.exists(), f"Target script not found: {LUA_SCRIPT_PATH}")
        self.raw_bytes = LUA_SCRIPT_PATH.read_bytes()
        self.source_code = self.raw_bytes.decode("ascii")

    def test_pure_ascii_compliance(self):
        """Validates that 100% of characters are pure ASCII (0..127) with no Turkish characters."""
        non_ascii = [(idx, b) for idx, b in enumerate(self.raw_bytes) if b > 127]
        self.assertEqual(
            len(non_ascii), 0,
            f"Found {len(non_ascii)} non-ASCII byte(s) in {LUA_SCRIPT_PATH}. Pure ASCII is strictly mandated."
        )

        turkish_chars = ["ğ", "ü", "ş", "ı", "ö", "ç", "İ", "Ğ", "Ü", "Ş", "Ö", "Ç"]
        for ch in turkish_chars:
            self.assertNotIn(ch, self.source_code, f"Turkish character '{ch}' found in Lua source code.")

    def test_mandatory_header_comment(self):
        """Verifies the exact mandatory header comment is at the top of the script."""
        expected_header = "-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp"
        first_line = self.source_code.strip().splitlines()[0]
        self.assertEqual(first_line, expected_header, "Script does not begin with mandatory repo header comment.")

    def test_mandatory_imgui_watermark(self):
        """Verifies the mandatory watermark is rendered immediately prior to ImGui.End()."""
        watermark_pattern = r'ImGui\.Separator\(\)\s*ImGui\.TextUnformatted\("By BrK \| Discord : mr_berk\."\)\s*ImGui\.End\(\)'
        match = re.search(watermark_pattern, self.source_code)
        self.assertIsNotNone(match, "Mandatory ImGui watermark ('By BrK | Discord : mr_berk.') not found before ImGui.End().")

    def test_no_runthread_or_pcall_concurrency_violation(self):
        """Verifies zero background runThread calls and zero pcall protected calls (AGENTS.md Rule 7)."""
        active_lines = [
            line.strip() for line in self.source_code.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        active_code = "\n".join(active_lines)

        self.assertNotIn("runThread(", active_code, "Violates Rule 7: runThread() call found in active Lua code.")
        self.assertNotIn("runThread (", active_code, "Violates Rule 7: runThread () call found in active Lua code.")
        self.assertNotIn("sleep(", active_code, "Violates Rule 7: blocking sleep() call found in active Lua code.")
        self.assertNotIn("sleep (", active_code, "Violates Rule 7: blocking sleep () call found in active Lua code.")
        self.assertNotIn("pcall(", active_code, "Violates Rule 7: pcall() call found in active Lua code.")
        self.assertNotIn("pcall (", active_code, "Violates Rule 7: pcall () call found in active Lua code.")


class Test14StateDefinitionsAndStructure(unittest.TestCase):
    """Verifies complete 14-state machine definitions and mapping."""

    @classmethod
    def setUpClass(cls):
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        cls.lua = create_mock_gentahax_lua_runtime()
        cls.engine = cls.lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

    def test_all_14_states_present_and_indexed(self):
        """Validates that all 14 states (STATE_0 through STATE_13) are defined in the engine."""
        expected_states = [
            (0, "STATE_0_IDLE"),
            (1, "STATE_1_LOAD_PERSISTENCE"),
            (2, "STATE_2_WARP_TARGET_SCAN"),
            (3, "STATE_3_WARP_STORAGE_A"),
            (4, "STATE_4_COLLECT_SEED_A"),
            (5, "STATE_5_WARP_STORAGE_B"),
            (6, "STATE_6_WARP_FARM_PLANT_A"),
            (7, "STATE_7_PLANTING_SEED_A"),
            (8, "STATE_8_SPLICING_SEED_B"),
            (9, "STATE_9_WAIT_MATURATION"),
            (10, "STATE_10_READY_TO_HARVEST"),
            (11, "STATE_11_HARVESTING"),
            (12, "STATE_12_DESIGNATED_DROPPING"),
            (13, "STATE_13_MISSION_COMPLETE")
        ]

        source = LUA_SCRIPT_PATH.read_text(encoding="ascii")
        for state_num, state_name in expected_states:
            pattern = rf"local\s+{state_name}\s*=\s*{state_num}"
            self.assertRegex(source, pattern, f"State definition {state_name} = {state_num} missing.")

    def test_initial_engine_state_is_idle(self):
        """Engine must start in STATE_0_IDLE."""
        self.assertEqual(self.engine.active_state, 0)
        self.assertIn("IDLE", self.engine.status_message)


class TestAntiBanMatrixParametersAndJitter(unittest.TestCase):
    """Validates parameters and heuristics for the 10-vector anti-ban matrix."""

    @classmethod
    def setUpClass(cls):
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")
        cls.lua = create_mock_gentahax_lua_runtime()
        cls.engine = cls.lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

    def test_token_bucket_rate_limiter_parameters(self):
        """Validates token bucket parameters: rate <= 3.5 pkt/s, min inter-packet delay 220ms."""
        ab = self.engine.anti_ban
        self.assertLessEqual(ab.refill_rate, 3.5)
        self.assertLessEqual(ab.max_tokens, 3.5)
        self.assertEqual(ab.min_inter_packet_delay, 0.220)

    def test_world_hop_and_stabilization_cooldowns(self):
        """Validates world hop cooldown >= 3.5s, same-world >= 10.0s, stabilization delay 2.8s +- 0.4s."""
        ab = self.engine.anti_ban
        self.assertGreaterEqual(ab.min_warp_cooldown, 3.5)
        self.assertGreaterEqual(ab.same_world_cooldown, 10.0)
        self.assertGreaterEqual(ab.world_enter_delay, 2.4)
        self.assertLessEqual(ab.world_enter_delay, 3.2)

    def test_drop_dialog_delay(self):
        """Validates drop dialog delay >= 400ms."""
        ab = self.engine.anti_ban
        self.assertGreaterEqual(ab.min_drop_delay, 0.400)

    def test_placement_jitter_and_hesitation_bounds(self):
        """Simulates placement jitter calculation across multiple actions."""
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        delays = [engine.calculate_placement_delay() for _ in range(60)]

        # Action 20 should be a micro-pause (0.7s to 1.4s)
        self.assertGreaterEqual(delays[19], 0.700)
        self.assertLessEqual(delays[19], 1.400)

        # Action 40 should be a micro-pause (0.7s to 1.4s)
        self.assertGreaterEqual(delays[39], 0.700)
        self.assertLessEqual(delays[39], 1.400)

        # Action 50 should be a random hesitation (1.8s to 3.5s)
        self.assertGreaterEqual(delays[49], 1.800)
        self.assertLessEqual(delays[49], 3.500)

        # Normal placement actions should fall within 210ms to 310ms (260 +- 50ms)
        for i in range(15):
            self.assertGreaterEqual(delays[i], 0.210)
            self.assertLessEqual(delays[i], 0.310)

    def test_integrity_packet_suppression(self):
        """Validates that packet type 25 (PACKET_APP_INTEGRITY_FAIL) is suppressed."""
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        bad_packet = lua.table(type=25)
        normal_packet = lua.table(type=10)

        suppressed_bad = engine.on_raw_packet_handler(bad_packet)
        suppressed_normal = engine.on_raw_packet_handler(normal_packet)

        self.assertTrue(suppressed_bad, "Integrity fail packet (type 25) must return true (suppressed).")
        self.assertFalse(suppressed_normal, "Normal packets must not be suppressed.")

    def test_moderator_detection_hook_halts_engine(self):
        """Hook OnVarlist with [MOD] message should trigger emergency halt to STATE_0_IDLE."""
        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 7
        varlist = lua.eval('{[0] = "OnConsoleMessage", [1] = "`4[MOD] `oUbisoft Mod entered the world."}')

        engine.on_varlist_handler(varlist)

        self.assertEqual(engine.active_state, 0, "Moderator detection must halt engine to STATE_0_IDLE.")
        self.assertTrue(engine.anti_ban.mod_detected, "anti_ban.mod_detected must be set to true.")

    def test_no_mid_session_hwid_spoofing(self):
        """Verifies strictly zero calls to randomGid() or randomMac() in source code."""
        src = LUA_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertNotIn("randomGid", src, "randomGid() call found; violates HWID stability safety.")
        self.assertNotIn("randomMac", src, "randomMac() call found; violates HWID stability safety.")


class TestRule8SoilGeometryInLua(unittest.TestCase):
    """Verifies AGENTS.md Rule 8 soil geometry checking in Lua."""

    def test_soil_geometry_filter(self):
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        # Setup test tiles via mock state:
        # Tile (10, 20) is solid Dirt (fg=2, isCollideable=true) -> tile (10, 19) is valid
        # Tile (20, 20) is non-collideable flower (fg=100, isCollideable=false) -> tile (20, 19) invalid
        # Tile (30, 20) is air (fg=0) -> tile (30, 19) invalid
        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_tiles["10_20"] = lua.table(fg=2, bg=8, isCollideable=True)
        mock_tiles["20_20"] = lua.table(fg=100, bg=8, isCollideable=False)
        mock_tiles["30_20"] = lua.table(fg=0, bg=8, isCollideable=False)

        valid_solid = engine.is_valid_soil_block(10, 19)
        invalid_non_col = engine.is_valid_soil_block(20, 19)
        invalid_air = engine.is_valid_soil_block(30, 19)

        self.assertTrue(valid_solid, "Tile above solid block must be valid soil.")
        self.assertFalse(invalid_non_col, "Tile above non-collideable block must NOT be valid soil.")
        self.assertFalse(invalid_air, "Tile above empty air must NOT be valid soil.")


class TestTwoStageVerifiedSplicing(unittest.TestCase):
    """Verifies two-stage verified splicing logic in Lua."""

    def test_secondary_seed_b_never_placed_without_seed_a_verified(self):
        """In STATE_8_SPLICING_SEED_B, Seed B is placed ONLY if checkTile(x, y).fg == seed_a_id."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 8
        engine.seed_a_id = 3
        engine.seed_b_id = 5
        engine.target_tree_id = 101
        engine.splice_index = 1
        engine.planted_base_coords = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20} }')

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        # Case 1: Tile (10, 20) has Seed A (fg = 3) -> should splice
        mock_tiles["10_20"] = lua.table(fg=3, bg=8, isCollideable=False)
        # Case 2: Tile (11, 20) was cleared (fg = 0) -> must NOT splice
        mock_tiles["11_20"] = lua.table(fg=0, bg=8, isCollideable=False)

        # Run tick step
        engine.on_tick_step(0.500)

        spliced_10 = mock_tiles["10_20"].fg
        unspliced_11 = mock_tiles["11_20"].fg

        self.assertEqual(spliced_10, 5, "Tile 10 with verified Seed A must have Seed B placed.")
        self.assertEqual(unspliced_11, 0, "Tile 11 without Seed A must NEVER receive Seed B.")


class TestDesignatedDropZoneManager(unittest.TestCase):
    """Verifies safe limit 5000 threshold and multi-tile overflow advancing."""

    def test_safe_limit_5000_threshold(self):
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))
        self.assertEqual(engine.drop_zone.limit, 5000, "Drop zone safe limit must be strictly 5000.")

    def test_drop_overflow_advances_coordinate(self):
        """When tile count reaches 5000, coordinates must advance to (x + 1, y) and reset count."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 12
        engine.drop_zone.world = "GROW_FARM1"
        engine.drop_zone.x = 50
        engine.drop_zone.y = 23
        engine.drop_zone.count = 5000  # Cap reached
        engine.anti_ban.world_enter_time = 0
        engine.anti_ban.world_enter_delay = 0

        engine.on_tick_step(0.500)

        self.assertEqual(engine.drop_zone.x, 51, "Tile reached 5000 cap; x must advance from 50 to 51.")
        self.assertEqual(engine.drop_zone.count, 0, "Count for new drop tile must reset to 0.")


class TestEmbeddedJsonAndGroundTruthReconciliation(unittest.TestCase):
    """Verifies embedded pure Lua JSON encode/decode and ground-truth tile reconciliation."""

    def test_embedded_json_roundtrip(self):
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        payload = lua.eval('{active_state = 7, world = "TEST_VAULT", capacity = 300, only_above = true, tiles = {{x = 10, y = 20}, {x = 11, y = 20}}}')

        encoded = engine.json_encode(payload)
        self.assertIn('"active_state":7', encoded)
        self.assertIn('"world":"TEST_VAULT"', encoded)

        decoded = engine.json_decode(encoded)
        self.assertEqual(decoded.active_state, 7)
        self.assertEqual(decoded.world, "TEST_VAULT")
        self.assertEqual(decoded.capacity, 300)
        self.assertTrue(decoded.only_above)
        self.assertEqual(len(decoded.tiles), 2)

    def test_ground_truth_reconciliation_ready_trees(self):
        """If tiles in farm world have ready trees, reconciles to STATE_10_READY_TO_HARVEST."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.farm_world = "GROW_FARM1"
        engine.target_tree_id = 101
        engine.valid_tiles = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20} }')

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_extras = lua.globals()._MOCK_STATE.extra_tiles

        mock_tiles["10_20"] = lua.table(fg=101, bg=8, isCollideable=False)
        mock_extras["10_20"] = lua.table(ready=True, growth=0)

        mock_tiles["11_20"] = lua.table(fg=101, bg=8, isCollideable=False)
        mock_extras["11_20"] = lua.table(ready=True, growth=0)

        ok, phase = engine.reconcile_live_tiles()
        self.assertTrue(ok)
        self.assertEqual(phase, "READY_TO_HARVEST")
        self.assertEqual(engine.active_state, 10, "Must reconcile directly to STATE_10_READY_TO_HARVEST.")

    def test_ground_truth_reconciliation_base_saplings(self):
        """If tiles have Base Seed A planted but unspliced, reconciles to STATE_8_SPLICING_SEED_B."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.farm_world = "GROW_FARM1"
        engine.seed_a_id = 3
        engine.valid_tiles = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20} }')

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_tiles["10_20"] = lua.table(fg=3, bg=8, isCollideable=False)
        mock_tiles["11_20"] = lua.table(fg=3, bg=8, isCollideable=False)

        ok, phase = engine.reconcile_live_tiles()
        self.assertTrue(ok)
        self.assertEqual(phase, "SPLICING_SEED_B")
        self.assertEqual(engine.active_state, 8, "Must reconcile to STATE_8_SPLICING_SEED_B.")


    def test_reconcile_empty_world_resumes_planting_a(self):
        """If tiles in farm world are empty, reconciles to STATE_7_PLANTING_SEED_A."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.farm_world = "GROW_FARM1"
        engine.valid_tiles = lua.eval('{ {x = 10, y = 20}, {x = 11, y = 20} }')

        mock_tiles = lua.globals()._MOCK_STATE.tiles
        mock_tiles["10_20"] = lua.table(fg=0, bg=8, isCollideable=False)
        mock_tiles["11_20"] = lua.table(fg=0, bg=8, isCollideable=False)

        ok, phase = engine.reconcile_live_tiles()
        self.assertTrue(ok)
        self.assertEqual(phase, "PLANTING_SEED_A")
        self.assertEqual(engine.active_state, 7, "Must reconcile to STATE_7_PLANTING_SEED_A.")


class TestMaturationCountdownAndDynamicButton(unittest.TestCase):
    """Verifies maturation countdown decrements and dynamic green button rendering."""

    def test_maturation_countdown_timer_ticks_down(self):
        """In STATE_9_WAIT_MATURATION, delta time decrements growth_remaining."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 9
        engine.growth_remaining = 100.0

        # Step 2.5 seconds
        engine.on_tick_step(2.5)
        self.assertAlmostEqual(engine.growth_remaining, 97.5, delta=0.01)

    def test_maturation_transition_to_state_10(self):
        """When growth_remaining reaches 0, transitions to STATE_10_READY_TO_HARVEST."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 9
        engine.growth_remaining = 0.5

        # Step 1.0 second (exceeds remaining)
        engine.on_tick_step(1.0)
        self.assertEqual(engine.active_state, 10, "Must transition to STATE_10_READY_TO_HARVEST.")
        self.assertTrue(engine.ready_to_harvest)

    def test_dynamic_green_harvest_button_source_presence(self):
        """Verifies dynamic green button code exists with color 0xFF2ECC71 and conditional guard."""
        src = LUA_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("[ HARVEST ET ]", src)
        self.assertIn("0xFF2ECC71", src)
        self.assertIn("STATE_10_READY_TO_HARVEST", src)


class TestSurplusPruningAndDropZoneCapture(unittest.TestCase):
    """Verifies surplus pruning packets and avatar drop zone setting."""

    def test_surplus_pruning_packets(self):
        """When collecting seed yields surplus (> required), drops surplus back on ground."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        engine.active_state = 4  # COLLECT_SEED_A
        engine.required_seeds = 300
        engine.seed_a_id = 3

        # Mock inventory has 340 seeds (overshoot by 40)
        lua.globals()._MOCK_STATE.inventory = lua.eval('{{id = 3, amount = 340}}')

        # Step phase 1: initiates drop dialog request
        engine.on_tick_step(0.500)
        # Step phase 2: completes dialog return with exact surplus count
        engine.on_tick_step(0.500)

        # Check that drop packets were sent
        packets = list(lua.globals()._MOCK_STATE.packets_sent.values())
        drop_packets = [p.text for p in packets if "action|drop" in p.text or "dialog_name|drop_item" in p.text]
        self.assertTrue(any("count|40" in p for p in drop_packets), "Must send drop dialog packet for 40 surplus seeds.")

    def test_set_current_tile_as_drop_zone_capture(self):
        """Button click [ Set Current Tile as Drop Zone ] captures player avatar position."""
        if not HAS_LUPA:
            raise unittest.SkipTest("lupa not installed")

        lua = create_mock_gentahax_lua_runtime()
        engine = lua.execute(LUA_SCRIPT_PATH.read_text(encoding="ascii"))

        # Player at pixel (1600, 736) -> Tile (50, 23)
        lua.globals()._MOCK_STATE.player_x = 1600
        lua.globals()._MOCK_STATE.player_y = 736
        lua.globals()._MOCK_STATE.world_name = "DROP_VAULT_TEST"
        lua.globals()._MOCK_STATE.button_clicks["[ Set Current Tile as Drop Zone ]"] = True

        engine.on_render_hook(0.016)

        self.assertEqual(engine.drop_zone.x, 50)
        self.assertEqual(engine.drop_zone.y, 23)
        self.assertEqual(engine.drop_zone.world, "DROP_VAULT_TEST")


class TestBridgeHttpRelayStateEndpoints(unittest.TestCase):
    """Validates /save_state atomic write and /get_state endpoints in bridge.py."""

    @classmethod
    def setUpClass(cls):
        B.start_http_relay(port=8809)

    def test_save_state_and_get_state_roundtrip(self):
        """Posts state JSON to /save_state and verifies atomic storage and retrieval via /get_state."""
        payload = {
            "world": "TEST_FARM_ATOMIC",
            "active_state": 7,
            "scanned_capacity": 420,
            "drop_zone": {"world": "DROP_STORE", "x": 55, "y": 25, "count": 1200, "limit": 5000}
        }
        body_bytes = json.dumps(payload).encode("utf-8")

        # 1. POST to /save_state
        req = urllib.request.Request(
            "http://127.0.0.1:8809/save_state",
            data=body_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res_data.get("ok"))
            self.assertTrue(res_data.get("atomic"))

        # 2. GET from /get_state
        req_get = urllib.request.Request("http://127.0.0.1:8809/get_state")
        with urllib.request.urlopen(req_get, timeout=3.0) as resp_get:
            self.assertEqual(resp_get.status, 200)
            state_data = json.loads(resp_get.read().decode("utf-8"))
            self.assertEqual(state_data.get("world"), "TEST_FARM_ATOMIC")
            self.assertEqual(state_data.get("scanned_capacity"), 420)


if __name__ == "__main__":
    unittest.main()

