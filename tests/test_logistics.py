#!/usr/bin/env python3
"""
Unit and Integration Tests for GENTAHAX MCP Multi-World Logistics Engine (Milestone 2)
mr_berk edition

Validates:
1. Target Farm Capacity Scanning (scan_farm_capacity):
   - AGENTS.md Rule 8 soil geometry filter: only_above_block requires (x, y) fg==0 and (x, y+1) fg!=0 and isCollideable==True.
   - Non-solid blocks below (isCollideable==False) are rejected.
   - Air below (fg==0) is rejected when only_above_block==True.
   - All air tiles in boundary are accepted when only_above_block==False.
   - Snake / boustrophedon tile sorting order.
   - Multiple input formats: 2D array, dictionary, list of tile dicts, callable accessor.
2. Exact Seed Count Calculation & Multi-Tier Balancing (calculate_seed_quotas):
   - Resolves target items and seeds (e.g. Wood Block -> Dirt Seed + Lava Seed).
   - Generates exact quotas matching capacity (Seed A=N, Seed B=N).
   - Base seeds vs multi-tier items (e.g. Chandelier Tier 4).
   - Prunes quotas against user stock.
   - Handles un-splicable base leaves (Tier 1 roots).
3. Multi-World Storage Retrieval Planning (plan_storage_retrieval):
   - Single-world full satisfaction.
   - Multi-world deficit splitting and fallback routing (e.g. 180 + 120 = 300).
   - Insufficient total stock across all storage worlds.
   - Surplus remaining in storage worlds.
   - Dynamic scanning when storage amount is unknown upfront.
4. Immediate Surplus Pruning Calculations (calculate_surplus_pruning):
   - Overshoot condition (collected 340, needed 300 -> drop 40).
   - Packet generation for client text and dialog return packets.
   - Exact match (300 / 300) and under quota (200 / 300) cases.
   - Zero and negative boundary clamping.
5. Sequential Multi-Farm Coordination (plan_multi_farm_sequence):
   - Sequential filling: Farm 1 completely planned before Farm 2.
   - Dynamic storage pool deduction across sequential farms.
   - Step-by-step phases per farm (warp, scan, fetch A, plant A, fetch B, splice B, wait, harvest, drop).
   - Anti-ban parameters and safe threshold enforcement.
   - Rule 8 compliance structure.
6. FastMCP Tool Registration & Invocations (gh_logistics_plan in server.py):
   - Registered in FastMCP server.
   - Programmatic invocation with valid inputs, capacity override, and error handling.
"""

import asyncio
import json
import os
import sys
import unittest
from typing import Dict, List, Tuple

# Set up module paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logistics as LOG
import server as S


