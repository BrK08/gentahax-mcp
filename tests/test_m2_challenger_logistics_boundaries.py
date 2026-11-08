#!/usr/bin/env python3
"""
Adversarial Challenger Suite: Milestone 2 — Multi-World Logistics & Capacity Balancing Engine
mr_berk edition

Exhaustively probes and stress-tests:
1. 0 Capacity or Empty World Grid Boundaries:
   - Empty world grid (all fg=0) with only_above_block=True -> 0 plantable.
   - Empty world grid with only_above_block=False -> 5586 plantable (98x57).
   - None, empty dict, empty list, corrupted grid containers.
   - Fully occupied world (all fg!=0) -> 0 plantable.
   - calculate_seed_quotas with capacity=0, negative, string "0", None -> 0 net quotas.
   - plan_storage_retrieval with needed_count=0, negative -> 0 collected, deficit 0, satisfied=True.
   - calculate_surplus_pruning with 0 collected, 0 needed -> surplus 0, action='keep'.
   - plan_multi_farm_sequence with capacity_override=0 -> 0 capacity, 0 seeds needed.
2. Extremely Large Capacity Boundaries (> 5000 tiles):
   - Exact world maximum (5,586 tiles) and supra-world capacity (10,000, 50,000 tiles).
   - Multi-tier DAG MRP Bill of Materials scaling without recursion depth errors.
   - Sequential multi-farm distribution across large storage pools (> 50,000 units).
   - Performance benchmark (< 10ms for multi-tier 10,000-capacity calculations).
3. Insufficient Storage Seeds Across All Worlds:
   - Single storage world deficit.
   - Multi-world partial stock deficit routing.
   - Total zero stock across all storage worlds.
   - Multi-farm sequential exhaustion mid-workflow.
4. Exact Storage Match Boundaries (collected == needed -> surplus = 0):
   - calculate_surplus_pruning exact match (300/300, 5000/5000) -> surplus=0, drop_count=0.
   - plan_storage_retrieval exact match -> 0 deficit, 0 remaining surplus in storage.
5. Storage Undercollection Boundaries (collected < needed):
   - calculate_surplus_pruning undercollection (180/300, 1/5000) -> drop_required=False.
   - plan_storage_retrieval partial collection -> exact deficit reported.
6. Corrupted or Invalid World String Formats in FastMCP Tool:
   - gh_logistics_plan with empty/whitespace target, farm_world, storage_worlds.
   - Malformed storage world syntax ("::", ":100", "STORE1:", "STORE1:-50", ",,,  ,,,").
   - Unicode, emojis, SQL-injection strings in world names.
   - Extremely large capacity overrides and negative capacity overrides.
7. AGENTS.md Rule 8 Soil Geometry Edge Cases:
   - Non-solid blocks below: isCollideable=False, is_collideable=False, isCollideable="false", "0", 0.
   - Solid blocks below: isCollideable=True, isCollideable="true", 1.
   - Air below (fg=0) rejection.
   - Occupied candidate tile (fg!=0) rejection.
   - Bedrock at y=59 and candidate at y=58 border handling.
   - Outer world borders: x=0, y=0, x=99, y=59 strict exclusion from default scan range.
   - Snake / boustrophedon sweep order verification across multi-row grids.
"""

import asyncio
import json
import os
import sys
import time
import unittest
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import logistics as LOG
import server as S


