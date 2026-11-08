#!/usr/bin/env python3
"""
Unit Test Suite for Growtopia Mass Recipe Tracer Engine & HTTP Bridge
mr_berk edition

Covers:
1. Recipe database integrity (recipes.json schema, 832 rules, 1010+ items)
2. DAG model & backtracking DFS traversal with active critical path styling
3. Material Requirements Planning (MRP) capacity calculator, convergence, stock netting
4. Tree formats (nested JSON, flat graph, single-threaded in-game ImGui Lua)
5. FastMCP tools (gh_mass_trace, gh_mass_recipes, gh_mass_tree)
6. HTTP Bridge endpoints (/mass, /mass/data, /mass/trace, /sprite/<id>.png, /mass/action)
"""

import asyncio
import io
import json
import os
import sys
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import mass_tracer as MT
import server as S
import bridge as B


class TestRecipeDatabase(unittest.TestCase):
    """Verifies recipes.json integrity, schema compliance, and Growtopia pairing rules."""

    @classmethod
    def setUpClass(cls):
        cls.recipes_file = REPO_ROOT / "data" / "recipes.json"
        with open(cls.recipes_file, "r", encoding="utf-8") as f:
            cls.db = json.load(f)

    def test_metadata_and_rule_counts(self):
        meta = self.db.get("metadata", {})
        self.assertIn("version", meta)
        self.assertEqual(meta.get("total_rules"), 832, "Must cover all 832 authoritative rules")
        self.assertGreaterEqual(meta.get("total_spliceable_items", 0), 1010)
        self.assertGreaterEqual(len(self.db.get("items", {})), 1010)

    def test_item_seed_pairing_law(self):
        items = self.db["items"]
        # Wood Block (100) -> Wood Block Seed (101)
        self.assertIn("100", items)
        wood = items["100"]
        self.assertEqual(wood["seed_id"], 101)
        self.assertEqual(wood["name"], "Wood Block")
        self.assertEqual(wood["seed_name"], "Wood Block Seed")

        # Chandelier (340) -> Chandelier Seed (341)
        self.assertIn("340", items)
        chandi = items["340"]
        self.assertEqual(chandi["seed_id"], 341)
        self.assertEqual(chandi["name"], "Chandelier")

    def test_growth_times_and_fruit_drops(self):
        items = self.db["items"]
        # Wood Block: 68s, max drop 8
        self.assertEqual(items["100"]["growth_seconds"], 68)
        self.assertEqual(items["100"]["max_fruit_drop"], 8)

        # Chandelier: 661113s
        self.assertEqual(items["340"]["growth_seconds"], 661113)
        self.assertEqual(items["340"]["growth_formatted"], "7d 15h 38m 33s")

    def test_multi_output_range_expansion(self):
        items = self.db["items"]
        # Tangram Blocks A (626) to L (648)
        self.assertIn("626", items)
        tangram_a = items["626"]
        self.assertTrue(tangram_a["recipe"]["is_multi_output"])
        self.assertIn(648, tangram_a["recipe"]["output_siblings"])


