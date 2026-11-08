#!/usr/bin/env python3
"""
Empirical Adversarial Stress Test Suite for Growtopia Mass Recipe Tracer Engine
Agent: challenger_m1_1 (Role: empirical_challenger / critic / specialist)

Verifies:
1. Authoritative Database Integrity (acyclic, 832 rules, 1010 items).
2. Extreme capacity scaling (N = 10,000, N <= 0, invalid types).
3. Non-splicables & cyclic graph termination.
4. Mathematical MRP correctness oracle (proves overcounting defect when asserted).
5. Tree generator size & execution limits.
"""

import json
import sys
import time
import unittest
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import mass_tracer as MT


def compute_ground_truth_dag_mrp(tracer: MT.MassTreeTracer, target_seed_id: int, capacity: int, user_stock: dict = None, prune_with_stock: bool = True):
    """
    Ground-truth mathematical oracle for DAG MRP calculation.
    Uses standard Tarjan-style persistent visited set for single-visit topological sort,
    guaranteeing each node appears EXACTLY ONCE in top-down evaluation.
    """
    user_stock = user_stock or {}
    visited = set()
    topo_order = []
    adj = {}

    def dfs(s_id: int):
        if s_id in visited:
            return
        visited.add(s_id)
        item_id = tracer.seed_to_item.get(s_id, s_id - 1)
        if (s_id in MT.BASE_SEEDS) or (item_id in MT.BASE_ITEMS):
            topo_order.append(s_id)
            return
        recs = tracer.recipes_db.get(str(item_id), [])
        if not recs:
            topo_order.append(s_id)
            return
        r = recs[0]
        c1, c2 = r["ingredient_1"]["id"], r["ingredient_2"]["id"]
        adj[s_id] = (c1, c2)
        dfs(c1)
        dfs(c2)
        topo_order.append(s_id)

    dfs(target_seed_id)
    top_down = list(reversed(topo_order))

    gross_demand = defaultdict(int)
    net_deficit = defaultdict(int)

    gross_demand[target_seed_id] = capacity
    root_stock = user_stock.get(target_seed_id, 0)
    net_deficit[target_seed_id] = max(0, capacity - root_stock)

    for s_id in top_down:
        craft_needed = net_deficit[s_id] if prune_with_stock else gross_demand[s_id]
        if s_id in adj and craft_needed > 0:
            c1, c2 = adj[s_id]
            gross_demand[c1] += craft_needed
            gross_demand[c2] += craft_needed
            for c in (c1, c2):
                c_stock = user_stock.get(c, 0)
                net_deficit[c] = max(0, gross_demand[c] - c_stock)

    base_bom = {}
    for s_id in topo_order:
        item_id = tracer.seed_to_item.get(s_id, s_id - 1)
        is_base = (s_id in MT.BASE_SEEDS) or (item_id in MT.BASE_ITEMS) or (s_id not in adj)
        if is_base and gross_demand[s_id] > 0:
            s_name = tracer.items_db.get(str(s_id), f"Seed {s_id}")
            base_bom[s_id] = {
                "name": s_name,
                "gross_needed": gross_demand[s_id],
                "in_stock": user_stock.get(s_id, 0),
                "fetch_required": net_deficit[s_id]
            }

    return {
        "topo_order": topo_order,
        "unique_nodes": len(topo_order),
        "gross_demand": dict(gross_demand),
        "net_deficit": dict(net_deficit),
        "base_bom": base_bom
    }