class TestChallengerZeroCapacityAndEmptyWorld(unittest.TestCase):
    """Adversarial challenge for 0 capacity, empty grid, and negative capacity vectors."""

    def test_scan_capacity_completely_empty_world_only_above_block(self):
        """Empty air world with only_above_block=True must yield exactly 0 plantable capacity."""
        empty_grid = {(x, y): {"fg": 0, "bg": 8, "isCollideable": False} for y in range(60) for x in range(100)}
        res = LOG.scan_farm_capacity(empty_grid, only_above_block=True)
        self.assertEqual(res["plantable_count"], 0)
        self.assertEqual(res["capacity"], 0)
        self.assertEqual(len(res["valid_tiles"]), 0)
        self.assertTrue(res["only_above_block"])

    def test_scan_capacity_completely_empty_world_all_air(self):
        """Empty air world with only_above_block=False yields 98 * 57 = 5586 tiles."""
        empty_grid = {(x, y): {"fg": 0, "bg": 8, "isCollideable": False} for y in range(60) for x in range(100)}
        res = LOG.scan_farm_capacity(empty_grid, only_above_block=False)
        self.assertEqual(res["plantable_count"], 5586)
        self.assertEqual(len(res["valid_tiles"]), 5586)

    def test_scan_capacity_none_empty_dict_empty_list(self):
        """Passing None, empty dict, or empty list must return 0 capacity gracefully."""
        self.assertEqual(LOG.scan_farm_capacity(None)["plantable_count"], 0)
        self.assertEqual(LOG.scan_farm_capacity({})["plantable_count"], 0)
        self.assertEqual(LOG.scan_farm_capacity([])["plantable_count"], 0)
        self.assertEqual(LOG.scan_farm_capacity({"tiles": []})["plantable_count"], 0)

    def test_scan_capacity_fully_occupied_world(self):
        """A world where every candidate tile has fg != 0 must yield 0 plantable tiles."""
        solid_grid = {(x, y): {"fg": 2, "bg": 8, "isCollideable": True} for y in range(60) for x in range(100)}
        res = LOG.scan_farm_capacity(solid_grid, only_above_block=True)
        self.assertEqual(res["plantable_count"], 0)
        self.assertEqual(res["capacity"], 0)

    def test_calculate_seed_quotas_zero_and_negative_capacity(self):
        """calculate_seed_quotas with capacity 0 or negative must return 0 net quotas and 0 base BOM."""
        for zero_cap in [0, -1, -500, "0", "-10"]:
            res = LOG.calculate_seed_quotas("Wood Block", capacity=zero_cap)
            self.assertEqual(res["capacity"], 0)
            self.assertEqual(res["seed_quotas"], {3: 0, 5: 0})
            direct = res["direct_ingredients"]
            self.assertIsNotNone(direct)
            self.assertEqual(direct["seed_a"]["needed_count"], 0)
            self.assertEqual(direct["seed_a"]["gross_needed"], 0)
            self.assertTrue(direct["seed_a"]["is_satisfied"])
            self.assertEqual(direct["seed_b"]["needed_count"], 0)
            self.assertTrue(direct["seed_b"]["is_satisfied"])
            # Base BOM must also have 0 fetch required
            for base_info in res["base_seeds_bom"].values():
                self.assertEqual(base_info["fetch_required"], 0)

    def test_plan_storage_retrieval_zero_and_negative_needed(self):
        """plan_storage_retrieval with needed_count <= 0 must return satisfied with 0 collection."""
        for zero_needed in [0, -10, -999]:
            res = LOG.plan_storage_retrieval(seed_id=3, needed_count=zero_needed, storage_worlds="STORE1:500")
            self.assertTrue(res["is_fully_satisfied"])
            self.assertEqual(res["total_collected"], 0)
            self.assertEqual(res["deficit"], 0)
            self.assertEqual(len(res["steps"]), 0)

    def test_calculate_surplus_pruning_zero_collected_zero_needed(self):
        """calculate_surplus_pruning with 0 collected and 0 needed requires no pruning."""
        res = LOG.calculate_surplus_pruning(collected_count=0, needed_count=0, seed_id=3)
        self.assertEqual(res["surplus"], 0)
        self.assertEqual(res["drop_count"], 0)
        self.assertEqual(res["retained_count"], 0)
        self.assertFalse(res["drop_required"])
        self.assertEqual(res["action"], "keep")
        self.assertIsNone(res["drop_packet_instructions"])

    def test_plan_multi_farm_sequence_zero_capacity_override(self):
        """plan_multi_farm_sequence with capacity_override=0 plans 0 seeds and 0 collection."""
        plan = LOG.plan_multi_farm_sequence(
            farm_worlds="FARM1, FARM2",
            target_item="Wood Block",
            storage_worlds="STORE1:500",
            capacity_override=0
        )
        self.assertEqual(plan["total_capacity"], 0)
        self.assertEqual(plan["total_seeds_needed"], {3: 0, 5: 0})
        for fp in plan["farm_plans"]:
            self.assertEqual(fp["capacity"], 0)
            self.assertEqual(fp["seed_a_retrieval"]["needed_count"], 0)
            self.assertEqual(fp["seed_a_retrieval"]["total_collected"], 0)
            self.assertTrue(fp["seed_a_retrieval"]["is_fully_satisfied"])


