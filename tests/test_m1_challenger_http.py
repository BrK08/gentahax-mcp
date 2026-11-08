#!/usr/bin/env python3
"""
Empirical Adversarial Challenge Suite: HTTP Bridge Endpoints & FastMCP Tools
Milestone 1 — challenger_m1_2

Verifies:
1. HTTP Relay Endpoints (/mass, /mass/data, /mass/trace, /sprite/<id>.png, /mass/action, /save_state)
   - Edge query parameters, invalid types, malformed payloads
   - Server survival under invalid inputs
   - Concurrency stress (parallel requests via ThreadPoolExecutor)
   - Data consistency and CORS headers
2. FastMCP Tool Wrappers (server.py: gh_mass_trace, gh_mass_recipes, gh_mass_tree)
   - Tool reflection and schema compliance via mcp.list_tools()
   - Programmatic invocation via server.mcp.call_tool and direct Python callables
   - Stock netting (JSON dict and name:count formats), pruning flags, boundary inputs
   - ASCII compliance, required headers, and watermarks in generated ImGui Lua
"""

import asyncio
import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import bridge as B
import mass_tracer as MT
import server as S

CHALLENGE_PORT = 8841
BASE_URL = f"http://127.0.0.1:{CHALLENGE_PORT}"


class TestHttpBridgeEndpointsChallenge(unittest.TestCase):
    """Empirical challenge tests for HTTP bridge endpoints under edge parameters, invalid types, and concurrency."""

    @classmethod
    def setUpClass(cls):
        # Start the HTTP relay on an isolated port
        started = B.start_http_relay(CHALLENGE_PORT)
        import time
        time.sleep(0.3)

    def _http_get(self, path: str, timeout: float = 5.0):
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "ChallengerTest/1.0"})
        return urllib.request.urlopen(req, timeout=timeout)

    def _http_post(self, path: str, data: bytes, content_type: str = "application/json", timeout: float = 5.0):
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url, data=data, headers={"Content-Type": content_type, "User-Agent": "ChallengerTest/1.0"})
        return urllib.request.urlopen(req, timeout=timeout)

    # -----------------------------------------------------------------------
    # 1. /mass (Dashboard Web Interface)
    # -----------------------------------------------------------------------
    def test_mass_endpoint_paths_and_content(self):
        """Tests /mass, /mass/, and /mass/index.html with edge query parameters."""
        for p in ("/mass", "/mass/", "/mass/index.html", "/mass?cache_bust=12345&lang=en"):
            with self._http_get(p) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("text/html", resp.headers.get("Content-Type", ""))
                body = resp.read().decode("utf-8")
                self.assertIn("GENTAHAX MASS TRACER", body)
                self.assertIn("dagCanvas", body)
                self.assertIn("By BrK | Discord : mr_berk.", body)

    def test_mass_endpoint_concurrency(self):
        """Stress-tests /mass with 50 concurrent GET requests."""
        def fetch():
            with self._http_get("/mass") as resp:
                return resp.status, len(resp.read())

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(fetch) for _ in range(50)]
            for f in as_completed(futures):
                status, length = f.result()
                self.assertEqual(status, 200)
                self.assertGreater(length, 1000)

    # -----------------------------------------------------------------------
    # 2. /mass/data (Session & Live Bot State)
    # -----------------------------------------------------------------------
    def test_mass_data_schema_and_cors(self):
        """Validates /mass/data schema, JSON compliance, and CORS header."""
        with self._http_get("/mass/data?param=ignore_me") as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("application/json", resp.headers.get("Content-Type", ""))
            data = json.loads(resp.read().decode("utf-8"))

        required_keys = ["world", "player", "gems", "bot_phase", "scanned_capacity", "drop_zone"]
        for k in required_keys:
            self.assertIn(k, data, f"Missing required key '{k}' in /mass/data")
        self.assertIn("x", data["drop_zone"])
        self.assertIn("y", data["drop_zone"])
        self.assertIn("limit", data["drop_zone"])

    def test_mass_data_concurrency(self):
        """Stress-tests /mass/data with 50 concurrent GET requests."""
        def fetch():
            with self._http_get("/mass/data") as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(fetch) for _ in range(50)]
            for f in as_completed(futures):
                status, data = f.result()
                self.assertEqual(status, 200)
                self.assertIn("world", data)

    # -----------------------------------------------------------------------
    # 3. /mass/trace (DAG & MRP Trace Engine over HTTP)
    # -----------------------------------------------------------------------
    def test_mass_trace_valid_queries(self):
        """Tests standard, item-name, seed-name, and ID queries."""
        cases = [
            ("target=Rock&capacity=100", 10, 1),
            ("target=Wood%20Block&capacity=300", 100, 2),
            ("target=Chandelier&capacity=50", 340, 12),
            ("target=341&capacity=10", 340, 12),  # Chandelier Seed ID
        ]
        for query_str, expected_item_id, expected_tier in cases:
            with self._http_get(f"/mass/trace?{query_str}") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["target"]["item_id"], expected_item_id)
                self.assertEqual(data["summary"]["tier_depth"], expected_tier)

    def test_mass_trace_edge_parameters(self):
        """Tests missing target, non-existent target, zero, negative, and extreme capacity."""
        # Missing target defaults to Chandelier
        with self._http_get("/mass/trace") as resp_def:
            self.assertEqual(resp_def.status, 200)
            data_def = json.loads(resp_def.read().decode("utf-8"))
            self.assertEqual(data_def["target"]["item_id"], 340)

        # Non-existent target returns JSON error object without 500 crash
        with self._http_get("/mass/trace?target=NonExistentItem9999999") as resp_err:
            self.assertEqual(resp_err.status, 200)
            data_err = json.loads(resp_err.read().decode("utf-8"))
            self.assertIn("error", data_err)

        # Zero and negative capacity clamped to >= 1
        for cap in (0, -10):
            with self._http_get(f"/mass/trace?target=Rock&capacity={cap}") as resp_cap:
                self.assertEqual(resp_cap.status, 200)
                data_cap = json.loads(resp_cap.read().decode("utf-8"))
                self.assertGreaterEqual(data_cap["target"]["capacity_requested"], 1)

        # Huge capacity
        with self._http_get("/mass/trace?target=Rock&capacity=1000000") as resp_huge:
            self.assertEqual(resp_huge.status, 200)
            data_huge = json.loads(resp_huge.read().decode("utf-8"))
            self.assertEqual(data_huge["target"]["capacity_requested"], 1000000)

    def test_mass_trace_invalid_type_and_server_resilience(self):
        """
        Adversarial test: Send non-integer capacity to /mass/trace.
        Verifies that even if the request triggers a ValueError in int(capacity),
        the HTTP server remains alive and immediately responds to subsequent valid requests.
        """
        try:
            self._http_get("/mass/trace?target=Rock&capacity=invalid_abc")
        except Exception:
            # RemoteDisconnected or HTTPError expected due to int() conversion
            pass

        # Verify server is still alive and healthy
        with self._http_get("/mass/data") as resp:
            self.assertEqual(resp.status, 200)

    def test_mass_trace_stock_parameter_and_behavior(self):
        """
        Tests the 'stock' query parameter on /mass/trace.
        Checks malformed JSON handling and validates behavior with user stock.
        """
        # Malformed JSON stock is handled gracefully without crashing
        with self._http_get("/mass/trace?target=Rock&capacity=10&stock={malformed_json") as resp_bad:
            self.assertEqual(resp_bad.status, 200)
            data_bad = json.loads(resp_bad.read().decode("utf-8"))
            self.assertIn("target", data_bad)

        # Valid JSON stock parameter
        with self._http_get("/mass/trace?target=Wood%20Block&capacity=10&stock=%7B%223%22%3A10%7D") as resp_stock:
            self.assertEqual(resp_stock.status, 200)
            data_stock = json.loads(resp_stock.read().decode("utf-8"))
            self.assertIn("target", data_stock)

    def test_mass_trace_concurrency(self):
        """Stress-tests /mass/trace with 50 concurrent requests evaluating different recipes."""
        targets = ["Rock", "Wood Block", "Door", "Glass Pane", "Laser Grid", "Chandelier"]

        def fetch(idx):
            tgt = targets[idx % len(targets)]
            with self._http_get(f"/mass/trace?target={urllib.parse.quote(tgt)}&capacity=200") as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(fetch, i) for i in range(50)]
            for f in as_completed(futures):
                status, data = f.result()
                self.assertEqual(status, 200)
                self.assertIn("dag", data)
                self.assertGreater(len(data["dag"]["nodes"]), 0)

    # -----------------------------------------------------------------------
    # 4. /sprite/<id>.png (32x32 Genuine & Procedural Sprite Pipeline)
    # -----------------------------------------------------------------------
    def test_sprite_pipeline_valid_and_fallbacks(self):
        """Tests sprite generation, PNG integrity, and fallback mechanisms."""
        # 1. Standard Dirt (2)
        with self._http_get("/sprite/2.png") as resp_dirt:
            self.assertEqual(resp_dirt.status, 200)
            self.assertEqual(resp_dirt.headers.get("Content-Type"), "image/png")
            dirt_bytes = resp_dirt.read()
            self.assertTrue(dirt_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
            img = Image.open(io.BytesIO(dirt_bytes))
            self.assertEqual(img.size, (32, 32))

        # 2. Non-numeric ID: /sprite/invalid.png -> safely defaults to 2
        with self._http_get("/sprite/invalid_abc.png") as resp_invalid:
            self.assertEqual(resp_invalid.status, 200)
            self.assertTrue(resp_invalid.read().startswith(b"\x89PNG\r\n\x1a\n"))

        # 3. Negative ID: /sprite/-5.png -> safely defaults to 2
        with self._http_get("/sprite/-5.png") as resp_neg:
            self.assertEqual(resp_neg.status, 200)
            self.assertTrue(resp_neg.read().startswith(b"\x89PNG\r\n\x1a\n"))

        # 4. Non-existent item ID: /sprite/99999999.png -> procedural fallback
        with self._http_get("/sprite/99999999.png") as resp_proc:
            self.assertEqual(resp_proc.status, 200)
            proc_bytes = resp_proc.read()
            self.assertTrue(proc_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
            proc_img = Image.open(io.BytesIO(proc_bytes))
            self.assertEqual(proc_img.size, (32, 32))

    def test_sprite_caching_and_concurrency(self):
        """Stress-tests sprite endpoint with 60 concurrent requests and validates caching."""
        ids = [2, 3, 5, 10, 11, 100, 101, 340, 341, 5666, 999999]

        def fetch(idx):
            item_id = ids[idx % len(ids)]
            with self._http_get(f"/sprite/{item_id}.png") as resp:
                return resp.status, len(resp.read())

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(fetch, i) for i in range(60)]
            for f in as_completed(futures):
                status, length = f.result()
                self.assertEqual(status, 200)
                self.assertGreater(length, 50)

    # -----------------------------------------------------------------------
    # 5. /mass/action (POST Operator Actions & Resilience)
    # -----------------------------------------------------------------------
    def test_mass_action_valid_endpoints(self):
        """Tests scan_capacity, trigger_harvest, and set_drop_zone POST actions."""
        # 1. scan_capacity
        p1 = json.dumps({"action": "scan_capacity", "only_above_block": True}).encode("utf-8")
        with self._http_post("/mass/action", p1) as resp1:
            self.assertEqual(resp1.status, 200)
            d1 = json.loads(resp1.read().decode("utf-8"))
            self.assertTrue(d1.get("ok"))
            self.assertEqual(d1.get("capacity"), 300)

        # 2. trigger_harvest
        p2 = json.dumps({"action": "trigger_harvest"}).encode("utf-8")
        with self._http_post("/mass/action", p2) as resp2:
            self.assertEqual(resp2.status, 200)
            d2 = json.loads(resp2.read().decode("utf-8"))
            self.assertTrue(d2.get("ok"))

        # Verify state updated in /mass/data
        with self._http_get("/mass/data") as resp_data:
            state = json.loads(resp_data.read().decode("utf-8"))
            self.assertEqual(state.get("bot_phase"), "HARVESTING")

        # 3. set_drop_zone
        p3 = json.dumps({"action": "set_drop_zone", "world": "VAULT_TEST", "x": 62, "y": 28}).encode("utf-8")
        with self._http_post("/mass/action", p3) as resp3:
            self.assertEqual(resp3.status, 200)
            d3 = json.loads(resp3.read().decode("utf-8"))
            self.assertTrue(d3.get("ok"))
            self.assertEqual(d3["drop_zone"]["world"], "VAULT_TEST")
            self.assertEqual(d3["drop_zone"]["x"], 62)
            self.assertEqual(d3["drop_zone"]["y"], 28)

    def test_mass_action_malformed_payloads(self):
        """Tests malformed payloads (invalid JSON, list JSON, empty string, unknown action)."""
        # Malformed JSON
        with self._http_post("/mass/action", b"{invalid_json_missing_brace") as resp_bad:
            self.assertEqual(resp_bad.status, 200)
            d_bad = json.loads(resp_bad.read().decode("utf-8"))
            self.assertFalse(d_bad.get("ok"))
            self.assertIn("error", d_bad)

        # JSON List instead of Object
        with self._http_post("/mass/action", b"[1, 2, 3]") as resp_list:
            self.assertEqual(resp_list.status, 200)
            d_list = json.loads(resp_list.read().decode("utf-8"))
            self.assertFalse(d_list.get("ok"))

        # Empty body
        with self._http_post("/mass/action", b"") as resp_empty:
            self.assertEqual(resp_empty.status, 200)
            d_empty = json.loads(resp_empty.read().decode("utf-8"))
            self.assertTrue(d_empty.get("ok"))

        # Unknown action
        with self._http_post("/mass/action", json.dumps({"action": "dance_party"}).encode("utf-8")) as resp_unk:
            self.assertEqual(resp_unk.status, 200)
            d_unk = json.loads(resp_unk.read().decode("utf-8"))
            self.assertTrue(d_unk.get("ok"))

    def test_mass_action_and_data_concurrency(self):
        """Tests concurrent POST actions interleaved with concurrent GET /mass/data."""
        def post_action(i):
            payload = json.dumps({"action": "set_drop_zone", "world": f"WORLD_{i}", "x": i, "y": 20}).encode("utf-8")
            with self._http_post("/mass/action", payload) as r:
                r.read()
                return r.status

        def get_state(i):
            with self._http_get("/mass/data") as r:
                data = json.loads(r.read().decode("utf-8"))
                return r.status, data

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            for i in range(20):
                futures.append(pool.submit(post_action, i))
                futures.append(pool.submit(get_state, i))

            for f in as_completed(futures):
                res = f.result()
                if isinstance(res, tuple):
                    status, data = res
                    self.assertEqual(status, 200)
                    self.assertIn("world", data)
                else:
                    self.assertEqual(res, 200)

    # -----------------------------------------------------------------------
    # 6. /save_state & 404 Routing
    # -----------------------------------------------------------------------
    def test_save_state_and_404_routes(self):
        """Tests /save_state persistence endpoint and non-existent route 404s."""
        state_payload = json.dumps({"test_state": "active", "timestamp": 123456789}).encode("utf-8")
        with self._http_post("/save_state", state_payload) as resp_save:
            self.assertEqual(resp_save.status, 200)
            d_save = json.loads(resp_save.read().decode("utf-8"))
            self.assertTrue(d_save.get("ok"))

        # 404 Not Found on undefined endpoints
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_get("/non_existent_endpoint_xyz")
        self.assertEqual(ctx.exception.code, 404)


class TestFastMCPToolWrappersChallenge(unittest.TestCase):
    """Empirical challenge tests for FastMCP tool wrappers in server.py."""

    def test_fastmcp_tool_reflection_and_schemas(self):
        """Verifies FastMCP tool reflection and parameter schemas via mcp.list_tools()."""
        loop = asyncio.new_event_loop()
        try:
            tools = loop.run_until_complete(S.mcp.list_tools())
        finally:
            loop.close()

        tool_map = {t.name: t for t in tools}
        expected_tools = ["gh_mass_trace", "gh_mass_recipes", "gh_mass_tree"]
        for t_name in expected_tools:
            self.assertIn(t_name, tool_map, f"FastMCP tool '{t_name}' not registered in server.mcp")

        # Schema inspection for gh_mass_trace
        trace_tool = tool_map["gh_mass_trace"]
        props = trace_tool.parameters.get("properties", {})
        self.assertIn("target", props)
        self.assertIn("capacity", props)
        self.assertIn("stock", props)
        self.assertIn("prune_with_stock", props)
        self.assertIn("target", trace_tool.parameters.get("required", []))

    def test_gh_mass_trace_programmatic_invocations(self):
        """Tests programmatic invocations of gh_mass_trace via direct call and mcp.call_tool."""
        # 1. Direct call with Wood Block (ID 100)
        raw_res = S.gh_mass_trace(target="Wood Block", capacity=10)
        data = json.loads(raw_res)
        self.assertEqual(data["target"]["item_id"], 100)
        self.assertEqual(data["target"]["item_name"], "Wood Block")
        self.assertEqual(data["summary"]["tier_depth"], 2)

        # 2. Stock as JSON string with integer netting
        stock_json = json.dumps({"3": 10, "5": 5})
        res_stock = json.loads(S.gh_mass_trace(target="Wood Block", capacity=10, stock=stock_json))
        bom_dict = res_stock["summary"]["base_seeds_bill_of_materials"]
        bom = {item["seed_id"]: item for item in bom_dict.values()}
        self.assertEqual(bom[3]["in_stock"], 10)
        self.assertEqual(bom[3]["fetch_required"], 0)
        self.assertEqual(bom[5]["in_stock"], 5)
        self.assertEqual(bom[5]["fetch_required"], 5)

        # 3. Stock as comma-separated name:count string
        stock_csv = "Dirt Seed: 10, Lava Seed: 4"
        res_csv = json.loads(S.gh_mass_trace(target="Wood Block", capacity=10, stock=stock_csv))
        bom_csv_dict = res_csv["summary"]["base_seeds_bill_of_materials"]
        bom_csv = {item["seed_id"]: item for item in bom_csv_dict.values()}
        self.assertEqual(bom_csv[3]["in_stock"], 10)
        self.assertEqual(bom_csv[3]["fetch_required"], 0)
        self.assertEqual(bom_csv[5]["in_stock"], 4)
        self.assertEqual(bom_csv[5]["fetch_required"], 6)

        # 4. Malformed stock format returns graceful JSON error, does not raise
        res_bad_stock = json.loads(S.gh_mass_trace(target="Wood Block", capacity=10, stock="{broken_json"))
        self.assertIn("error", res_bad_stock)

        # 5. Negative capacity clamped to >= 1
        res_neg = json.loads(S.gh_mass_trace(target="Wood Block", capacity=-50))
        self.assertEqual(res_neg["target"]["capacity_requested"], 1)

        # 6. Unknown target returns JSON error
        res_unk = json.loads(S.gh_mass_trace(target="UnknownNonExistentXYZ999"))
        self.assertIn("error", res_unk)

        # 7. FastMCP mcp.call_tool invocation
        loop = asyncio.new_event_loop()
        try:
            mcp_res = loop.run_until_complete(
                S.mcp.call_tool("gh_mass_trace", {"target": "Wood Block", "capacity": 50})
            )
        finally:
            loop.close()

        # mcp_res is ToolResult with TextContent
        content_text = mcp_res.content[0].text
        data_mcp = json.loads(content_text)
        self.assertEqual(data_mcp["target"]["item_id"], 100)

    def test_gh_mass_recipes_programmatic_invocations(self):
        """Tests programmatic invocations of gh_mass_recipes."""
        # 1. Target search
        res_target = json.loads(S.gh_mass_recipes(query="Wood", filter_by="target", limit=5))
        self.assertGreater(res_target["count"], 0)
        self.assertIn("recipes", res_target)
        self.assertIn("watermark", res_target)

        # 2. Ingredient search
        res_ing = json.loads(S.gh_mass_recipes(query="Lava Seed", filter_by="ingredient", limit=5))
        self.assertGreater(res_ing["count"], 0)

        # 3. Tier search
        res_tier = json.loads(S.gh_mass_recipes(query="8", filter_by="tier", limit=10))
        self.assertGreater(res_tier["count"], 0)
        for r in res_tier["recipes"]:
            self.assertEqual(r["tier"], 8)

        # 4. Non-matching query
        res_none = json.loads(S.gh_mass_recipes(query="NonExistentQueryZXYZZZ", limit=10))
        self.assertEqual(res_none["count"], 0)
        self.assertEqual(len(res_none["recipes"]), 0)

        # 5. FastMCP mcp.call_tool invocation
        loop = asyncio.new_event_loop()
        try:
            mcp_res = loop.run_until_complete(
                S.mcp.call_tool("gh_mass_recipes", {"query": "Glass Pane", "limit": 2})
            )
        finally:
            loop.close()
        data_mcp = json.loads(mcp_res.content[0].text)
        self.assertGreaterEqual(data_mcp["count"], 1)

    def test_gh_mass_tree_formats_and_agents_md_compliance(self):
        """Tests gh_mass_tree formats and AGENTS.md rule compliance."""
        # 1. Nested format for Wood Block (has 2 ingredient children)
        res_nested = json.loads(S.gh_mass_tree(target="Wood Block", format="nested"))
        self.assertEqual(res_nested["name"], "Wood Block")
        self.assertIn("children", res_nested)
        self.assertEqual(len(res_nested["children"]), 2)

        # 2. Flat format
        res_flat = json.loads(S.gh_mass_tree(target="Wood Block", format="flat"))
        self.assertIn("nodes", res_flat)
        self.assertIn("edges", res_flat)

        # 3. ImGui Lua format — AGENTS.md rules compliance
        lua_code = S.gh_mass_tree(target="Wood Block", format="imgui_lua")

        # AGENTS.md Rule 4 (Header comment required on every script)
        self.assertIn(
            "-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp",
            lua_code,
            "Header comment missing from ImGui Lua generation"
        )

        # AGENTS.md Rule 4 (Watermark required before ImGui.End / TreePop)
        self.assertIn(
            'ImGui.TextUnformatted("By BrK | Discord : mr_berk.")',
            lua_code,
            "Watermark missing from ImGui Lua generation"
        )

        # AGENTS.md Rule 3 (ASCII-only constraint: Turkish chars forbidden)
        turkish_chars = ["ğ", "ü", "ş", "ı", "ö", "ç", "İ", "Ğ", "Ü", "Ş", "Ö", "Ç"]
        for ch in turkish_chars:
            self.assertNotIn(ch, lua_code, f"Turkish character '{ch}' found in ImGui Lua code!")

        # ImGui structure
        self.assertIn("ImGui.TreeNode", lua_code)
        self.assertIn("ImGui.TreePop()", lua_code)

        # 4. Error handling for unknown target
        err_res = S.gh_mass_tree(target="UnknownXYZItem999", format="nested")
        err_data = json.loads(err_res)
        self.assertIn("error", err_data)

        # 5. FastMCP mcp.call_tool invocation
        loop = asyncio.new_event_loop()
        try:
            mcp_res = loop.run_until_complete(
                S.mcp.call_tool("gh_mass_tree", {"target": "Wood Block", "format": "nested"})
            )
        finally:
            loop.close()
        data_mcp = json.loads(mcp_res.content[0].text)
        self.assertEqual(data_mcp["name"], "Wood Block")


if __name__ == "__main__":
    unittest.main(verbosity=2)