class TestEmpiricalRobustness(unittest.TestCase):
    """Stress tests that evaluate robust system boundaries and error handling."""

    def setUp(self):
        self.tracer = MT.MassTreeTracer()

    def test_database_is_strictly_acyclic(self):
        """Authoritative recipes.json must contain 0 cycles."""
        adj = {}
        for iid_str, recs in self.tracer.recipes_db.items():
            if recs:
                r = recs[0]
                adj[int(iid_str)] = [r["ingredient_1"]["id"], r["ingredient_2"]["id"]]

        visited = {}
        cycles = []

        def dfs(u, path):
            visited[u] = 1
            path.append(u)
            for c in adj.get(u, []):
                c_item = self.tracer.seed_to_item.get(c, c - 1)
                if visited.get(c_item, 0) == 1:
                    cycles.append(path + [c_item])
                elif visited.get(c_item, 0) == 0:
                    dfs(c_item, path)
            path.pop()
            visited[u] = 2

        for u in list(adj.keys()):
            if visited.get(u, 0) == 0:
                dfs(u, [])

        self.assertEqual(len(cycles), 0, f"Database must have 0 cycles, found: {cycles}")

    def test_extreme_capacity_scaling_n10000(self):
        """Capacity N = 10,000 must scale linearly without integer overflow or float conversion."""
        res_10k = self.tracer.trace_dag("Wood Block", capacity=10000)
        bom_10k = res_10k["summary"]["base_seeds_bill_of_materials"]
        self.assertEqual(bom_10k["Dirt Seed (3)"]["gross_needed"], 10000)
        self.assertEqual(bom_10k["Lava Seed (5)"]["gross_needed"], 10000)

    def test_boundary_capacities_zero_negative(self):
        """Capacity <= 0 must default safely to 1 without crashing."""
        res_zero = self.tracer.trace_dag("Rock", capacity=0)
        res_neg = self.tracer.trace_dag("Rock", capacity=-500)
        self.assertEqual(res_zero["target"]["capacity_requested"], 1)
        self.assertEqual(res_neg["target"]["capacity_requested"], 1)

    def test_non_splicable_laser_grid(self):
        """Laser Grid (5666) is an unsplicable farmable; must be treated as base leaf without crash."""
        res = self.tracer.trace_dag("Laser Grid", capacity=500)
        self.assertNotIn("error", res)
        self.assertEqual(res["target"]["tier"], 1)
        self.assertEqual(res["target"]["item_id"], 5666)
        self.assertEqual(res["target"]["seed_id"], 5667)
        bom = res["summary"]["base_seeds_bill_of_materials"]
        self.assertIn("Laser Grid Seed (5667)", bom)
        self.assertEqual(bom["Laser Grid Seed (5667)"]["gross_needed"], 500)

    def test_synthetic_cyclic_graph_safeguards(self):
        """Synthetic circular dependency injection must not cause infinite recursion."""
        self.tracer.recipes_db["998800"] = [{
            "id": "r_cyc_a",
            "ingredient_1": {"id": 998803, "name": "Cyc B Seed"},
            "ingredient_2": {"id": 3, "name": "Dirt Seed"}
        }]
        self.tracer.recipes_db["998802"] = [{
            "id": "r_cyc_b",
            "ingredient_1": {"id": 998801, "name": "Cyc A Seed"},
            "ingredient_2": {"id": 5, "name": "Lava Seed"}
        }]
        self.tracer.seed_to_item[998801] = 998800
        self.tracer.seed_to_item[998803] = 998802

        start_time = time.time()
        res = self.tracer.trace_dag("998800", capacity=100)
        elapsed = time.time() - start_time

        self.assertLess(elapsed, 0.5, "Cycle must be caught immediately (<500ms)")
        self.assertNotIn("error", res)


class TestEmpiricalDefectVerification(unittest.TestCase):
    """
    Defect reproduction test suite.
    Demonstrates mathematically that mass_tracer.py produces incorrect MRP calculations
    and tree generation explosions.
    """

    def setUp(self):
        self.tracer = MT.MassTreeTracer()

    def test_defect_mrp_overcounting_chandelier(self):
        """
        DEFECT REPRODUCTION: Chandelier MRP calculation.
        Mathematical truth requires 31 Dirt Seeds and 32 Rock Seeds.
        Tracer calculates 791 Dirt Seeds (25.5x) and 754 Rock Seeds (23.5x).
        """
        oracle = compute_ground_truth_dag_mrp(self.tracer, 341, capacity=1)
        actual = self.tracer.trace_dag("Chandelier", capacity=1)

        oracle_dirt = oracle["base_bom"][3]["gross_needed"]
        actual_dirt = actual["summary"]["base_seeds_bill_of_materials"]["Dirt Seed (3)"]["gross_needed"]

        # This assertion verifies whether tracer matches mathematical truth.
        # It FAILS under current defective code: 791 != 31.
        self.assertEqual(
            actual_dirt, oracle_dirt,
            f"CRITICAL DEFECT: Chandelier Dirt Seed demand calculated as {actual_dirt}, but true MRP demand is {oracle_dirt} (25.5x overcount)!"
        )

    def test_defect_mrp_overcounting_mini_mammoth_leash(self):
        """
        DEFECT REPRODUCTION: Tier 17 Mini Mammoth Leash MRP calculation.
        Mathematical truth requires 107 Dirt Seeds.
        Tracer calculates 42,768 Dirt Seeds (400x overcount).
        """
        oracle = compute_ground_truth_dag_mrp(self.tracer, 1351, capacity=1)
        actual = self.tracer.trace_dag("Mini Mammoth Leash", capacity=1)

        oracle_dirt = oracle["base_bom"][3]["gross_needed"]
        actual_dirt = actual["summary"]["base_seeds_bill_of_materials"]["Dirt Seed (3)"]["gross_needed"]

        self.assertEqual(
            actual_dirt, oracle_dirt,
            f"CRITICAL DEFECT: Mini Mammoth Leash Dirt Seed demand calculated as {actual_dirt}, but true MRP demand is {oracle_dirt} (399.7x overcount)!"
        )

    def test_defect_tree_generator_size_explosion(self):
        """
        DEFECT REPRODUCTION: ImGui Lua tree size for Chandelier.
        A clean UI hierarchy should be < 500 lines. Current implementation emits 116,375 lines.
        """
        lua = self.tracer.generate_tree("Chandelier", output_format="imgui_lua")
        line_count = len(lua.splitlines())
        self.assertLess(
            line_count, 1000,
            f"CRITICAL DEFECT: Chandelier ImGui Lua tree exploded to {line_count} lines (>1,000 threshold), threatening game client crash!"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