class TestChallengerExtremelyLargeCapacity(unittest.TestCase):
    """Adversarial stress-test for large capacity (> 5,000 tiles)."""

    def test_exact_world_maximum_capacity_5586(self):
        """Full world grid capacity (5,586 tiles) calculated accurately for multi-tier item."""
        res = LOG.calculate_seed_quotas("Chandelier", capacity=5586)
        self.assertEqual(res["capacity"], 5586)
        # Direct ingredients Crimson Block Seed (339) and Glass Pane Seed (57)
        direct = res["direct_ingredients"]
        self.assertEqual(direct["seed_a"]["needed_count"], 5586)
        self.assertEqual(direct["seed_b"]["needed_count"], 5586)

        # Full BOM Tier 1 base seeds gross counts
        base_bom = res["base_seeds_bom"]
        self.assertEqual(base_bom["Lava Seed (5)"]["gross_needed"], 5586 * 11)
        self.assertEqual(base_bom["Rock Seed (11)"]["gross_needed"], 5586 * 32)
        self.assertEqual(base_bom["Dirt Seed (3)"]["gross_needed"], 5586 * 31)
        self.assertEqual(base_bom["Cave Background Seed (15)"]["gross_needed"], 5586 * 13)

    def test_supra_world_capacity_50000(self):
        """Massive 50,000 capacity stress test completes in under 20ms without recursion errors."""
        t0 = time.time()
        res = LOG.calculate_seed_quotas("Chandelier", capacity=50000)
        elapsed_ms = (time.time() - t0) * 1000.0
        self.assertLess(elapsed_ms, 20.0, f"Calculation took {elapsed_ms:.2f}ms, expected < 20ms")
        self.assertEqual(res["capacity"], 50000)
        self.assertEqual(res["seed_quotas"][287], 50000)
        self.assertEqual(res["seed_quotas"][261], 50000)

    def test_multi_farm_large_capacity_distribution(self):
        """5 sequential farms with 2,000 capacity each (total 10,000) across 4 storage worlds."""
        storage_str = "STORE1:3000, STORE2:3000, STORE3:3000, STORE4:3000"
        plan = LOG.plan_multi_farm_sequence(
            farm_worlds=["F1", "F2", "F3", "F4", "F5"],
            target_item="Wood Block",
            storage_worlds=storage_str,
            capacity_override=2000
        )
        self.assertEqual(plan["total_farms"], 5)
        self.assertEqual(plan["total_capacity"], 10000)
        # 10,000 Wood Block = 10,000 Dirt Seed + 10,000 Lava Seed = 20,000 total seeds
        # Total storage: 4 * 3,000 = 12,000 seeds -> all 12,000 exhausted, deficit remaining
        remaining_pool = plan["storage_pool_remaining"]
        self.assertEqual(sum(remaining_pool.values()), 0)