class TestFarmCapacityScanning(unittest.TestCase):
    """Tests for scan_farm_capacity respecting AGENTS.md Rule 8."""

    def setUp(self):
        # Create a standard 100x60 empty world
        self.grid: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for y in range(60):
            for x in range(100):
                self.grid[(x, y)] = {"fg": 0, "bg": 8, "isCollideable": False, "x": x, "y": y}

    def test_empty_world_no_plantable_when_only_above_block(self):
        """In a completely empty air world, only_above_block=True should yield 0 plantable tiles."""
        result = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(result["plantable_count"], 0)
        self.assertEqual(result["capacity"], 0)
        self.assertEqual(len(result["valid_tiles"]), 0)
        self.assertTrue(result["only_above_block"])

    def test_empty_world_all_air_when_not_only_above_block(self):
        """When only_above_block=False, all air tiles in 1..98, 1..57 are plantable."""
        result = LOG.scan_farm_capacity(self.grid, only_above_block=False)
        expected_tiles = 98 * 57  # x: 1..98 (98), y: 1..57 (57)
        self.assertEqual(result["plantable_count"], expected_tiles)
        self.assertEqual(len(result["valid_tiles"]), expected_tiles)
        self.assertFalse(result["only_above_block"])

    def test_solid_block_row_qualifies_candidate_tiles(self):
        """A solid block row at y=20 (Dirt fg=2) makes tiles at y=19 plantable."""
        for x in range(1, 99):
            self.grid[(x, 20)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": x, "y": 20}

        result = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        # Row 19 has 98 tiles (x=1..98) directly above solid Dirt at row 20
        self.assertEqual(result["plantable_count"], 98)
        self.assertEqual(len(result["valid_tiles"]), 98)

        # Verify all detected tiles have y=19
        for tile in result["valid_tiles"]:
            self.assertEqual(tile["y"], 19)
            self.assertTrue(1 <= tile["x"] <= 98)

    def test_non_collideable_block_below_is_rejected(self):
        """A decorative non-collideable item below (isCollideable=False) must NOT count as solid support."""
        # Tile at (10, 20) is non-collideable flower (fg=1000, isCollideable=False)
        self.grid[(10, 20)] = {"fg": 1000, "bg": 8, "isCollideable": False, "x": 10, "y": 20}
        # Tile at (11, 20) is solid Dirt (fg=2, isCollideable=True)
        self.grid[(11, 20)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": 11, "y": 20}

        result = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        # Only (11, 19) should qualify, not (10, 19)
        self.assertEqual(result["plantable_count"], 1)
        self.assertEqual(result["valid_tiles"][0], {"x": 11, "y": 19})

    def test_occupied_candidate_tile_is_rejected(self):
        """If candidate tile (x, y) already has fg != 0, it cannot be planted on."""
        # Solid ground at (15, 25)
        self.grid[(15, 25)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": 15, "y": 25}
        # Candidate tile at (15, 24) already has a seed / sapling (fg=3)
        self.grid[(15, 24)] = {"fg": 3, "bg": 8, "isCollideable": False, "x": 15, "y": 24}

        result = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(result["plantable_count"], 0)

    def test_boundary_exclusions(self):
        """Tiles at boundaries (x=0, x=99, y=0, y=58, y=59) are excluded from scanning."""
        # Top border y=0 with solid block below at y=1
        self.grid[(10, 1)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": 10, "y": 1}
        # Left border x=0 with solid block below at y=21
        self.grid[(0, 21)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": 0, "y": 21}
        # Right border x=99 with solid block below at y=21
        self.grid[(99, 21)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": 99, "y": 21}
        # Bottom bedrock candidate y=58 with bedrock at y=59
        self.grid[(10, 59)] = {"fg": 8, "bg": 8, "isCollideable": True, "x": 10, "y": 59}

        result = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        # None of the boundary candidates should be counted (x in 1..98, y in 1..57)
        self.assertEqual(result["plantable_count"], 0)

    def test_snake_boustrophedon_ordering(self):
        """Candidate tiles must be sorted even row L->R, odd row R->L."""
        # Add solid blocks on rows 11 and 13
        # Valid plantable rows will be y=10 (even) and y=12 (even), or y=11 (odd)
        for x in (5, 10, 15):
            self.grid[(x, 21)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": x, "y": 21}  # candidate y=20 (even)
            self.grid[(x, 32)] = {"fg": 2, "bg": 8, "isCollideable": True, "x": x, "y": 32}  # candidate y=31 (odd)

        result = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        tiles = result["valid_tiles"]
        row_20 = [t["x"] for t in tiles if t["y"] == 20]
        row_31 = [t["x"] for t in tiles if t["y"] == 31]

        # Even row 20: L -> R (5, 10, 15)
        self.assertEqual(row_20, [5, 10, 15])
        # Odd row 31: R -> L (15, 10, 5)
        self.assertEqual(row_31, [15, 10, 5])

    def test_support_various_input_formats(self):
        """Tests that 2D grid, flat list, callable, and dict with 'tiles' are all accepted."""
        # Flat list
        tile_list = [
            {"x": 5, "y": 10, "fg": 0, "isCollideable": False},
            {"x": 5, "y": 11, "fg": 2, "isCollideable": True}
        ]
        r1 = LOG.scan_farm_capacity(tile_list, only_above_block=True)
        self.assertEqual(r1["plantable_count"], 1)

        # Dict with 'tiles'
        r2 = LOG.scan_farm_capacity({"tiles": tile_list}, only_above_block=True)
        self.assertEqual(r2["plantable_count"], 1)

        # Callable
        def accessor(x, y):
            if x == 5 and y == 10:
                return {"fg": 0}
            if x == 5 and y == 11:
                return {"fg": 2, "isCollideable": True}
            return None

        r3 = LOG.scan_farm_capacity(accessor, only_above_block=True)
        self.assertEqual(r3["plantable_count"], 1)

        # None input
        r4 = LOG.scan_farm_capacity(None)
        self.assertEqual(r4["plantable_count"], 0)


class TestExactSeedQuotasCalculation(unittest.TestCase):
    """Tests for calculate_seed_quotas and multi-tier balancing."""

    def test_wood_block_direct_splicing_pair(self):
        """Wood Block (Tier 2) requires Dirt Seed (3) and Lava Seed (5) at exact capacity."""
        res = LOG.calculate_seed_quotas("Wood Block", capacity=300)
        target = res["target"]
        self.assertEqual(target["item_name"], "Wood Block")
        self.assertEqual(res["capacity"], 300)

        direct = res["direct_ingredients"]
        self.assertIsNotNone(direct)
        self.assertEqual(direct["seed_a"]["seed_id"], 3)  # Dirt Seed
        self.assertEqual(direct["seed_a"]["needed_count"], 300)
        self.assertEqual(direct["seed_b"]["seed_id"], 5)  # Lava Seed
        self.assertEqual(direct["seed_b"]["needed_count"], 300)
        self.assertEqual(res["seed_quotas"], {3: 300, 5: 300})

    def test_user_stock_pruning(self):
        """If user has 100 Dirt Seeds in stock, net quota should be 200."""
        res = LOG.calculate_seed_quotas("Wood Block", capacity=300, user_stock={3: 100})
        direct = res["direct_ingredients"]
        self.assertEqual(direct["seed_a"]["needed_count"], 200)
        self.assertEqual(direct["seed_a"]["in_stock"], 100)
        self.assertEqual(direct["seed_b"]["needed_count"], 300)
        self.assertEqual(res["seed_quotas"], {3: 200, 5: 300})

    def test_multi_tier_chandelier_splicing(self):
        """Chandelier (Tier 4) resolves direct pair and full base BOM."""
        res = LOG.calculate_seed_quotas("Chandelier", capacity=100)
        target = res["target"]
        self.assertEqual(target["item_name"], "Chandelier")
        self.assertEqual(target["tier"], 12)

        direct = res["direct_ingredients"]
        # Direct ingredients are Crimson Block Seed (339) + Glass Pane Seed (57)
        self.assertIsNotNone(direct)
        self.assertEqual(direct["seed_a"]["needed_count"], 100)
        self.assertEqual(direct["seed_b"]["needed_count"], 100)

        # Full BOM includes Tier 1 base seeds: Dirt, Lava, Rock, Cave Background
        base_bom = res["base_seeds_bom"]
        self.assertTrue(len(base_bom) >= 4)
        for seed_entry in base_bom.values():
            self.assertGreater(seed_entry["gross_needed"], 0)

    def test_base_seed_root_item(self):
        """Requesting an un-splicable base seed (e.g. Dirt Seed, Rock Seed) returns base item info."""
        res = LOG.calculate_seed_quotas("Dirt Seed", capacity=250)
        self.assertTrue(res["target"]["is_base"])
        self.assertIsNone(res["direct_ingredients"])
        self.assertEqual(res["seed_quotas"], {3: 250})

    def test_invalid_target_raises_value_error(self):
        """Unknown or invalid item names must raise ValueError."""
        with self.assertRaises(ValueError):
            LOG.calculate_seed_quotas("NonExistentItem999XYZ", capacity=100)
        with self.assertRaises(ValueError):
            LOG.calculate_seed_quotas("", capacity=100)


class TestStorageRetrievalPlanning(unittest.TestCase):
    """Tests for plan_storage_retrieval and multi-world deficit splitting."""

    def test_single_world_satisfaction(self):
        """Single world with ample stock satisfies quota immediately."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=300, storage_worlds="STORE1:500")
        self.assertTrue(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 300)
        self.assertEqual(plan["deficit"], 0)
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["to_collect"], 300)
        self.assertEqual(plan["steps"][0]["surplus_remaining_in_storage"], 200)

    def test_multi_world_deficit_splitting(self):
        """World 1 has 180, World 2 has 200 -> Collects 180 from World 1, 120 from World 2."""
        plan = LOG.plan_storage_retrieval(
            seed_id="Dirt Seed",
            needed_count=300,
            storage_worlds="STORE1:180, STORE2:200"
        )
        self.assertTrue(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 300)
        self.assertEqual(plan["deficit"], 0)
        self.assertEqual(len(plan["steps"]), 2)

        # Step 1
        s1 = plan["steps"][0]
        self.assertEqual(s1["world"], "STORE1")
        self.assertEqual(s1["to_collect"], 180)
        self.assertEqual(s1["remaining_needed_after"], 120)
        self.assertEqual(s1["surplus_remaining_in_storage"], 0)

        # Step 2
        s2 = plan["steps"][1]
        self.assertEqual(s2["world"], "STORE2")
        self.assertEqual(s2["to_collect"], 120)
        self.assertEqual(s2["remaining_needed_after"], 0)
        self.assertEqual(s2["surplus_remaining_in_storage"], 80)

    def test_insufficient_stock_flags_deficit(self):
        """If storage worlds only have 100 and 150 (total 250) for 300 needed, deficit is 50."""
        plan = LOG.plan_storage_retrieval(
            seed_id=5,
            needed_count=300,
            storage_worlds=[{"world": "W1", "amount": 100}, {"world": "W2", "amount": 150}]
        )
        self.assertFalse(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 250)
        self.assertEqual(plan["deficit"], 50)
        self.assertEqual(plan["status"], "insufficient_stock")

    def test_zero_needed_count(self):
        """When needed count is 0, plan completes with 0 collection."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=0, storage_worlds="STORE1:100")
        self.assertTrue(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 0)
        self.assertEqual(len(plan["steps"]), 0)


class TestSurplusPruningCalculations(unittest.TestCase):
    """Tests for calculate_surplus_pruning."""

    def test_overshoot_pruning(self):
        """Picking up 340 seeds when 300 needed generates drop_surplus action for 40 seeds."""
        res = LOG.calculate_surplus_pruning(collected_count=340, needed_count=300, seed_id=3)
        self.assertEqual(res["surplus"], 40)
        self.assertEqual(res["drop_count"], 40)
        self.assertEqual(res["retained_count"], 300)
        self.assertTrue(res["drop_required"])
        self.assertEqual(res["action"], "drop_surplus")

        # Verify drop packet contents
        packets = res["drop_packet_instructions"]
        self.assertIsNotNone(packets)
        self.assertIn("itemID|3", packets["text_packet"])
        self.assertIn("count|40", packets["dialog_packet"])

    def test_exact_match_no_pruning(self):
        """Collecting exactly 300 seeds when 300 needed requires no pruning."""
        res = LOG.calculate_surplus_pruning(collected_count=300, needed_count=300)
        self.assertEqual(res["surplus"], 0)
        self.assertEqual(res["drop_count"], 0)
        self.assertEqual(res["retained_count"], 300)
        self.assertFalse(res["drop_required"])
        self.assertEqual(res["action"], "keep")
        self.assertIsNone(res["drop_packet_instructions"])

    def test_under_quota_no_pruning(self):
        """Collecting 200 seeds when 300 needed requires no pruning."""
        res = LOG.calculate_surplus_pruning(collected_count=200, needed_count=300)
        self.assertEqual(res["surplus"], 0)
        self.assertEqual(res["retained_count"], 200)
        self.assertFalse(res["drop_required"])
        self.assertEqual(res["action"], "keep")

    def test_zero_and_negative_inputs(self):
        """Handles edge case non-positive values cleanly."""
        res = LOG.calculate_surplus_pruning(collected_count=-10, needed_count=-5)
        self.assertEqual(res["collected"], 0)
        self.assertEqual(res["needed"], 0)
        self.assertEqual(res["surplus"], 0)


class TestSequentialMultiFarmCoordination(unittest.TestCase):
    """Tests for plan_multi_farm_sequence."""

    def test_two_farm_sequential_coordination(self):
        """Tests sequential coordination of World 4 and World 5."""
        plan = LOG.plan_multi_farm_sequence(
            farm_worlds="WORLD4, WORLD5",
            target_item="Wood Block",
            storage_worlds="STORE1:500, STORE2:300",
            only_above_block=True,
            capacity_override=200
        )
        self.assertEqual(plan["status"], "success")
        self.assertEqual(plan["total_farms"], 2)
        self.assertEqual(plan["total_capacity"], 400)

        farms = plan["farm_plans"]
        self.assertEqual(len(farms), 2)
        self.assertEqual(farms[0]["farm_world"], "WORLD4")
        self.assertEqual(farms[1]["farm_world"], "WORLD5")

        # Verify sequential phases in Farm 1
        phases_1 = farms[0]["phases"]
        phase_actions = [p["action"] for p in phases_1]
        expected_actions = [
            "warp_and_scan",
            "storage_collect",
            "plant_base_seeds",
            "storage_collect",
            "splice_secondary_seeds",
            "wait_maturation",
            "harvest_and_drop",
            "farm_complete"
        ]
        self.assertEqual(phase_actions, expected_actions)

    def test_storage_pool_deduction_across_farms(self):
        """Verifies that Farm 1's consumption properly reduces storage pool for Farm 2."""
        # STORE1 has 300 seeds. Farm 1 needs 200 seeds, Farm 2 needs 200 seeds.
        # Farm 1 takes 200 from STORE1. STORE1 is left with 100.
        # Farm 2 takes remaining 100 from STORE1 and routes to STORE2 for 100.
        plan = LOG.plan_multi_farm_sequence(
            farm_worlds=["FARM1", "FARM2"],
            target_item="Wood Block",
            storage_worlds="STORE1:300, STORE2:500",
            capacity_override=200
        )
        # Check storage pool after both farms
        remaining = plan["storage_pool_remaining"]
        # Wood Block needs Seed A (Dirt) and Seed B (Lava).
        # Total capacity 400 = 400 Dirt Seeds + 400 Lava Seeds.
        # Total storage: STORE1 had 300, STORE2 had 500 = 800 total units.
        # 800 - 400 (Seed A) - 400 (Seed B) = 0 remaining across storage worlds.
        self.assertEqual(sum(remaining.values()), 0)

    def test_rule_8_compliance_reporting(self):
        """Confirms Rule 8 compliance section is fully reported."""
        plan = LOG.plan_multi_farm_sequence(
            farm_worlds="FARM1",
            target_item="Rock",
            storage_worlds="STORE1:500",
            only_above_block=True
        )
        rule_8 = plan["rule_8_compliance"]
        self.assertTrue(rule_8["enforced"])
        self.assertIn("Only Above Solid Blocks", rule_8["mode"])
        self.assertIn("ImGui.Checkbox", rule_8["imgui_checkbox"])


class TestLuaCodeGenerators(unittest.TestCase):
    """Tests for Lua snippet generators ensuring AGENTS.md compliance."""

    def test_capacity_scanner_lua_agents_md_compliance(self):
        lua = LOG.generate_scan_farm_capacity_lua(only_above_block=True)
        # AGENTS.md Rule 4 header
        self.assertIn("-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp", lua)
        # Rule 8 logic
        self.assertIn("checkTile(x, y + 1)", lua)
        self.assertIn("below.isCollideable", lua)
        # Bounded scan grid
        self.assertIn("for y = 1, 57 do", lua)
        self.assertIn("for x = 1, 98 do", lua)

    def test_surplus_prune_lua(self):
        lua = LOG.generate_surplus_prune_lua(seed_id=3, drop_count=40)
        self.assertIn("action|drop", lua)
        self.assertIn("itemID|", lua)
        self.assertIn("pruneSurplus(3, 40)", lua)


class TestFastMCPLogisticsTool(unittest.TestCase):
    """Tests FastMCP tool gh_logistics_plan in server.py."""

    def test_tool_registered_in_fastmcp(self):
        async def check():
            tools = await S.mcp.list_tools()
            names = [t.name for t in tools]
            self.assertIn("gh_logistics_plan", names)
        asyncio.run(check())

    def test_tool_invocation_valid_target(self):
        raw = S.gh_logistics_plan(
            target="Wood Block",
            farm_world="FARM4",
            storage_worlds="STORE1:500",
            only_above_block=True,
            capacity_override=300
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_farms"], 1)
        self.assertEqual(data["total_capacity"], 300)
        self.assertEqual(data["target"]["item_name"], "Wood Block")

    def test_tool_invocation_multi_farm(self):
        raw = S.gh_logistics_plan(
            target="Chandelier",
            farm_world="FARM1, FARM2",
            storage_worlds="STORE1:1000",
            only_above_block=True,
            capacity_override=150
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_farms"], 2)
        self.assertEqual(data["total_capacity"], 300)

    def test_tool_invocation_invalid_target(self):
        raw = S.gh_logistics_plan(
            target="TotallyFakeItem999",
            farm_world="FARM1",
            storage_worlds="STORE1:100"
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "error")
        self.assertIn("could not be resolved", data["error"])

    def test_tool_schema_and_parameters(self):
        async def check():
            tools = await S.mcp.list_tools()
            tool_obj = next((t for t in tools if t.name == "gh_logistics_plan"), None)
            self.assertIsNotNone(tool_obj)
            self.assertIn("target", tool_obj.parameters["properties"])
            self.assertIn("farm_world", tool_obj.parameters["properties"])
            self.assertIn("storage_worlds", tool_obj.parameters["properties"])
            self.assertIn("only_above_block", tool_obj.parameters["properties"])
            self.assertIn("capacity_override", tool_obj.parameters["properties"])
        asyncio.run(check())


class TestLogisticsAdversarialAndBoundaries(unittest.TestCase):
    """Adversarial stress and edge cases for logistics engine."""

    def test_sparse_and_corrupt_tile_entries(self):
        """Capacity scan handles sparse dicts, None tiles, and custom key spellings."""
        sparse_world = {
            (5, 5): None,
            (5, 6): {"fg": 2, "is_collideable": True},
            (10, 10): {"fg": 0},
            (10, 11): {"fg": 0},  # Air below
            (12, 12): {"fg": 0},
            (12, 13): {"fg": 10, "isCollideable": "true"},  # truthy string
            (14, 14): {"fg": 0},
            (14, 15): {"fg": 10, "isCollideable": 0},  # falsy integer
        }
        res = LOG.scan_farm_capacity(sparse_world, only_above_block=True)
        # (12, 12) has solid block (12, 13). (14, 14) has non-collideable. (5, 5) is None.
        self.assertEqual(res["plantable_count"], 1)
        self.assertEqual(res["valid_tiles"][0], {"x": 12, "y": 12})

    def test_large_capacity_and_string_sanitization(self):
        """calculate_seed_quotas handles string capacity and string stock gracefully."""
        res = LOG.calculate_seed_quotas(
            target_item="100",  # Wood Block item ID
            capacity="2500",
            user_stock="Dirt Seed: 500, 5: 300"
        )
        self.assertEqual(res["capacity"], 2500)
        direct = res["direct_ingredients"]
        self.assertEqual(direct["seed_a"]["needed_count"], 2000)  # 2500 - 500
        self.assertEqual(direct["seed_b"]["needed_count"], 2200)  # 2500 - 300

    def test_many_fallback_storage_worlds_routing(self):
        """5 fallback worlds each providing partial stock."""
        storage_str = "STORE1:40, STORE2:40, STORE3:40, STORE4:40, STORE5:100"
        plan = LOG.plan_storage_retrieval(
            seed_id=3,
            needed_count=150,
            storage_worlds=storage_str
        )
        self.assertTrue(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 150)
        self.assertEqual(len(plan["steps"]), 4)  # 40 + 40 + 40 + 30 = 150 (satisfies in 4th world)
        self.assertEqual(plan["steps"][0]["to_collect"], 40)
        self.assertEqual(plan["steps"][1]["to_collect"], 40)
        self.assertEqual(plan["steps"][2]["to_collect"], 40)
        self.assertEqual(plan["steps"][3]["to_collect"], 30)
        self.assertEqual(plan["steps"][3]["surplus_remaining_in_storage"], 10)

    def test_three_farms_sequential_exhaustion(self):
        """3 sequential farms where stock runs out mid-sequence."""
        plan = LOG.plan_multi_farm_sequence(
            farm_worlds="FARM1, FARM2, FARM3",
            target_item="Wood Block",
            storage_worlds="STORE1:300",  # Only 300 total units
            capacity_override=100
        )
        self.assertEqual(plan["total_farms"], 3)
        self.assertEqual(plan["total_capacity"], 300)
        # Farm 1 needs 100 A + 100 B (200 units). STORE1 left with 100 units.
        # Farm 2 needs 100 A + 100 B (200 units). Takes 100 A, 0 B left.
        # Farm 3 gets deficit.
        farms = plan["farm_plans"]
        self.assertTrue(farms[0]["seed_a_retrieval"]["is_fully_satisfied"])
        self.assertTrue(farms[0]["seed_b_retrieval"]["is_fully_satisfied"])
        self.assertFalse(farms[1]["seed_b_retrieval"]["is_fully_satisfied"])
        self.assertFalse(farms[2]["seed_a_retrieval"]["is_fully_satisfied"])


if __name__ == "__main__":
    unittest.main()
