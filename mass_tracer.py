"""
GENTAHAX MCP — Mass Recipe Tracer DAG Engine
mr_berk edition

Provides:
- Directed Acyclic Graph (DAG) recipe model.
- Recursive backtracking DFS traversal with cycle detection.
- Active critical path highlighting (#10B981 emerald green) vs inactive branches (#334155 slate).
- Two-pass topological Material Requirements Planning (MRP) for exact seed counts (Capacity N).
- Multi-parent demand convergence and inventory stock pruning.
- Hierarchy tree generators (nested JSON, flat graph, and in-game ImGui Lua code).
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Tier 1 Base Seeds (un-splicable roots in Growtopia)
BASE_SEEDS: Dict[int, str] = {
    3: "Dirt Seed",
    5: "Lava Seed",
    11: "Rock Seed",
    15: "Cave Background Seed",
    443: "Sand Seed",
    611: "Magic Egg",
    2035: "Starseed",
    2037: "Galactic Starseed",
}

# Base items corresponding to base seeds
BASE_ITEMS: Dict[int, int] = {
    2: 3,    # Dirt -> Dirt Seed
    4: 5,    # Lava -> Lava Seed
    10: 11,  # Rock -> Rock Seed
    14: 15,  # Cave Background -> Cave Background Seed
    442: 443,# Sand -> Sand Seed
    611: 611,
    2035: 2035,
    2037: 2037,
}


def format_duration(seconds: int) -> str:
    """Formats raw seconds into human-readable duration (e.g. 7d 15h 38m 33s)."""
    if seconds <= 0:
        return "Instant"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if mins > 0:
        parts.append(f"{mins}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


class MassTreeTracer:
    def __init__(
        self,
        recipes_path: Optional[str] = None,
        items_path: Optional[str] = None
    ):
        base_dir = Path(__file__).resolve().parent
        if not recipes_path:
            recipes_path = str(base_dir / "data" / "recipes.json")
        if not items_path:
            items_path = str(base_dir / "data" / "items.json")

        self.recipes_db: Dict[str, List[Dict[str, Any]]] = {}
        self.items_info: Dict[str, Dict[str, Any]] = {}
        self.by_seed_id: Dict[str, int] = {}
        self.by_ingredient: Dict[str, List[int]] = {}
        self.items_db: Dict[str, str] = {}
        self.seed_to_item: Dict[int, int] = {}
        self.item_to_seed: Dict[int, int] = {}

        self._load_items_db(items_path)
        self._load_recipes_db(recipes_path)

    def _load_items_db(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.items_db = data.get("items", {})

        for iid_str, name in self.items_db.items():
            iid = int(iid_str)
            clean_name = re.sub(r"\s+", " ", name).strip()
            if clean_name.endswith(" Seed"):
                base_name = clean_name[:-5].strip()
                if str(iid - 1) in self.items_db and re.sub(r"\s+", " ", self.items_db[str(iid - 1)]).strip() == base_name:
                    self.seed_to_item[iid] = iid - 1
                    self.item_to_seed[iid - 1] = iid
                else:
                    for cand_str, cand_name in self.items_db.items():
                        if re.sub(r"\s+", " ", cand_name).strip() == base_name and not cand_name.endswith(" Seed"):
                            cid = int(cand_str)
                            self.seed_to_item[iid] = cid
                            self.item_to_seed[cid] = iid
                            break

        # Register special catalysts
        self.seed_to_item[4455] = 4454
        self.item_to_seed[4454] = 4455
        self.seed_to_item[5721] = 5720
        self.item_to_seed[5720] = 5721
        for cat in (611, 2035, 2037):
            self.seed_to_item[cat] = cat
            self.item_to_seed[cat] = cat

    def _load_recipes_db(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.items_info = data.get("items", {})
            self.recipes_db = data.get("recipes", {})
            self.by_seed_id = {str(k): int(v) for k, v in data.get("by_seed_id", {}).items()}
            self.by_ingredient = {str(k): v for k, v in data.get("by_ingredient", {}).items()}

        # Cross-populate seed_to_item and item_to_seed from by_seed_id
        for sid_str, iid in self.by_seed_id.items():
            sid = int(sid_str)
            self.seed_to_item[sid] = iid
            self.item_to_seed[iid] = sid

    def resolve_target(self, query: str) -> Optional[Tuple[int, int, str]]:
        """
        Resolves query (ID or Name) to (item_id, seed_id, item_name).
        Returns None if not found.
        """
        if query is None:
            return None
        q = str(query).strip()
        if not q or q.lower() == "none":
            return None

        # Check numeric ID
        if q.isdigit():
            target_id = int(q)
            # If target_id is a seed
            if target_id in self.seed_to_item:
                seed_id = target_id
                item_id = self.seed_to_item[seed_id]
                item_name = self.items_db.get(str(item_id), f"Item {item_id}")
                return item_id, seed_id, item_name
            # If target_id is an item
            if str(target_id) in self.items_db:
                item_id = target_id
                seed_id = self.item_to_seed.get(item_id, item_id + 1)
                item_name = self.items_db[str(item_id)]
                return item_id, seed_id, item_name
            if str(target_id) in self.items_info:
                info = self.items_info[str(target_id)]
                return info["item_id"], info["seed_id"], info["name"]
            # Fallback assumption
            return target_id, target_id + 1, f"Item {target_id}"

        q_lower = q.lower()

        # Exact match in recipes/items_info
        for iid_str, info in self.items_info.items():
            if info["name"].lower() == q_lower:
                return info["item_id"], info["seed_id"], info["name"]
            if info["seed_name"].lower() == q_lower:
                return info["item_id"], info["seed_id"], info["name"]

        # Exact match in items_db
        for iid_str, name in self.items_db.items():
            clean = re.sub(r"\s+", " ", name).strip()
            if clean.lower() == q_lower:
                iid = int(iid_str)
                if clean.endswith(" Seed"):
                    base_id = self.seed_to_item.get(iid, iid - 1)
                    base_name = self.items_db.get(str(base_id), clean[:-5].strip())
                    return base_id, iid, base_name
                seed_id = self.item_to_seed.get(iid, iid + 1)
                return iid, seed_id, clean

        # Substring search in recipes
        for iid_str, info in self.items_info.items():
            if q_lower in info["name"].lower():
                return info["item_id"], info["seed_id"], info["name"]

        # Substring search in items_db (prefer non-seed)
        for iid_str, name in self.items_db.items():
            clean = re.sub(r"\s+", " ", name).strip()
            if q_lower in clean.lower() and not clean.endswith(" Seed"):
                iid = int(iid_str)
                seed_id = self.item_to_seed.get(iid, iid + 1)
                return iid, seed_id, clean

        return None

    def trace_dag(
        self,
        target_query: str,
        capacity: int = 1,
        user_stock: Optional[Dict[int, int]] = None,
        prune_with_stock: bool = True
    ) -> Dict[str, Any]:
        """
        Executes recursive backtracking DFS + 2-pass MRP seed requirements calculation.
        Marks critical path with neon emerald green (#10B981) and alternative paths with dark slate (#334155).
        """
        if not target_query or not str(target_query).strip():
            return {"error": "Target item or seed query cannot be empty."}

        res = self.resolve_target(target_query)
        if not res:
            return {
                "error": f"Item or seed '{target_query}' could not be resolved in Growtopia database."
            }

        target_item_id, target_seed_id, target_name = res

        try:
            if capacity is None:
                capacity = 1
            elif isinstance(capacity, str):
                capacity = int(float(capacity.strip())) if "." in capacity else int(capacity.strip())
            else:
                capacity = int(capacity)
            capacity = max(1, capacity)
        except (ValueError, TypeError, OverflowError):
            capacity = 1

        sanitized_stock: Dict[int, int] = {}
        if isinstance(user_stock, str):
            try:
                s_clean = user_stock.strip()
                if s_clean.startswith("{"):
                    user_stock = json.loads(s_clean)
                elif ":" in s_clean:
                    parsed_csv = {}
                    for part in s_clean.split(","):
                        if ":" in part:
                            k, v = part.strip().split(":", 1)
                            r = self.resolve_target(k.strip())
                            if r:
                                parsed_csv[r[1]] = int(v.strip())
                    user_stock = parsed_csv
            except Exception:
                user_stock = {}

        if isinstance(user_stock, dict):
            for k, v in user_stock.items():
                try:
                    sid = None
                    if isinstance(k, int):
                        sid = k
                    elif isinstance(k, str) and k.strip().isdigit():
                        sid = int(k.strip())
                    elif isinstance(k, str):
                        r = self.resolve_target(k.strip())
                        if r:
                            sid = r[1]
                    if sid is not None:
                        sanitized_stock[sid] = max(0, int(v))
                except (ValueError, TypeError):
                    continue
        user_stock = sanitized_stock

        if isinstance(prune_with_stock, str):
            prune_with_stock = prune_with_stock.strip().lower() not in ("false", "0", "no", "f", "off", "none")
        else:
            prune_with_stock = bool(prune_with_stock)

        # Check if item exists in our recipe dataset
        is_in_recipes = str(target_item_id) in self.items_info or str(target_item_id) in self.recipes_db
        is_known_base = target_seed_id in BASE_SEEDS or target_item_id in BASE_ITEMS

        # ---------------------------------------------------------
        # PASS 1: Recursive Backtracking DFS & Topological Order
        # ---------------------------------------------------------
        nodes: Dict[int, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        active_nodes: Set[int] = set()
        active_edges: Set[str] = set()
        adj: Dict[int, Tuple[int, int]] = {}
        visiting_ancestors: Set[int] = set()
        visited: Set[int] = set()
        topo_order: List[int] = []

        def get_node_metadata(seed_id: int) -> Dict[str, Any]:
            item_id = self.seed_to_item.get(seed_id, seed_id - 1)
            is_base = (seed_id in BASE_SEEDS) or (item_id in BASE_ITEMS)
            item_name = self.items_db.get(str(item_id), f"Item {item_id}")
            seed_name = self.items_db.get(str(seed_id), f"{item_name} Seed")

            # Check items_info
            info = self.items_info.get(str(item_id), {})
            if info:
                item_name = info.get("name", item_name)
                seed_name = info.get("seed_name", seed_name)
                growth = info.get("growth_seconds", 0)
                rarity = info.get("rarity", 1)
                tier = info.get("tier", 1 if is_base else 2)
                max_fruit = info.get("max_fruit_drop", 4)
                colors = info.get("colors", {"base": "FFFFFF", "overlay": "FFFFFF"})
                is_splicable = (info.get("recipe", {}).get("type") == "SPLICE")
            else:
                growth = 31 if is_base else 0
                rarity = 1
                tier = 1 if is_base else 2
                max_fruit = 8 if is_base else 4
                colors = {"base": "808080", "overlay": "C8C8C8"}
                is_splicable = not is_base and (str(item_id) in self.recipes_db)

            return {
                "id": f"node_{seed_id}",
                "item_id": item_id,
                "item_name": item_name,
                "seed_id": seed_id,
                "seed_name": seed_name,
                "tier": tier,
                "rarity": rarity,
                "growth_time_seconds": growth,
                "growth_time_formatted": format_duration(growth),
                "max_fruit_drop": max_fruit,
                "is_base": is_base,
                "is_splicable": is_splicable,
                "colors": colors,
                "textures": {
                    "atlas": "tiles_page1.rttex",
                    "sprite_url": f"/sprite/{item_id}.png"
                },
                "demand": {
                    "gross_required": 0,
                    "user_stock": user_stock.get(seed_id, 0),
                    "net_deficit": 0,
                    "is_satisfied_by_stock": False
                }
            }

        def dfs(seed_id: int) -> bool:
            if seed_id in visiting_ancestors:
                return False  # Cycle safeguard
            if seed_id in visited:
                return True
            visiting_ancestors.add(seed_id)

            if seed_id not in nodes:
                nodes[seed_id] = get_node_metadata(seed_id)

            active_nodes.add(seed_id)

            item_id = nodes[seed_id]["item_id"]
            if nodes[seed_id]["is_base"]:
                visited.add(seed_id)
                topo_order.append(seed_id)
                visiting_ancestors.remove(seed_id)
                return True

            recipe_candidates = self.recipes_db.get(str(item_id), [])
            if not recipe_candidates:
                # Terminal leaf
                nodes[seed_id]["is_base"] = True
                nodes[seed_id]["tier"] = 1
                visited.add(seed_id)
                topo_order.append(seed_id)
                visiting_ancestors.remove(seed_id)
                return True

            # Heuristic selection for best candidate recipe
            best_recipe = None
            best_score = float("inf")
            for r in recipe_candidates:
                score = r.get("growth_time_seconds", 0)
                ing1 = r["ingredient_1"]["id"]
                ing2 = r["ingredient_2"]["id"]
                if user_stock.get(ing1, 0) > 0:
                    score -= 5000
                if user_stock.get(ing2, 0) > 0:
                    score -= 5000
                if score < best_score:
                    best_score = score
                    best_recipe = r

            if best_recipe is None:
                best_recipe = recipe_candidates[0]

            for r in recipe_candidates:
                is_selected = (r == best_recipe)
                ing1 = r["ingredient_1"]["id"]
                ing2 = r["ingredient_2"]["id"]
                r_id = r.get("id", f"r_{item_id}")

                e1_id = f"edge_{seed_id}_{ing1}_{r_id}_primary"
                e2_id = f"edge_{seed_id}_{ing2}_{r_id}_secondary"

                edges.append({
                    "id": e1_id,
                    "source": f"node_{seed_id}",
                    "target": f"node_{ing1}",
                    "recipe_id": r_id,
                    "ingredient_role": "primary",
                    "ratio": 1.0,
                    "is_active": is_selected
                })
                edges.append({
                    "id": e2_id,
                    "source": f"node_{seed_id}",
                    "target": f"node_{ing2}",
                    "recipe_id": r_id,
                    "ingredient_role": "secondary",
                    "ratio": 1.0,
                    "is_active": is_selected
                })

                if is_selected:
                    active_edges.add(e1_id)
                    active_edges.add(e2_id)
                    adj[seed_id] = (ing1, ing2)
                    dfs(ing1)
                    dfs(ing2)

            visited.add(seed_id)
            topo_order.append(seed_id)
            visiting_ancestors.remove(seed_id)
            return True

        dfs(target_seed_id)

        # ---------------------------------------------------------
        # PASS 2: Top-Down Net Deficit Propagation (MRP)
        # ---------------------------------------------------------
        # Reverse topological order goes from root down to base leaves
        top_down = list(reversed(topo_order))
        gross_demand: Dict[int, int] = defaultdict(int)
        net_deficit: Dict[int, int] = defaultdict(int)

        gross_demand[target_seed_id] = capacity
        root_stock = user_stock.get(target_seed_id, 0)
        net_deficit[target_seed_id] = max(0, capacity - root_stock)

        for s_id in top_down:
            craft_needed = net_deficit[s_id] if prune_with_stock else gross_demand[s_id]
            if s_id in adj and craft_needed > 0:
                child1, child2 = adj[s_id]
                gross_demand[child1] += craft_needed
                gross_demand[child2] += craft_needed
                for c in (child1, child2):
                    c_stock = user_stock.get(c, 0)
                    net_deficit[c] = max(0, gross_demand[c] - c_stock)

        # Update node demand objects
        for s_id, n in nodes.items():
            n["demand"]["gross_required"] = gross_demand[s_id]
            n["demand"]["net_deficit"] = net_deficit[s_id]
            n["demand"]["user_stock"] = user_stock.get(s_id, 0)
            n["demand"]["is_satisfied_by_stock"] = (
                gross_demand[s_id] > 0 and net_deficit[s_id] == 0
            )

        # Compute tier numbers bottom-up
        for s_id in topo_order:
            if s_id in adj:
                c1, c2 = adj[s_id]
                nodes[s_id]["tier"] = 1 + max(nodes[c1]["tier"], nodes[c2]["tier"])

        # ---------------------------------------------------------
        # Styling & Active Path Flagging
        # Emerald Green (#10B981) vs Dark Slate (#334155)
        # ---------------------------------------------------------
        for s_id, n in nodes.items():
            is_act = s_id in active_nodes
            n["visual"] = {
                "is_active": is_act,
                "status": "critical_path" if is_act else "alternative",
                "color": "#10B981" if is_act else "#334155",
                "stroke_width": 3.5 if is_act else 1.0,
                "glow": is_act,
                "opacity": 1.0 if is_act else 0.4
            }

        for e in edges:
            is_act = e["id"] in active_edges
            e["visual"] = {
                "is_active": is_act,
                "stroke": "#10B981" if is_act else "#334155",
                "stroke_width": 3.5 if is_act else 1.0,
                "stroke_dasharray": "8, 4" if is_act else "none",
                "animated_pulse": is_act,
                "glow": is_act,
                "opacity": 1.0 if is_act else 0.4
            }

        # ---------------------------------------------------------
        # Bill of Materials & Execution Roadmap
        # ---------------------------------------------------------
        base_bom = {}
        for s_id, n in nodes.items():
            if n["is_base"] and gross_demand[s_id] > 0:
                base_bom[f"{n['seed_name']} ({s_id})"] = {
                    "seed_id": s_id,
                    "seed_name": n["seed_name"],
                    "gross_needed": gross_demand[s_id],
                    "in_stock": user_stock.get(s_id, 0),
                    "fetch_required": net_deficit[s_id]
                }

        stages = defaultdict(list)
        flat_operations = []
        op_step_num = 1
        first_active_step = None

        for s_id in topo_order:
            if not nodes[s_id]["is_base"] and s_id in adj:
                t = nodes[s_id]["tier"]
                c1, c2 = adj[s_id]
                craft_needed = net_deficit[s_id] if prune_with_stock else gross_demand[s_id]
                stock_avail = user_stock.get(s_id, 0)
                # An operation is skipped if user has enough stock or its demand was pruned
                is_skipped = (craft_needed == 0 and stock_avail >= gross_demand[s_id]) or (gross_demand[s_id] == 0)

                op_entry = {
                    "step_number": op_step_num,
                    "target_seed": nodes[s_id]["seed_name"],
                    "target_seed_id": s_id,
                    "target_item_id": nodes[s_id]["item_id"],
                    "gross_demand": gross_demand[s_id],
                    "in_stock": stock_avail,
                    "quantity_to_splice": craft_needed,
                    "base_seed_a": nodes[c1]["seed_name"],
                    "base_seed_a_id": c1,
                    "secondary_seed_b": nodes[c2]["seed_name"],
                    "secondary_seed_b_id": c2,
                    "growth_time_seconds": nodes[s_id]["growth_time_seconds"],
                    "growth_time_formatted": nodes[s_id]["growth_time_formatted"],
                    "is_satisfied_by_stock": is_skipped,
                    "status": "SKIPPED_IN_STOCK" if is_skipped else "ACTIVE_CRAFT",
                    "status_label": f"✅ Stokta Var (x{stock_avail}) — Atlandı" if is_skipped else f"⚡ Üretilecek (x{craft_needed})"
                }

                if not is_skipped and first_active_step is None:
                    first_active_step = op_step_num
                    op_entry["is_first_active_step"] = True
                else:
                    op_entry["is_first_active_step"] = False

                stages[t].append(op_entry)
                flat_operations.append(op_entry)
                op_step_num += 1

        execution_roadmap = [
            {
                "tier": t,
                "phase_name": f"Tier {t} Splicing Phase",
                "operations": ops
            }
            for t, ops in sorted(stages.items())
        ]

        target_node = nodes[target_seed_id]
        skipped_count = sum(1 for op in flat_operations if op["is_satisfied_by_stock"])

        return {
            "target": {
                "item_id": target_item_id,
                "item_name": target_name,
                "seed_id": target_seed_id,
                "seed_name": target_node["seed_name"],
                "capacity_requested": capacity,
                "tier": target_node["tier"],
                "growth_time_seconds": target_node["growth_time_seconds"],
                "growth_time_formatted": target_node["growth_time_formatted"],
                "max_fruit_drop": target_node["max_fruit_drop"]
            },
            "summary": {
                "total_unique_seeds": len(nodes),
                "tier_depth": target_node["tier"],
                "base_seeds_bill_of_materials": base_bom,
                "execution_stages_count": len(execution_roadmap),
                "total_operations_count": len(flat_operations),
                "skipped_operations_count": skipped_count,
                "first_active_step": first_active_step or 1,
                "first_active_target": flat_operations[first_active_step - 1]["target_seed"] if (first_active_step and first_active_step <= len(flat_operations)) else target_node["seed_name"]
            },
            "execution_roadmap": execution_roadmap,
            "flat_operations": flat_operations,
            "dag": {
                "nodes": list(nodes.values()),
                "edges": edges
            }
        }

    def search_recipes(
        self,
        query: str,
        filter_by: str = "target",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Searches recipes by target, ingredient, or tier.
        """
        q = str(query or "").strip().lower()
        try:
            limit = max(1, min(500, int(limit)))
        except (ValueError, TypeError):
            limit = 20

        filter_by = str(filter_by or "target").strip().lower()
        if filter_by not in ("target", "ingredient", "tier"):
            filter_by = "target"
        results = []

        if filter_by == "tier" and q.isdigit():
            tier_req = int(q)
            for iid_str, info in self.items_info.items():
                if info.get("tier") == tier_req:
                    results.append(self._format_recipe_result(int(iid_str)))
                    if len(results) >= limit:
                        break
            return results

        if filter_by == "ingredient":
            # Search recipes where ingredient matches
            matched_targets = set()
            # If q is numeric seed ID
            if q.isdigit():
                sid_str = q
                if sid_str in self.by_ingredient:
                    matched_targets.update(self.by_ingredient[sid_str])
            else:
                for sid_str, iid_list in self.by_ingredient.items():
                    s_name = self.items_db.get(sid_str, "").lower()
                    if q in s_name:
                        matched_targets.update(iid_list)

            for t_id in sorted(list(matched_targets))[:limit]:
                results.append(self._format_recipe_result(t_id))
            return results

        # Default filter_by == "target"
        # 1. Exact numeric ID
        if q.isdigit():
            target_id = int(q)
            if str(target_id) in self.items_info:
                results.append(self._format_recipe_result(target_id))
            elif target_id in self.seed_to_item and str(self.seed_to_item[target_id]) in self.items_info:
                results.append(self._format_recipe_result(self.seed_to_item[target_id]))

        # 2. Name matches
        for iid_str, info in self.items_info.items():
            iid = int(iid_str)
            if any(r["item_id"] == iid for r in results):
                continue
            if q in info["name"].lower() or q in info["seed_name"].lower():
                results.append(self._format_recipe_result(iid))
                if len(results) >= limit:
                    break

        return results

    def _format_recipe_result(self, item_id: int) -> Dict[str, Any]:
        info = self.items_info.get(str(item_id), {})
        rec_list = self.recipes_db.get(str(item_id), [])
        primary = rec_list[0] if rec_list else {}
        ing1 = primary.get("ingredient_1", {})
        ing2 = primary.get("ingredient_2", {})
        return {
            "item_id": item_id,
            "name": info.get("name", self.items_db.get(str(item_id), f"Item {item_id}")),
            "seed_id": info.get("seed_id", self.item_to_seed.get(item_id, item_id + 1)),
            "seed_name": info.get("seed_name", f"{info.get('name', '')} Seed"),
            "tier": info.get("tier", 1),
            "rarity": info.get("rarity", 1),
            "growth_seconds": info.get("growth_seconds", 0),
            "growth_formatted": info.get("growth_formatted", "Instant"),
            "max_fruit_drop": info.get("max_fruit_drop", 4),
            "ingredient_1": ing1,
            "ingredient_2": ing2,
            "is_multi_output": primary.get("is_multi_output", False)
        }

    def generate_tree(
        self,
        target: str,
        output_format: str = "nested",
        max_depth: int = 10,
        memoize_subtrees: bool = True
    ) -> Any:
        """
        Generates hierarchy tree in format:
        - 'nested': Recursive JSON tree structure with cycle protection and subtree memoization.
        - 'flat': Deduplicated DAG with unique nodes and edges arrays.
        - 'imgui_lua': Ready-to-execute, crash-safe Lua code for single-threaded ImGui.TreeNode rendering.
        """
        if not target or not str(target).strip():
            err = {"error": "Target item or seed must be specified."}
            return f"-- Error generating Mass Tree: {err['error']}" if output_format == "imgui_lua" else err

        # Sanitize output_format
        output_format = str(output_format or "nested").strip().lower()
        if output_format not in ("nested", "flat", "imgui_lua"):
            output_format = "nested"

        # Sanitize max_depth: clamp between 1 and 50
        try:
            max_depth = max(1, min(50, int(max_depth)))
        except (ValueError, TypeError):
            max_depth = 10

        trace = self.trace_dag(target_query=target, capacity=1)
        if "error" in trace:
            if output_format == "imgui_lua":
                return f"-- Error generating Mass Tree: {trace['error']}"
            return trace

        if output_format == "flat":
            seen_edges: Set[Tuple[Any, Any, Any, Any]] = set()
            clean_edges: List[Dict[str, Any]] = []
            for e in trace.get("dag", {}).get("edges", []):
                edge_key = (
                    e.get("source"),
                    e.get("target"),
                    e.get("recipe_id"),
                    e.get("ingredient_role")
                )
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    clean_edges.append(e)

            seen_nodes: Set[Any] = set()
            clean_nodes: List[Dict[str, Any]] = []
            for n in trace.get("dag", {}).get("nodes", []):
                n_id = n.get("seed_id") or n.get("id")
                if n_id not in seen_nodes:
                    seen_nodes.add(n_id)
                    clean_nodes.append(n)

            return {
                "nodes": clean_nodes,
                "edges": clean_edges,
                "stats": {
                    "total_nodes": len(clean_nodes),
                    "active_nodes": sum(1 for n in clean_nodes if n.get("is_active", True)),
                    "total_edges": len(clean_edges),
                    "active_edges": sum(1 for e in clean_edges if e.get("is_active")),
                    "max_tier": max((n.get("tier", 1) for n in clean_nodes), default=1)
                }
            }

        target_info = trace["target"]
        root_seed_id = target_info["seed_id"]
        dag_nodes = {n["seed_id"]: n for n in trace["dag"]["nodes"]}

        # Deduplicated adjacency mapping: enforce strict binary degree (<= 2) and unique children
        adj: Dict[int, List[int]] = {}
        for e in trace.get("dag", {}).get("edges", []):
            if e.get("is_active"):
                try:
                    src_id = int(str(e["source"]).replace("node_", ""))
                    tgt_id = int(str(e["target"]).replace("node_", ""))
                except (ValueError, KeyError):
                    continue
                ch_list = adj.setdefault(src_id, [])
                if tgt_id not in ch_list and len(ch_list) < 2:
                    ch_list.append(tgt_id)

        if output_format == "nested":
            visited_subtrees: Set[int] = set()
            active_recursion: Set[int] = set()

            def build_nested(seed_id: int, depth: int) -> Dict[str, Any]:
                node = dag_nodes.get(seed_id, {})
                is_base = node.get("is_base", False)
                children_ids = adj.get(seed_id, [])

                # Cycle safeguard
                if seed_id in active_recursion:
                    return {
                        "id": seed_id,
                        "item_id": node.get("item_id"),
                        "name": node.get("item_name"),
                        "seed_name": node.get("seed_name"),
                        "tier": node.get("tier", 1),
                        "cycle_detected": True,
                        "children": []
                    }

                # Subtree memoization: prevent multi-megabyte JSON bloat on diamond DAGs
                if memoize_subtrees and seed_id in visited_subtrees:
                    return {
                        "id": seed_id,
                        "item_id": node.get("item_id"),
                        "name": node.get("item_name"),
                        "seed_name": node.get("seed_name"),
                        "tier": node.get("tier", 1),
                        "growth_seconds": node.get("growth_time_seconds", 0),
                        "growth_formatted": node.get("growth_time_formatted", "Instant"),
                        "is_base": is_base,
                        "expanded_elsewhere": True,
                        "children": []
                    }

                visited_subtrees.add(seed_id)
                active_recursion.add(seed_id)

                children = []
                if depth < max_depth and not is_base and seed_id in adj:
                    for ch_id in children_ids:
                        children.append(build_nested(ch_id, depth + 1))

                active_recursion.remove(seed_id)

                return {
                    "id": seed_id,
                    "item_id": node.get("item_id"),
                    "name": node.get("item_name"),
                    "seed_name": node.get("seed_name"),
                    "tier": node.get("tier", 1),
                    "growth_seconds": node.get("growth_time_seconds", 0),
                    "growth_formatted": node.get("growth_time_formatted", "Instant"),
                    "is_base": is_base,
                    "children": children
                }

            return build_nested(root_seed_id, 0)

        if output_format == "imgui_lua":
            lines = [
                "-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp",
                f"-- Mass Tree View: {target_info['seed_name']} ({root_seed_id}) - Tier {target_info['tier']}",
            ]
            visited_subtrees: Set[int] = set()
            active_recursion: Set[int] = set()

            def build_lua(seed_id: int, indent_level: int, depth: int):
                node = dag_nodes.get(seed_id, {})
                pad = "    " * indent_level
                name = node.get("seed_name", f"Seed {seed_id}")
                tier = node.get("tier", 1)
                is_base = node.get("is_base", False)
                children = adj.get(seed_id, [])

                # Cycle safeguard
                if seed_id in active_recursion:
                    lines.append(f'{pad}ImGui.BulletText("{name} ({seed_id}) [Tier {tier}] (Cycle Detected)")')
                    return

                if is_base:
                    lines.append(f'{pad}ImGui.BulletText("{name} ({seed_id}) [Tier {tier}] (Base)")')
                elif not children:
                    lines.append(f'{pad}ImGui.BulletText("{name} ({seed_id}) [Tier {tier}] (Leaf)")')
                elif depth >= max_depth:
                    lines.append(f'{pad}ImGui.BulletText("{name} ({seed_id}) [Tier {tier}] (Depth limit reached)")')
                elif memoize_subtrees and seed_id in visited_subtrees:
                    lines.append(f'{pad}ImGui.BulletText("{name} ({seed_id}) [Tier {tier}] (Subtree expanded above)")')
                else:
                    visited_subtrees.add(seed_id)
                    active_recursion.add(seed_id)
                    lines.append(f'{pad}if ImGui.TreeNode("{name} ({seed_id}) - Tier {tier}") then')
                    growth = node.get("growth_time_formatted", "Instant")
                    fruit = node.get("max_fruit_drop", 4)
                    lines.append(f'{pad}    ImGui.TextUnformatted("Grow Time: {growth} | Fruit: {fruit}")')
                    for ch in children:
                        build_lua(ch, indent_level + 1, depth + 1)
                    lines.append(f'{pad}    ImGui.TreePop()')
                    lines.append(f'{pad}end')
                    active_recursion.remove(seed_id)

            lines.append(f'if ImGui.TreeNode("{target_info["seed_name"]} ({root_seed_id}) - Tier {target_info["tier"]}") then')
            lines.append(f'    ImGui.TextUnformatted("Grow Time: {target_info["growth_time_formatted"]} | Fruit: {target_info["max_fruit_drop"]}")')
            for ch in adj.get(root_seed_id, []):
                build_lua(ch, 1, 1)
            lines.append('    ImGui.Separator()')
            lines.append('    ImGui.TextUnformatted("By BrK | Discord : mr_berk.")')
            lines.append('    ImGui.TreePop()')
            lines.append('end')

            return "\n".join(lines)

        return trace


# Global singleton instance
tracer = MassTreeTracer()