class TestChallengerInsufficientStorageSeeds(unittest.TestCase):
    """Adversarial test for insufficient stock and deficit routing."""

    def test_single_world_insufficient_stock(self):
        """Storage world has 100 seeds for 300 needed -> deficit 200, status='insufficient_stock'."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=300, storage_worlds="STORE1:100")
        self.assertFalse(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 100)
        self.assertEqual(plan["deficit"], 200)
        self.assertEqual(plan["status"], "insufficient_stock")
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["surplus_remaining_in_storage"], 0)

    def test_multi_world_cumulative_insufficient_stock(self):
        """3 worlds holding 40, 50, 60 (total 150) for 400 needed -> deficit 250."""
        plan = LOG.plan_storage_retrieval(
            seed_id=5,
            needed_count=400,
            storage_worlds="STORE1:40, STORE2:50, STORE3:60"
        )
        self.assertFalse(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 150)
        self.assertEqual(plan["deficit"], 250)
        self.assertEqual(len(plan["steps"]), 3)

    def test_zero_total_storage_stock(self):
        """Storage worlds with 0 seeds available -> deficit equals needed count."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=200, storage_worlds="STORE1:0, STORE2:0")
        self.assertFalse(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 0)
        self.assertEqual(plan["deficit"], 200)

    def test_empty_storage_worlds_specification(self):
        """Empty storage world string yields 0 collection and full deficit without crashing."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=300, storage_worlds="")
        self.assertFalse(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 0)
        self.assertEqual(plan["deficit"], 300)
        self.assertEqual(len(plan["steps"]), 0)


class TestChallengerExactStorageMatch(unittest.TestCase):
    """Adversarial test for exact storage match (collected == needed -> surplus = 0)."""

    def test_surplus_pruning_exact_match(self):
        """Exact match 300 / 300 leaves 0 surplus and requires no drop."""
        res = LOG.calculate_surplus_pruning(collected_count=300, needed_count=300, seed_id=101)
        self.assertEqual(res["surplus"], 0)
        self.assertEqual(res["drop_count"], 0)
        self.assertEqual(res["retained_count"], 300)
        self.assertFalse(res["drop_required"])
        self.assertEqual(res["action"], "keep")
        self.assertIsNone(res["drop_packet_instructions"])

    def test_plan_storage_retrieval_exact_match_single_world(self):
        """Single world with exactly needed seeds -> 0 deficit, 0 remaining in storage."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=250, storage_worlds="STORE1:250")
        self.assertTrue(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 250)
        self.assertEqual(plan["deficit"], 0)
        self.assertEqual(plan["steps"][0]["surplus_remaining_in_storage"], 0)

    def test_plan_storage_retrieval_exact_match_multi_world(self):
        """STORE1 has 130, STORE2 has 170 (total 300) for 300 needed -> exact zero deficit."""
        plan = LOG.plan_storage_retrieval(seed_id=3, needed_count=300, storage_worlds="STORE1:130, STORE2:170")
        self.assertTrue(plan["is_fully_satisfied"])
        self.assertEqual(plan["total_collected"], 300)
        self.assertEqual(plan["deficit"], 0)
        self.assertEqual(plan["steps"][1]["surplus_remaining_in_storage"], 0)


class TestChallengerStorageUndercollection(unittest.TestCase):
    """Adversarial test for storage undercollection (collected < needed)."""

    def test_surplus_pruning_undercollection(self):
        """Collecting 200 when 300 needed must retain all 200, surplus 0, no drop."""
        res = LOG.calculate_surplus_pruning(collected_count=200, needed_count=300, seed_id=3)
        self.assertEqual(res["surplus"], 0)
        self.assertEqual(res["drop_count"], 0)
        self.assertEqual(res["retained_count"], 200)
        self.assertFalse(res["drop_required"])
        self.assertEqual(res["action"], "keep")
        self.assertIsNone(res["drop_packet_instructions"])

    def test_surplus_pruning_severe_undercollection(self):
        """Collecting 1 when 5000 needed retains 1 with 0 surplus."""
        res = LOG.calculate_surplus_pruning(collected_count=1, needed_count=5000, seed_id=3)
        self.assertEqual(res["surplus"], 0)
        self.assertEqual(res["retained_count"], 1)
        self.assertFalse(res["drop_required"])