class TestMassTreeTracerDAG(unittest.TestCase):
    """Tests DAG traversal, backtracking DFS, MRP calculation, stock pruning, and cycle safety."""

    def setUp(self):
        self.tracer = MT.MassTreeTracer()

    def test_target_resolution(self):
        # By string name
        res = self.tracer.resolve_target("Wood Block")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], 100)
        self.assertEqual(res[1], 101)

        # By seed name
        res_seed = self.tracer.resolve_target("Wood Block Seed")
        self.assertIsNotNone(res_seed)
        self.assertEqual(res_seed[0], 100)
        self.assertEqual(res_seed[1], 101)

        # By item ID
        res_id = self.tracer.resolve_target("100")
        self.assertIsNotNone(res_id)
        self.assertEqual(res_id[0], 100)

        # Case insensitive
        res_case = self.tracer.resolve_target("cHaNdElIeR")
        self.assertIsNotNone(res_case)
        self.assertEqual(res_case[0], 340)

    def test_tier_1_base_leaf_tracing(self):
        # Rock is a base leaf (Tier 1)
        res = self.tracer.trace_dag("Rock", capacity=300)
        self.assertNotIn("error", res)
        target = res["target"]
        self.assertEqual(target["item_id"], 10)
        self.assertEqual(target["seed_id"], 11)
        self.assertEqual(target["tier"], 1)

        bom = res["summary"]["base_seeds_bill_of_materials"]
        self.assertIn("Rock Seed (11)", bom)
        self.assertEqual(bom["Rock Seed (11)"]["gross_needed"], 300)
        self.assertEqual(bom["Rock Seed (11)"]["fetch_required"], 300)

    def test_tier_2_wood_block_mrp(self):
        # Wood Block (100) = Dirt Seed (3) + Lava Seed (5)
        res = self.tracer.trace_dag("Wood Block", capacity=300)
        self.assertNotIn("error", res)
        summary = res["summary"]
        self.assertEqual(summary["tier_depth"], 2)
        bom = summary["base_seeds_bill_of_materials"]
        self.assertEqual(bom["Dirt Seed (3)"]["gross_needed"], 300)
        self.assertEqual(bom["Lava Seed (5)"]["gross_needed"], 300)
        self.assertEqual(len(res["execution_roadmap"]), 1)

    def test_multi_tier_chandelier_tracing(self):
        # Chandelier (340) -> Multi-tier DAG down to Tier 1
        res = self.tracer.trace_dag("Chandelier", capacity=100)
        self.assertNotIn("error", res)
        target = res["target"]
        self.assertEqual(target["tier"], 12)
        bom = res["summary"]["base_seeds_bill_of_materials"]
        # Must require Dirt, Lava, Rock, Cave
        self.assertIn("Dirt Seed (3)", bom)
        self.assertIn("Lava Seed (5)", bom)
        self.assertIn("Rock Seed (11)", bom)
        self.assertIn("Cave Background Seed (15)", bom)
        self.assertGreater(len(res["dag"]["nodes"]), 10)

    def test_stock_pruning_mrp(self):
        # If user has 300 Dirt Seeds in stock, fetch_required becomes 0
        res = self.tracer.trace_dag("Wood Block", capacity=300, user_stock={3: 300})
        bom = res["summary"]["base_seeds_bill_of_materials"]
        self.assertEqual(bom["Dirt Seed (3)"]["gross_needed"], 300)
        self.assertEqual(bom["Dirt Seed (3)"]["in_stock"], 300)
        self.assertEqual(bom["Dirt Seed (3)"]["fetch_required"], 0)
        self.assertEqual(bom["Lava Seed (5)"]["fetch_required"], 300)

    def test_active_critical_path_visual_styling(self):
        res = self.tracer.trace_dag("Wood Block", capacity=1)
        nodes = res["dag"]["nodes"]
        edges = res["dag"]["edges"]

        # Check active nodes styling
        active_nodes = [n for n in nodes if n["visual"]["is_active"]]
        self.assertGreaterEqual(len(active_nodes), 3)
        for n in active_nodes:
            self.assertEqual(n["visual"]["color"], "#10B981")
            self.assertEqual(n["visual"]["stroke_width"], 3.5)
            self.assertTrue(n["visual"]["glow"])
            self.assertEqual(n["visual"]["opacity"], 1.0)

        # Check active edges styling
        active_edges = [e for e in edges if e["visual"]["is_active"]]
        self.assertGreaterEqual(len(active_edges), 2)
        for e in active_edges:
            self.assertEqual(e["visual"]["stroke"], "#10B981")
            self.assertEqual(e["visual"]["stroke_width"], 3.5)
            self.assertTrue(e["visual"]["animated_pulse"])

    def test_cycle_protection(self):
        # 1. Test multi-tier complex splicing tree (Steel Block)
        res = self.tracer.trace_dag("Steel Block", capacity=50)
        self.assertNotIn("error", res)
        self.assertGreater(len(res["dag"]["nodes"]), 5)

        # 2. Genuine cycle safeguard test: artificially inject circular dependency
        # Seed 999901 -> Seed 999903 -> Seed 999901
        self.tracer.recipes_db["999900"] = [{
            "id": "r_cycle_1",
            "ingredient_1": {"id": 999903, "name": "Cycle B Seed"},
            "ingredient_2": {"id": 3, "name": "Dirt Seed"}
        }]
        self.tracer.recipes_db["999902"] = [{
            "id": "r_cycle_2",
            "ingredient_1": {"id": 999901, "name": "Cycle A Seed"},
            "ingredient_2": {"id": 5, "name": "Lava Seed"}
        }]
        self.tracer.seed_to_item[999901] = 999900
        self.tracer.seed_to_item[999903] = 999902

        # Must terminate safely without RecursionError
        cycle_res = self.tracer.trace_dag("999900", capacity=10)
        self.assertNotIn("error", cycle_res)
        self.assertIn("dag", cycle_res)


class TestTreeGenerators(unittest.TestCase):
    """Tests tree output formats: nested JSON, flat graph, and in-game ImGui Lua code."""

    def setUp(self):
        self.tracer = MT.MassTreeTracer()

    def test_generate_tree_nested(self):
        tree = self.tracer.generate_tree("Wood Block", output_format="nested")
        self.assertIsInstance(tree, dict)
        self.assertEqual(tree["name"], "Wood Block")
        self.assertEqual(len(tree["children"]), 2)
        child_names = [c["seed_name"] for c in tree["children"]]
        self.assertIn("Dirt Seed", child_names)
        self.assertIn("Lava Seed", child_names)

    def test_generate_tree_flat(self):
        flat = self.tracer.generate_tree("Wood Block", output_format="flat")
        self.assertIsInstance(flat, dict)
        self.assertIn("nodes", flat)
        self.assertIn("edges", flat)
        self.assertEqual(len(flat["nodes"]), 3)

    def test_generate_tree_imgui_lua(self):
        lua = self.tracer.generate_tree("Wood Block", output_format="imgui_lua")
        self.assertIsInstance(lua, str)
        # Check AGENTS.md required repo comment
        self.assertIn("-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp", lua)
        # Check AGENTS.md required watermark
        self.assertIn('ImGui.TextUnformatted("By BrK | Discord : mr_berk.")', lua)
        # Check single-threaded ImGui syntax
        self.assertIn("if ImGui.TreeNode(", lua)
        self.assertIn("ImGui.TreePop()", lua)
        # Verify ASCII only (no Turkish characters)
        turkish_chars = ["ğ", "ü", "ş", "ı", "ö", "ç", "İ", "Ğ", "Ü", "Ş", "Ö", "Ç"]
        for tc in turkish_chars:
            self.assertNotIn(tc, lua, f"Lua string must not contain Turkish character '{tc}'")


class TestFastMCPMassTools(unittest.TestCase):
    """Tests FastMCP tool registrations and invocations in server.py."""

    def test_tools_registered_in_fastmcp(self):
        async def check():
            tools = await S.mcp.list_tools()
            names = [t.name for t in tools]
            self.assertIn("gh_mass_trace", names)
            self.assertIn("gh_mass_recipes", names)
            self.assertIn("gh_mass_tree", names)
        asyncio.run(check())

    def test_gh_mass_trace_execution(self):
        out = S.gh_mass_trace("Wood Block", capacity=250)
        data = json.loads(out)
        self.assertEqual(data["target"]["item_name"], "Wood Block")
        self.assertEqual(data["target"]["capacity_requested"], 250)
        self.assertEqual(data["summary"]["base_seeds_bill_of_materials"]["Dirt Seed (3)"]["gross_needed"], 250)

    def test_gh_mass_recipes_filter_modes(self):
        # By target
        res_target = json.loads(S.gh_mass_recipes("Wood", filter_by="target", limit=5))
        self.assertGreater(res_target["count"], 0)

        # By ingredient (Dirt Seed ID 3)
        res_ing = json.loads(S.gh_mass_recipes("3", filter_by="ingredient", limit=5))
        self.assertGreater(res_ing["count"], 0)

        # By tier
        res_tier = json.loads(S.gh_mass_recipes("2", filter_by="tier", limit=5))
        self.assertGreater(res_tier["count"], 0)

    def test_gh_mass_tree_execution(self):
        out_lua = S.gh_mass_tree("Rock", format="imgui_lua")
        self.assertIn("Rock Seed", out_lua)
        self.assertIn("By BrK", out_lua)