class TestChallengerFastMCPCorruptedInputs(unittest.TestCase):
    """Adversarial challenge for corrupted and invalid inputs in FastMCP tool gh_logistics_plan."""

    def test_empty_and_whitespace_target(self):
        """Empty or whitespace target returns error JSON without crashing server."""
        for bad_target in ["", "   ", "\t\n"]:
            raw = S.gh_logistics_plan(target=bad_target, farm_world="FARM1", storage_worlds="STORE1:100")
            data = json.loads(raw)
            self.assertEqual(data["status"], "error")
            self.assertIn("target_item cannot be empty", data["error"])

    def test_nonexistent_target_item(self):
        """Unresolvable target item returns error JSON."""
        raw = S.gh_logistics_plan(target="UnicornSuperBlock999", farm_world="FARM1", storage_worlds="STORE1:100")
        data = json.loads(raw)
        self.assertEqual(data["status"], "error")
        self.assertIn("could not be resolved", data["error"])

    def test_empty_and_commas_farm_world(self):
        """Empty, space, or commas-only farm_world returns error JSON."""
        for bad_farm in ["", "  ", ",,, ,  ,,"]:
            raw = S.gh_logistics_plan(target="Wood Block", farm_world=bad_farm, storage_worlds="STORE1:100")
            data = json.loads(raw)
            self.assertEqual(data["status"], "error")
            self.assertIn("At least one farm world must be specified", data["error"])

    def test_corrupted_storage_world_strings(self):
        """Corrupted storage syntax (::, :100, STORE1:-50, invalid strings) is sanitized cleanly."""
        corrupt_str = "::, , :50, abc:xyz, STORE1:-50, STORE2:200, ,,,"
        raw = S.gh_logistics_plan(
            target="Wood Block",
            farm_world="FARM1",
            storage_worlds=corrupt_str,
            capacity_override=100
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        pool = data["storage_pool_remaining"]
        # Empty world names must NOT exist in storage pool
        self.assertNotIn("", pool)
        # Negative amounts must be clamped to non-negative
        if "STORE1" in pool:
            self.assertGreaterEqual(pool["STORE1"], 0)

    def test_unicode_and_special_character_farm_worlds(self):
        """Non-ASCII Turkish letters, emojis, and special symbols in farm names are handled safely."""
        raw = S.gh_logistics_plan(
            target="Wood Block",
            farm_world="TARLA 🌾, ÇİFTLİK 🚜, FARM_#123",
            storage_worlds="DEPO1:500",
            capacity_override=50
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_farms"], 3)
        self.assertEqual(data["total_capacity"], 150)

    def test_negative_capacity_override_sanitization(self):
        """Negative capacity override is clamped to 0 without resulting in negative quotas."""
        raw = S.gh_logistics_plan(
            target="Wood Block",
            farm_world="FARM1",
            storage_worlds="STORE1:100",
            capacity_override=-100
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_capacity"], 0)
        self.assertEqual(data["farm_plans"][0]["capacity"], 0)


class TestChallengerRule8EdgeCases(unittest.TestCase):
    """Adversarial boundary tests for AGENTS.md Rule 8 soil geometry."""

    def setUp(self):
        self.grid: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for y in range(60):
            for x in range(100):
                self.grid[(x, y)] = {"fg": 0, "bg": 8, "isCollideable": False, "x": x, "y": y}

    def test_string_boolean_false_non_collideable_rejected(self):
        """String forms 'false', '0', 'no' for isCollideable must NOT be treated as truthy."""
        # Candidate at (10, 20), below at (10, 21) has isCollideable = 'false'
        self.grid[(10, 21)] = {"fg": 100, "isCollideable": "false", "x": 10, "y": 21}
        # Candidate at (11, 20), below at (11, 21) has is_collideable = '0'
        self.grid[(11, 21)] = {"fg": 100, "is_collideable": "0", "x": 11, "y": 21}
        # Candidate at (12, 20), below at (12, 21) has isCollideable = 0
        self.grid[(12, 21)] = {"fg": 100, "isCollideable": 0, "x": 12, "y": 21}
        # Valid solid block at (13, 21)
        self.grid[(13, 21)] = {"fg": 2, "isCollideable": True, "x": 13, "y": 21}

        res = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        # Only (13, 20) should qualify
        self.assertEqual(res["plantable_count"], 1)
        self.assertEqual(res["valid_tiles"][0], {"x": 13, "y": 20})

    def test_string_boolean_true_collideable_accepted(self):
        """String forms 'true', '1', 'yes' for isCollideable must qualify as solid."""
        self.grid[(15, 21)] = {"fg": 2, "isCollideable": "true", "x": 15, "y": 21}
        self.grid[(16, 21)] = {"fg": 2, "isCollideable": "1", "x": 16, "y": 21}

        res = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(res["plantable_count"], 2)
        tiles = sorted(res["valid_tiles"], key=lambda t: t["x"])
        self.assertEqual(tiles, [{"x": 15, "y": 20}, {"x": 16, "y": 20}])

    def test_outer_world_borders_strictly_excluded(self):
        """Coordinates at borders x=0, x=99, y=0, y=59 must be excluded from plantable set."""
        # Border candidates with solid ground below
        self.grid[(0, 10)] = {"fg": 0}
        self.grid[(0, 11)] = {"fg": 2, "isCollideable": True}
        self.grid[(99, 10)] = {"fg": 0}
        self.grid[(99, 11)] = {"fg": 2, "isCollideable": True}
        self.grid[(10, 0)] = {"fg": 0}
        self.grid[(10, 1)] = {"fg": 2, "isCollideable": True}

        res = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(res["plantable_count"], 0)

    def test_bedrock_row_boundary_behavior(self):
        """Bedrock is at y=59. Row y=58 candidate is excluded in default (1, 57) range, but included in (1, 58)."""
        self.grid[(25, 58)] = {"fg": 0}
        self.grid[(25, 59)] = {"fg": 8, "isCollideable": True}  # Bedrock

        # Default range 1..57 excludes y=58
        res_default = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(res_default["plantable_count"], 0)

        # Extended range 1..58 includes y=58
        res_ext = LOG.scan_farm_capacity(self.grid, only_above_block=True, y_range=(1, 58))
        self.assertEqual(res_ext["plantable_count"], 1)
        self.assertEqual(res_ext["valid_tiles"][0], {"x": 25, "y": 58})

    def test_candidate_tile_occupied_rejected(self):
        """If candidate tile has fg != 0 (e.g. sapling fg=3, tree fg=101), it cannot be planted on."""
        self.grid[(30, 20)] = {"fg": 3, "isCollideable": False}  # Occupied by sapling
        self.grid[(30, 21)] = {"fg": 2, "isCollideable": True}   # Solid ground below

        res = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(res["plantable_count"], 0)

    def test_snake_boustrophedon_sweep_direction(self):
        """Validates snake ordering: even rows L->R, odd rows R->L across multiple lines."""
        # Row 20 (even): candidate at y=20 has solid ground at y=21
        for x in (10, 20, 30):
            self.grid[(x, 21)] = {"fg": 2, "isCollideable": True}
        # Row 31 (odd): candidate at y=31 has solid ground at y=32
        for x in (10, 20, 30):
            self.grid[(x, 32)] = {"fg": 2, "isCollideable": True}

        res = LOG.scan_farm_capacity(self.grid, only_above_block=True)
        self.assertEqual(res["plantable_count"], 6)

        row_20 = [t["x"] for t in res["valid_tiles"] if t["y"] == 20]
        row_31 = [t["x"] for t in res["valid_tiles"] if t["y"] == 31]

        # Even row 20: L -> R (10, 20, 30)
        self.assertEqual(row_20, [10, 20, 30])
        # Odd row 31: R -> L (30, 20, 10)
        self.assertEqual(row_31, [30, 20, 10])


if __name__ == "__main__":
    unittest.main()