class TestHTTPRelayBridge(unittest.TestCase):
    """Tests embedded HTTP Relay endpoints on bridge.py."""

    @classmethod
    def setUpClass(cls):
        cls.port = 8829
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        B.start_http_relay(port=cls.port)

    def test_route_mass_html_dashboard(self):
        url = f"{self.base_url}/mass"
        req = urllib.request.urlopen(url, timeout=5)
        self.assertEqual(req.status, 200)
        content_type = req.headers.get("Content-Type", "")
        self.assertIn("text/html", content_type)
        body = req.read().decode("utf-8")
        self.assertIn("GENTAHAX MASS TRACER", body)
        self.assertIn("dagCanvas", body)
        self.assertIn("Only Above Solid Blocks", body)

    def test_route_mass_data(self):
        url = f"{self.base_url}/mass/data"
        req = urllib.request.urlopen(url, timeout=5)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("world", data)
        self.assertIn("player", data)
        self.assertIn("drop_zone", data)

    def test_route_mass_trace(self):
        url = f"{self.base_url}/mass/trace?target=Wood%20Block&capacity=300"
        req = urllib.request.urlopen(url, timeout=5)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertEqual(data["target"]["item_name"], "Wood Block")
        self.assertEqual(data["summary"]["tier_depth"], 2)

    def test_route_mass_recipes(self):
        url = f"{self.base_url}/mass/recipes?query=Wood&limit=5"
        req = urllib.request.urlopen(url, timeout=5)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("recipes", data)
        self.assertGreater(data["count"], 0)

    def test_route_sprite_pipeline(self):
        url = f"{self.base_url}/sprite/100.png"
        req = urllib.request.urlopen(url, timeout=5)
        self.assertEqual(req.status, 200)
        content_type = req.headers.get("Content-Type", "")
        self.assertEqual(content_type, "image/png")
        data = req.read()
        self.assertGreater(len(data), 50)
        # Verify valid PNG header
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")

        # Open with PIL to verify genuine 32x32 dimensions
        img = Image.open(io.BytesIO(data))
        self.assertEqual(img.size, (32, 32))

    def test_route_mass_action_post(self):
        url = f"{self.base_url}/mass/action"
        payload = json.dumps({"action": "scan_capacity", "only_above_block": True}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        self.assertEqual(resp.status, 200)
        res = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(res.get("ok"))
        self.assertIn("capacity", res)


class TestRemediatedAlgorithmicAccuracyAndHardening(unittest.TestCase):
    """Verifies remediated topological sort, single-visit MRP, bounded tree generation, and input hardening."""

    def setUp(self):
        self.tracer = MT.MassTreeTracer()

    def test_chandelier_exact_ground_truth_bom(self):
        """If this test fails, diamond DAG topological sort or MRP demand propagation has regressed."""
        res = self.tracer.trace_dag("Chandelier", capacity=1)
        bom = res["summary"]["base_seeds_bill_of_materials"]
        self.assertEqual(bom["Dirt Seed (3)"]["gross_needed"], 31)
        self.assertEqual(bom["Rock Seed (11)"]["gross_needed"], 32)
        self.assertEqual(bom["Lava Seed (5)"]["gross_needed"], 11)
        self.assertEqual(bom["Cave Background Seed (15)"]["gross_needed"], 13)

    def test_mini_mammoth_leash_exact_ground_truth_bom(self):
        """If this test fails, deep Tier 17 DAG MRP calculation has regressed."""
        res = self.tracer.trace_dag("Mini Mammoth Leash", capacity=1)
        bom = res["summary"]["base_seeds_bill_of_materials"]
        self.assertEqual(bom["Dirt Seed (3)"]["gross_needed"], 107)
        self.assertEqual(bom["Rock Seed (11)"]["gross_needed"], 100)

    def test_generate_tree_lua_bounded_size_and_timing(self):
        """If this test fails, tree generator deduplication or subtree memoization has regressed."""
        import time
        lua_chan = self.tracer.generate_tree("Chandelier", output_format="imgui_lua")
        self.assertLess(len(lua_chan.splitlines()), 500)

        t0 = time.perf_counter()
        lua_mml = self.tracer.generate_tree("Mini Mammoth Leash", output_format="imgui_lua")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 50.0)
        self.assertLess(len(lua_mml.splitlines()), 500)

    def test_trace_dag_capacity_and_stock_hardening(self):
        """If this test fails, input sanitization for capacity or user stock has broken."""
        # Non-integer capacity fallback
        res_none = self.tracer.trace_dag("Rock", capacity=None)
        self.assertEqual(res_none["target"]["capacity_requested"], 1)

        res_abc = self.tracer.trace_dag("Rock", capacity="abc")
        self.assertEqual(res_abc["target"]["capacity_requested"], 1)

        res_float = self.tracer.trace_dag("Rock", capacity="50.0")
        self.assertEqual(res_float["target"]["capacity_requested"], 50)

        # String-key dictionary normalization
        res_stock = self.tracer.trace_dag("Wood Block", capacity=10, user_stock={"3": 10})
        bom = res_stock["summary"]["base_seeds_bill_of_materials"]
        self.assertEqual(bom["Dirt Seed (3)"]["in_stock"], 10)
        self.assertEqual(bom["Dirt Seed (3)"]["fetch_required"], 0)

    def test_intermediate_seed_detection_and_skip(self):
        """Verifies that holding intermediate tree seeds automatically skips prior crafts and targets the active tree."""
        # Aqua Block (4 operations: Grass, Bricks, Glass Pane, Aqua Block)
        # If user holds 100 Bricks Seeds (ID: 117), Grass and Bricks are skipped, starting from Glass Pane (step 3)
        res = self.tracer.trace_dag("Aqua Block", capacity=100, user_stock={117: 100}, prune_with_stock=True)
        summary = res["summary"]
        self.assertEqual(summary["skipped_operations_count"], 2)
        self.assertEqual(summary["first_active_step"], 3)
        self.assertEqual(summary["first_active_target"], "Glass Pane Seed")

        ops = res["flat_operations"]
        self.assertEqual(len(ops), 4)
        self.assertTrue(ops[0]["is_satisfied_by_stock"])
        self.assertTrue(ops[1]["is_satisfied_by_stock"])
        self.assertFalse(ops[2]["is_satisfied_by_stock"])
        self.assertTrue(ops[2]["is_first_active_step"])


if __name__ == "__main__":
    unittest.main()

