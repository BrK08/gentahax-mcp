"""
GENTAHAX MCP — Multi-World Logistics & Capacity Balancing Engine
mr_berk edition

Provides:
- Target farm capacity scanning (`scan_farm_capacity`) respecting AGENTS.md Rule 8
  (`only_above_block` filter: tile fg==0 and below tile fg!=0 with isCollideable==True).
- Exact seed count calculation and multi-tier balancing (`calculate_seed_quotas`)
  integrated with `mass_tracer.py`.
- Multi-world storage retrieval planning (`plan_storage_retrieval`) with partial
  collection and fallback world routing.
- Immediate surplus pruning calculations (`calculate_surplus_pruning`) when a stack
  overshoots quota.
- Sequential multi-farm coordination (`plan_multi_farm_sequence`) ensuring Farm 1
  is completely planted and spliced before moving to Farm 2.
- Anti-ban rate limiting and humanized timing parameters.
- Single-threaded OnRender ASCII-compliant Lua code generators.
"""

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

try:
    import mass_tracer as MT
    _tracer = MT.tracer
    BASE_SEEDS = MT.BASE_SEEDS
    BASE_ITEMS = MT.BASE_ITEMS
except ImportError:
    from . import mass_tracer as MT
    _tracer = MT.tracer
    BASE_SEEDS = MT.BASE_SEEDS
    BASE_ITEMS = MT.BASE_ITEMS

WATERMARK = "mr_berk"
REPO_URL = "https://github.com/BrK08/gentahax-mcp"

# Safe Anti-Ban & Timing Constants (PROJECT.md Section 8)
SAFE_PACKET_RATE_LIMIT = 3.5        # Max packets per second (token bucket)
MIN_INTER_PACKET_DELAY_MS = 220    # Minimum inter-packet delay in ms
PLACEMENT_BASE_DELAY_MS = 260       # Humanized placement delay in ms
PLACEMENT_JITTER_MS = 50           # Gaussian jitter delta (+-50ms)
WORLD_STABILIZATION_DELAY_S = 2.8   # Wait time upon entering new world
WORLD_HOP_COOLDOWN_S = 3.5         # Minimum cooldown between world warps
SAME_WORLD_REJOIN_COOLDOWN_S = 10.0# Cooldown for re-joining identical world
SAFE_DROP_TILE_THRESHOLD = 5000     # Safe cap per tile (below GT hard ceiling 5500)
GT_HARD_DROP_CEILING = 5500        # Server ceiling


# ===========================================================================
# 1. TARGET FARM CAPACITY SCANNING (AGENTS.md Rule 8)
# ===========================================================================

def scan_farm_capacity(
    tiles_or_world: Any,
    only_above_block: bool = True,
    x_range: Tuple[int, int] = (1, 98),
    y_range: Tuple[int, int] = (1, 57)
) -> Dict[str, Any]:
    """
    Scans world grid (1..57, 1..98) to determine exact plantable capacity C_target.

    Satisfies AGENTS.md Rule 8:
    - If only_above_block=True:
        Candidate tile (x, y) must have fg == 0 AND below tile (x, y + 1) must have
        fg != 0 and isCollideable == True (solid walkable block, e.g. Dirt, Rock, Platform).
    - If only_above_block=False:
        Candidate tile (x, y) must have fg == 0 (all empty air spaces including floating).

    Candidate tiles are sorted in snake/boustrophedon sweep (even rows L->R, odd rows R->L)
    to optimize avatar pathfinding movement.

    Args:
        tiles_or_world: World grid representation:
                        - Dict with 'tiles' list/dict
                        - Dict mapping (x, y) -> tile
                        - 2D array/grid of tiles
                        - Object with check_tile(x, y) or checkTile(x, y) method
                        - Callable fn(x, y) returning tile
                        - None / empty
        only_above_block: Boolean soil geometry filter (AGENTS.md Rule 8).
        x_range: Scan horizontal range inclusive (default: 1..98).
        y_range: Scan vertical range inclusive (default: 1..57).

    Returns:
        Dict with 'plantable_count', 'capacity', 'valid_tiles', 'only_above_block',
        'x_range', 'y_range', 'total_scanned_tiles', and metadata.
    """
    x_min, x_max = min(x_range), max(x_range)
    y_min, y_max = min(y_range), max(y_range)
    total_scanned = (x_max - x_min + 1) * (y_max - y_min + 1)

    if tiles_or_world is None:
        return {
            "plantable_count": 0,
            "capacity": 0,
            "valid_tiles": [],
            "only_above_block": bool(only_above_block),
            "x_range": [x_min, x_max],
            "y_range": [y_min, y_max],
            "total_scanned_tiles": 0,
            "rule_8_enforced": bool(only_above_block)
        }

    # If an existing capacity scan result is passed directly
    if isinstance(tiles_or_world, dict) and "plantable_count" in tiles_or_world and "valid_tiles" in tiles_or_world:
        res = dict(tiles_or_world)
        res["capacity"] = res["plantable_count"]
        return res

    # Resolve tile extractor function
    get_tile_fn = _build_tile_accessor(tiles_or_world)

    valid_tiles_by_row: Dict[int, List[Dict[str, int]]] = defaultdict(list)
    plantable_count = 0

    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            tile = get_tile_fn(x, y)
            if tile is None:
                continue

            fg = _get_tile_fg(tile)
            if fg != 0:
                continue  # Tile already occupied

            if only_above_block:
                below = get_tile_fn(x, y + 1)
                if below is None:
                    continue
                below_fg = _get_tile_fg(below)
                if below_fg == 0:
                    continue  # Air below
                below_col = _get_tile_collideable(below)
                if not below_col:
                    continue  # Non-solid block below (e.g. non-collideable decoration)
                
                plantable_count += 1
                valid_tiles_by_row[y].append({"x": x, "y": y})
            else:
                plantable_count += 1
                valid_tiles_by_row[y].append({"x": x, "y": y})

    # Snake / Boustrophedon ordering: even rows L->R, odd rows R->L
    ordered_valid_tiles: List[Dict[str, int]] = []
    for y in sorted(valid_tiles_by_row.keys()):
        row_tiles = valid_tiles_by_row[y]
        if y % 2 == 0:
            row_tiles.sort(key=lambda t: t["x"])
        else:
            row_tiles.sort(key=lambda t: t["x"], reverse=True)
        ordered_valid_tiles.extend(row_tiles)

    return {
        "plantable_count": plantable_count,
        "capacity": plantable_count,
        "valid_tiles": ordered_valid_tiles,
        "only_above_block": bool(only_above_block),
        "x_range": [x_min, x_max],
        "y_range": [y_min, y_max],
        "total_scanned_tiles": total_scanned,
        "rule_8_enforced": bool(only_above_block)
    }


def _build_tile_accessor(tiles_or_world: Any) -> Callable[[int, int], Any]:
    """Constructs an O(1) tile coordinate lookup function for any data layout."""
    if callable(tiles_or_world):
        return tiles_or_world

    if hasattr(tiles_or_world, "check_tile"):
        return getattr(tiles_or_world, "check_tile")
    if hasattr(tiles_or_world, "checkTile"):
        return getattr(tiles_or_world, "checkTile")
    if hasattr(tiles_or_world, "get_tile"):
        return getattr(tiles_or_world, "get_tile")
    if hasattr(tiles_or_world, "getTile"):
        return getattr(tiles_or_world, "getTile")

    container = tiles_or_world
    if isinstance(tiles_or_world, dict) and "tiles" in tiles_or_world:
        container = tiles_or_world["tiles"]

    # If mapping (x, y) -> tile
    if isinstance(container, dict):
        # Check if keys are tuples or string "x,y"
        first_key = next(iter(container.keys())) if container else None
        if isinstance(first_key, tuple):
            return lambda x, y: container.get((x, y))
        if isinstance(first_key, str) and "," in first_key:
            return lambda x, y: container.get(f"{x},{y}")
        return lambda x, y: container.get((x, y)) or container.get(f"{x},{y}")

    # If list of tiles
    if isinstance(container, (list, tuple)):
        # Check if 2D grid: list of rows
        if container and isinstance(container[0], (list, tuple)):
            num_rows = len(container)
            num_cols = len(container[0])
            if num_rows == 60 and num_cols == 100:
                return lambda x, y: container[y][x] if 0 <= y < 60 and 0 <= x < 100 else None
            elif num_rows == 100 and num_cols == 60:
                return lambda x, y: container[x][y] if 0 <= x < 100 and 0 <= y < 60 else None
            else:
                return lambda x, y: container[y][x] if 0 <= y < num_rows and 0 <= x < num_cols else None

        # Flat list of tile objects / dicts: build O(1) index map
        index_map: Dict[Tuple[int, int], Any] = {}
        for item in container:
            if not item:
                continue
            x, y = None, None
            if isinstance(item, dict):
                if "pos" in item and isinstance(item["pos"], dict):
                    x = item["pos"].get("x")
                    y = item["pos"].get("y")
                elif "x" in item and "y" in item:
                    x = item.get("x")
                    y = item.get("y")
            else:
                pos = getattr(item, "pos", None)
                if pos is not None:
                    x = getattr(pos, "x", None)
                    y = getattr(pos, "y", None)
                else:
                    x = getattr(item, "x", None)
                    y = getattr(item, "y", None)
            if x is not None and y is not None:
                index_map[(int(x), int(y))] = item

        return lambda x, y: index_map.get((x, y))

    return lambda x, y: None


def _get_tile_fg(tile: Any) -> int:
    """Extracts foreground item ID from tile."""
    if isinstance(tile, dict):
        return int(tile.get("fg", 0))
    return int(getattr(tile, "fg", 0))


def _get_tile_collideable(tile: Any) -> bool:
    """Extracts collideable flag from tile, defaulting to solid if fg != 0."""
    if isinstance(tile, dict):
        val = tile.get("isCollideable")
        if val is None:
            val = tile.get("is_collideable")
        if val is None:
            fg = int(tile.get("fg", 0))
            return fg != 0
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes")
        return bool(val)

    val = getattr(tile, "isCollideable", None)
    if val is None:
        val = getattr(tile, "is_collideable", None)
    if val is None:
        fg = getattr(tile, "fg", 0)
        return fg != 0
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


# ===========================================================================
# 2. EXACT SEED COUNT CALCULATION & MULTI-TIER BALANCING
# ===========================================================================

def calculate_seed_quotas(
    target_item: str,
    capacity: int,
    user_stock: Optional[Union[Dict[int, int], str]] = None
) -> Dict[str, Any]:
    """
    Calculates exact seed quotas for plantable farm capacity C_target.
    Integrates directly with `mass_tracer.py`.

    Features:
    - Resolves target item/seed name or ID.
    - Determines direct splicing ingredients (Base Seed A and Secondary Seed B).
    - Computes net quotas for immediate splicing stage (e.g. Seed A=300, Seed B=300).
    - Generates multi-tier foundation Bill of Materials (BOM) for Tier 1 base seeds
      (Dirt Seed, Lava Seed, Rock Seed, Cave Background Seed) using 2-pass topological MRP.
    - Prunes quotas against available user stock.

    Args:
        target_item: Target item or seed name/ID (e.g. 'Rock', 'Wood Block', 'Chandelier', '340').
        capacity: Exact plantable capacity N (e.g. 300).
        user_stock: Optional stock dict or string of available seeds.

    Returns:
        Dict with target details, direct ingredients pair, seed quotas, base seeds BOM,
        and execution roadmap.
    """
    if not target_item or not str(target_item).strip():
        raise ValueError("target_item cannot be empty.")

    try:
        capacity_val = int(capacity)
        capacity_val = max(0, capacity_val)
    except (ValueError, TypeError):
        capacity_val = 0

    # Resolve target
    resolved = _tracer.resolve_target(str(target_item).strip())
    if not resolved:
        raise ValueError(f"Item or seed '{target_item}' could not be resolved in Growtopia database.")

    target_item_id, target_seed_id, target_name = resolved

    # Sanitize user stock
    sanitized_stock: Dict[int, int] = {}
    if isinstance(user_stock, str):
        try:
            s_clean = user_stock.strip()
            if s_clean.startswith("{"):
                raw_dict = json.loads(s_clean)
                for k, v in raw_dict.items():
                    r = _tracer.resolve_target(str(k))
                    sid = r[1] if r else (int(k) if str(k).isdigit() else None)
                    if sid is not None:
                        sanitized_stock[sid] = max(0, int(v))
            elif ":" in s_clean:
                for part in s_clean.split(","):
                    if ":" in part:
                        k, v = part.strip().split(":", 1)
                        r = _tracer.resolve_target(k.strip())
                        sid = r[1] if r else (int(k.strip()) if k.strip().isdigit() else None)
                        if sid is not None:
                            sanitized_stock[sid] = max(0, int(v.strip()))
        except Exception:
            sanitized_stock = {}
    elif isinstance(user_stock, dict):
        for k, v in user_stock.items():
            try:
                sid = None
                if isinstance(k, int):
                    sid = k
                elif isinstance(k, str) and k.strip().isdigit():
                    sid = int(k.strip())
                elif isinstance(k, str):
                    r = _tracer.resolve_target(k.strip())
                    if r:
                        sid = r[1]
                if sid is not None:
                    sanitized_stock[sid] = max(0, int(v))
            except (ValueError, TypeError):
                continue

    # Execute full DAG MRP calculation
    dag_trace = _tracer.trace_dag(
        target_query=str(target_item_id),
        capacity=max(1, capacity_val),
        user_stock=sanitized_stock,
        prune_with_stock=True
    )

    target_node = dag_trace.get("target", {})
    tier = target_node.get("tier", 1)
    growth_seconds = target_node.get("growth_time_seconds", 0)
    growth_formatted = target_node.get("growth_time_formatted", "Instant")
    target_seed_name = target_node.get("seed_name", f"{target_name} Seed")

    # Direct splicing recipe ingredients
    recipe_candidates = _tracer.recipes_db.get(str(target_item_id), [])
    is_base = (target_seed_id in BASE_SEEDS) or (target_item_id in BASE_ITEMS) or (not recipe_candidates)

    direct_ingredients: Optional[Dict[str, Any]] = None
    seed_quotas: Dict[int, int] = {}

    if not is_base and recipe_candidates:
        primary_recipe = recipe_candidates[0]
        ing1 = primary_recipe["ingredient_1"]
        ing2 = primary_recipe["ingredient_2"]

        seed_a_id = int(ing1["id"])
        seed_a_name = ing1["name"]
        seed_b_id = int(ing2["id"])
        seed_b_name = ing2["name"]

        stock_a = sanitized_stock.get(seed_a_id, 0)
        stock_b = sanitized_stock.get(seed_b_id, 0)
        net_a = max(0, capacity_val - stock_a)
        net_b = max(0, capacity_val - stock_b)

        direct_ingredients = {
            "seed_a": {
                "seed_id": seed_a_id,
                "seed_name": seed_a_name,
                "role": "base",
                "instruction": "Plant first on empty valid soil tiles",
                "gross_needed": capacity_val,
                "in_stock": stock_a,
                "needed_count": net_a,
                "is_satisfied": (net_a == 0)
            },
            "seed_b": {
                "seed_id": seed_b_id,
                "seed_name": seed_b_name,
                "role": "secondary",
                "instruction": "Splice second strictly onto verified Base Seed A saplings",
                "gross_needed": capacity_val,
                "in_stock": stock_b,
                "needed_count": net_b,
                "is_satisfied": (net_b == 0)
            }
        }
        seed_quotas = {
            seed_a_id: net_a,
            seed_b_id: net_b
        }
    else:
        # Base leaf
        stock_target = sanitized_stock.get(target_seed_id, 0)
        net_target = max(0, capacity_val - stock_target)
        seed_quotas = {
            target_seed_id: net_target
        }

    # Base bill of materials from DAG
    base_bom = dag_trace.get("summary", {}).get("base_seeds_bill_of_materials", {})
    if capacity_val == 0:
        zero_bom = {}
        for k, item in base_bom.items():
            ic = dict(item)
            ic["gross_needed"] = 0
            ic["fetch_required"] = 0
            zero_bom[k] = ic
        base_bom = zero_bom
    base_quotas = {
        item["seed_id"]: item["fetch_required"]
        for item in base_bom.values()
    }

    return {
        "target": {
            "item_id": target_item_id,
            "item_name": target_name,
            "seed_id": target_seed_id,
            "seed_name": target_seed_name,
            "tier": tier,
            "growth_time_seconds": growth_seconds,
            "growth_time_formatted": growth_formatted,
            "is_base": is_base
        },
        "capacity": capacity_val,
        "direct_ingredients": direct_ingredients,
        "seed_quotas": seed_quotas,
        "base_seeds_bom": base_bom,
        "base_quotas": base_quotas,
        "execution_roadmap": dag_trace.get("execution_roadmap", []),
        "total_unique_seeds": dag_trace.get("summary", {}).get("total_unique_seeds", 1),
        "user_stock_applied": sanitized_stock
    }


# ===========================================================================
# 3. MULTI-WORLD STORAGE RETRIEVAL PLANNING
# ===========================================================================

def plan_storage_retrieval(
    seed_id: Union[int, str],
    needed_count: int,
    storage_worlds: Any
) -> Dict[str, Any]:
    """
    Plans sequential retrieval of seeds across one or more storage worlds with
    deficit splitting and fallback routing.

    Example:
        Needed: 300 Dirt Seeds.
        Storage 1 has 180 -> Collect 180, remaining deficit: 120.
        Storage 2 has 200 -> Collect 120, remaining deficit: 0, surplus left: 80.

    Args:
        seed_id: Seed ID or name to retrieve.
        needed_count: Exact count required (C_target).
        storage_worlds: Can be:
                        - Comma-separated string: "STORE1:180, STORE2:300" or "STORE1, STORE2"
                        - List of world names: ["STORE1", "STORE2"]
                        - List of dicts: [{"world": "STORE1", "amount": 180}, ...]
                        - Dict: {"STORE1": 180, "STORE2": 300}

    Returns:
        Dict detailing step-by-step collection route, per-world amounts, and deficit status.
    """
    needed = max(0, int(needed_count))

    # Resolve seed name & ID
    res = _tracer.resolve_target(str(seed_id))
    if res:
        sid = res[1]
        s_name = res[2] if res[2].endswith(" Seed") else f"{res[2]} Seed"
    else:
        try:
            sid = int(seed_id)
            s_name = _tracer.items_db.get(str(sid), f"Seed {sid}")
        except (ValueError, TypeError):
            sid = 0
            s_name = str(seed_id)

    parsed_worlds = _parse_storage_worlds(storage_worlds)

    steps: List[Dict[str, Any]] = []
    remaining_needed = needed
    total_collected = 0

    for idx, (w_name, available) in enumerate(parsed_worlds, 1):
        if remaining_needed <= 0:
            break

        if available is None:
            # Dynamic world scan: bot will collect up to remaining_needed upon arrival
            to_collect = remaining_needed
            steps.append({
                "step_index": idx,
                "world": w_name,
                "target_seed_id": sid,
                "target_seed_name": s_name,
                "available_in_storage": "dynamic_scan",
                "to_collect": to_collect,
                "remaining_needed_before": remaining_needed,
                "remaining_needed_after": 0,
                "surplus_remaining_in_storage": "dynamic"
            })
            total_collected += to_collect
            remaining_needed = 0
        else:
            avail_clamped = max(0, available)
            to_collect = min(avail_clamped, remaining_needed)
            rem_before = remaining_needed
            remaining_needed -= to_collect
            total_collected += to_collect
            surplus_in_storage = max(0, avail_clamped - to_collect)

            steps.append({
                "step_index": idx,
                "world": w_name,
                "target_seed_id": sid,
                "target_seed_name": s_name,
                "available_in_storage": avail_clamped,
                "to_collect": to_collect,
                "remaining_needed_before": rem_before,
                "remaining_needed_after": remaining_needed,
                "surplus_remaining_in_storage": surplus_in_storage
            })

    deficit = remaining_needed
    is_satisfied = (deficit == 0)

    return {
        "seed_id": sid,
        "seed_name": s_name,
        "needed_count": needed,
        "total_collected": total_collected,
        "deficit": deficit,
        "is_fully_satisfied": is_satisfied,
        "status": "satisfied" if is_satisfied else "insufficient_stock",
        "steps": steps,
        "storage_worlds_count": len(steps)
    }


def _parse_storage_worlds(storage_worlds: Any) -> List[Tuple[str, Optional[int]]]:
    """Parses diverse storage world input representations into [(world_name, amount)]."""
    result: List[Tuple[str, Optional[int]]] = []

    if not storage_worlds:
        return result

    if isinstance(storage_worlds, str):
        parts = storage_worlds.split(",")
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if ":" in p:
                w, amt_str = p.split(":", 1)
                w_clean = w.strip().upper()
                if not w_clean:
                    continue
                try:
                    amt = max(0, int(amt_str.strip()))
                except ValueError:
                    amt = None
                result.append((w_clean, amt))
            else:
                w_clean = p.upper()
                if w_clean:
                    result.append((w_clean, None))
        return result

    if isinstance(storage_worlds, dict):
        for k, v in storage_worlds.items():
            w = str(k).strip().upper()
            if not w:
                continue
            amt = None
            if isinstance(v, (int, float)):
                amt = max(0, int(v))
            elif isinstance(v, dict):
                val = v.get("amount") or v.get("count") or v.get("seeds")
                if val is not None:
                    try:
                        amt = max(0, int(val))
                    except (ValueError, TypeError):
                        amt = None
            elif isinstance(v, str) and v.strip().lstrip("-").isdigit():
                try:
                    amt = max(0, int(v.strip()))
                except (ValueError, TypeError):
                    amt = None
            result.append((w, amt))
        return result

    if isinstance(storage_worlds, (list, tuple)):
        for item in storage_worlds:
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                if ":" in item:
                    w, amt_str = item.split(":", 1)
                    w_clean = w.strip().upper()
                    if not w_clean:
                        continue
                    try:
                        amt = max(0, int(amt_str.strip()))
                    except ValueError:
                        amt = None
                    result.append((w_clean, amt))
                else:
                    w_clean = item.upper()
                    if w_clean:
                        result.append((w_clean, None))
            elif isinstance(item, dict):
                w = item.get("world") or item.get("world_name") or item.get("name") or "STORAGE"
                w_clean = str(w).strip().upper()
                if not w_clean:
                    continue
                val = item.get("amount") or item.get("count")
                try:
                    amt = max(0, int(val)) if val is not None else None
                except (ValueError, TypeError):
                    amt = None
                result.append((w_clean, amt))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                w_clean = str(item[0]).strip().upper()
                if not w_clean:
                    continue
                try:
                    amt = max(0, int(item[1]))
                except (ValueError, TypeError):
                    amt = None
                result.append((w_clean, amt))

    return result


# ===========================================================================
# 4. IMMEDIATE SURPLUS PRUNING CALCULATIONS
# ===========================================================================

def calculate_surplus_pruning(
    collected_count: int,
    needed_count: int,
    seed_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculates immediate surplus pruning when an avatar picks up floating seed piles
    that exceed the required quota.

    User Constraint (ORIGINAL_REQUEST.md line 6 & PROJECT.md Section 4.2):
    "Sallıyorum dünya1'de 1500 tane dirt seed vardır ama ekeceği dünyada ekebileceği seed 300'dür,
    300 tane getiricek o dünyaya."
    If picking up floating piles yields 340 seeds when 300 is needed, the surplus is
    Delta = 340 - 300 = 40. The bot immediately drops 40 seeds back onto the ground
    in the storage world before leaving.

    Args:
        collected_count: Total seeds collected in inventory.
        needed_count: Exact required seed quota.
        seed_id: Optional item ID of the seed for packet generation.

    Returns:
        Dict with surplus, drop_count, retained_count, action, and drop packet commands.
    """
    collected = max(0, int(collected_count))
    needed = max(0, int(needed_count))

    surplus = max(0, collected - needed)
    retained = min(collected, needed)
    drop_required = (surplus > 0)

    sid_str = str(seed_id) if seed_id is not None else "<SEED_ID>"

    if drop_required:
        action = "drop_surplus"
        reason = (
            f"Inventory overshoot: collected {collected} seeds exceeds exact quota {needed} "
            f"by {surplus}. Immediate surplus pruning back to storage ground required."
        )
        drop_packets = {
            "text_packet": f"action|drop\n|itemID|{sid_str}",
            "dialog_packet": f"action|dialog_return\ndialog_name|drop_item\nitemID|{sid_str}|\ncount|{surplus}",
            "drop_amount": surplus
        }
    else:
        action = "keep"
        reason = "Collected quantity does not exceed quota. No surplus pruning required."
        drop_packets = None

    return {
        "collected": collected,
        "needed": needed,
        "surplus": surplus,
        "drop_count": surplus,
        "retained_count": retained,
        "drop_required": drop_required,
        "action": action,
        "reason": reason,
        "drop_packet_instructions": drop_packets
    }


# ===========================================================================
# 5. SEQUENTIAL MULTI-FARM COORDINATION
# ===========================================================================

def plan_multi_farm_sequence(
    farm_worlds: Any,
    target_item: str,
    storage_worlds: Any,
    only_above_block: bool = True,
    capacity_override: Optional[int] = None
) -> Dict[str, Any]:
    """
    Coordinates sequential multi-farm execution respecting user grill-me decision 4:
    "Birden fazla tarla dünyası: Sırayla (önce 1. dünya tamamen doldurulup aşılanacak,
    sonra 2. dünyaya geçilecek)."

    For each farm world in sequence:
    1. Scan target farm capacity C_target (Rule 8 geometry filter).
    2. Calculate seed quotas needed for this farm.
    3. Plan storage retrieval across storage worlds, deducting inventory in real-time.
    4. Splicing execution steps:
       - Warp to Farm World -> Stabilize 2.8s.
       - Warp to Storage World(s) -> Fetch Seed A -> Prune surplus.
       - Warp to Farm World -> Plant Base Seed A -> Verify saplings.
       - Warp to Storage World(s) -> Fetch Seed B -> Prune surplus.
       - Warp to Farm World -> Splice Secondary Seed B strictly on Seed A -> Verify tree.
       - Wait maturation ($T_{grow}$) with live ImGui countdown HUD.
       - Dynamic green [ HARVEST ET ] button unlock.
       - Harvest and designated dropping (max 5,000 threshold per tile).
    5. Once Farm 1 completes, automatically advance to Farm 2!

    Args:
        farm_worlds: Farm world names or specs (e.g. "FARM4, FARM5" or [{"world": "FARM4", "capacity": 300}]).
        target_item: Item or seed name/ID to produce.
        storage_worlds: Storage world names and/or seed stocks.
        only_above_block: AGENTS.md Rule 8 soil geometry filter.
        capacity_override: Optional capacity override for farm worlds.

    Returns:
        Dict containing complete sequential multi-farm execution plan.
    """
    parsed_farms = _parse_farm_worlds(farm_worlds, capacity_override)
    if not parsed_farms:
        raise ValueError("At least one farm world must be specified.")

    # Parse initial mutable storage pool
    parsed_storages = _parse_storage_worlds(storage_worlds)
    storage_pool: Dict[str, Optional[int]] = {w: amt for w, amt in parsed_storages}

    farm_plans: List[Dict[str, Any]] = []
    total_capacity = 0
    total_seeds_needed: Dict[int, int] = defaultdict(int)

    for farm_idx, farm_spec in enumerate(parsed_farms, 1):
        farm_name = farm_spec["world"]
        cap = farm_spec["capacity"]
        total_capacity += cap

        # Calculate quotas for this farm
        quotas = calculate_seed_quotas(
            target_item=target_item,
            capacity=cap
        )

        direct_ing = quotas.get("direct_ingredients")
        seed_a_plan = None
        seed_b_plan = None

        if direct_ing:
            seed_a_info = direct_ing["seed_a"]
            seed_b_info = direct_ing["seed_b"]

            # Plan storage retrieval for Seed A
            seed_a_plan = _deduct_from_storage_pool(
                storage_pool=storage_pool,
                seed_id=seed_a_info["seed_id"],
                needed=seed_a_info["needed_count"]
            )
            total_seeds_needed[seed_a_info["seed_id"]] += seed_a_info["needed_count"]

            # Plan storage retrieval for Seed B
            seed_b_plan = _deduct_from_storage_pool(
                storage_pool=storage_pool,
                seed_id=seed_b_info["seed_id"],
                needed=seed_b_info["needed_count"]
            )
            total_seeds_needed[seed_b_info["seed_id"]] += seed_b_info["needed_count"]
        else:
            # Base item
            base_seed_id = quotas["target"]["seed_id"]
            seed_a_plan = _deduct_from_storage_pool(
                storage_pool=storage_pool,
                seed_id=base_seed_id,
                needed=cap
            )
            total_seeds_needed[base_seed_id] += cap

        # Generate sequential workflow phases for this farm
        phases = _generate_farm_execution_phases(
            farm_name=farm_name,
            farm_idx=farm_idx,
            capacity=cap,
            quotas=quotas,
            seed_a_plan=seed_a_plan,
            seed_b_plan=seed_b_plan,
            only_above_block=only_above_block
        )

        farm_plans.append({
            "sequence_order": farm_idx,
            "farm_world": farm_name,
            "capacity": cap,
            "only_above_block": only_above_block,
            "seed_a_retrieval": seed_a_plan,
            "seed_b_retrieval": seed_b_plan,
            "maturation_seconds": quotas["target"]["growth_time_seconds"],
            "maturation_formatted": quotas["target"]["growth_time_formatted"],
            "phases": phases
        })

    target_info = quotas["target"]

    return {
        "status": "success",
        "target": target_info,
        "total_farms": len(farm_plans),
        "total_capacity": total_capacity,
        "total_seeds_needed": dict(total_seeds_needed),
        "storage_pool_remaining": storage_pool,
        "rule_8_compliance": {
            "enforced": bool(only_above_block),
            "mode": "Only Above Solid Blocks (y+1 solid, y empty)" if only_above_block else "All Empty Air Spaces",
            "imgui_checkbox": "ImGui.Checkbox('Only Above Blocks (Dirt etc.)', state.only_above_block)"
        },
        "anti_ban_parameters": {
            "safe_packet_rate_limit": SAFE_PACKET_RATE_LIMIT,
            "placement_base_delay_ms": PLACEMENT_BASE_DELAY_MS,
            "placement_jitter_ms": PLACEMENT_JITTER_MS,
            "world_stabilization_delay_s": WORLD_STABILIZATION_DELAY_S,
            "safe_drop_tile_threshold": SAFE_DROP_TILE_THRESHOLD
        },
        "farm_plans": farm_plans,
        "watermark": WATERMARK
    }


def _parse_farm_worlds(farm_worlds: Any, capacity_override: Optional[int]) -> List[Dict[str, Any]]:
    """Normalizes farm worlds into [{world: str, capacity: int}]."""
    result = []
    default_cap = max(0, int(capacity_override)) if capacity_override is not None else 300

    if not farm_worlds:
        return result

    if isinstance(farm_worlds, str):
        for w in farm_worlds.split(","):
            w = w.strip()
            if w:
                result.append({"world": w.upper(), "capacity": default_cap})
    elif isinstance(farm_worlds, (list, tuple)):
        for item in farm_worlds:
            if isinstance(item, str):
                item = item.strip()
                if item:
                    result.append({"world": item.upper(), "capacity": default_cap})
            elif isinstance(item, dict):
                w = item.get("world") or item.get("world_name") or item.get("name") or "FARM"
                cap = item.get("capacity") or item.get("plantable_count")
                if capacity_override is not None:
                    cap = default_cap
                elif cap is None:
                    cap = default_cap
                try:
                    cap_val = max(0, int(cap))
                except (ValueError, TypeError):
                    cap_val = default_cap
                result.append({"world": str(w).strip().upper(), "capacity": cap_val})
    elif isinstance(farm_worlds, dict):
        for k, v in farm_worlds.items():
            try:
                cap = max(0, int(v)) if isinstance(v, (int, float, str)) else default_cap
            except (ValueError, TypeError):
                cap = default_cap
            if capacity_override is not None:
                cap = default_cap
            result.append({"world": str(k).strip().upper(), "capacity": cap})

    return result


def _deduct_from_storage_pool(
    storage_pool: Dict[str, Optional[int]],
    seed_id: int,
    needed: int
) -> Dict[str, Any]:
    """Plans retrieval from storage pool and mutates available stock in place."""
    steps = []
    needed_val = max(0, int(needed))
    rem_needed = needed_val
    total_collected = 0

    if rem_needed <= 0:
        s_name = _tracer.items_db.get(str(seed_id), f"Seed {seed_id}")
        return {
            "seed_id": seed_id,
            "seed_name": s_name,
            "needed_count": 0,
            "total_collected": 0,
            "deficit": 0,
            "is_fully_satisfied": True,
            "steps": []
        }

    for idx, (w_name, avail) in enumerate(list(storage_pool.items()), 1):
        if rem_needed <= 0:
            break

        if avail is None:
            # Dynamic world scan: collects needed amount
            to_collect = rem_needed
            steps.append({
                "step_index": idx,
                "world": w_name,
                "target_seed_id": seed_id,
                "available_in_storage": "dynamic_scan",
                "to_collect": to_collect,
                "remaining_needed_before": rem_needed,
                "remaining_needed_after": 0,
                "surplus_remaining_in_storage": "dynamic"
            })
            total_collected += to_collect
            rem_needed = 0
        else:
            avail_clamped = max(0, avail)
            to_collect = min(avail_clamped, rem_needed)
            rem_before = rem_needed
            rem_needed -= to_collect
            total_collected += to_collect
            storage_pool[w_name] = max(0, avail_clamped - to_collect)

            steps.append({
                "step_index": idx,
                "world": w_name,
                "target_seed_id": seed_id,
                "available_in_storage": avail_clamped,
                "to_collect": to_collect,
                "remaining_needed_before": rem_before,
                "remaining_needed_after": rem_needed,
                "surplus_remaining_in_storage": storage_pool[w_name]
            })

    deficit = rem_needed
    is_satisfied = (deficit == 0)

    s_name = _tracer.items_db.get(str(seed_id), f"Seed {seed_id}")

    return {
        "seed_id": seed_id,
        "seed_name": s_name,
        "needed_count": needed_val,
        "total_collected": total_collected,
        "deficit": deficit,
        "is_fully_satisfied": is_satisfied,
        "steps": steps
    }


def _generate_farm_execution_phases(
    farm_name: str,
    farm_idx: int,
    capacity: int,
    quotas: Dict[str, Any],
    seed_a_plan: Optional[Dict[str, Any]],
    seed_b_plan: Optional[Dict[str, Any]],
    only_above_block: bool
) -> List[Dict[str, Any]]:
    """Builds concrete step-by-step sequential phases for a farm world."""
    target_info = quotas["target"]
    direct_ing = quotas.get("direct_ingredients")

    phases: List[Dict[str, Any]] = []

    # Phase 1: Warp & Scan Capacity
    phases.append({
        "phase_id": 1,
        "name": f"Scan Farm {farm_name} Capacity",
        "description": f"Warp to {farm_name}, stabilize {WORLD_STABILIZATION_DELAY_S}s, scan grid (1..57, 1..98) for C_target={capacity}.",
        "rule_8_filter": "only_above_block" if only_above_block else "all_empty",
        "action": "warp_and_scan",
        "target_world": farm_name
    })

    # Phase 2: Fetch Base Seed A
    if seed_a_plan:
        phases.append({
            "phase_id": 2,
            "name": f"Retrieve Base Seed A ({seed_a_plan['seed_name']})",
            "description": f"Visit storage world(s) to collect exactly {seed_a_plan['needed_count']} units. Apply immediate surplus pruning if stack overshoots.",
            "action": "storage_collect",
            "steps": seed_a_plan["steps"]
        })

    # Phase 3: Plant Base Seed A
    phases.append({
        "phase_id": 3,
        "name": f"Plant Base Seed A on {farm_name}",
        "description": f"Warp back to {farm_name}, stabilize {WORLD_STABILIZATION_DELAY_S}s, plant Base Seed A on {capacity} verified tiles ({PLACEMENT_BASE_DELAY_MS} +- {PLACEMENT_JITTER_MS}ms Gaussian jitter). Verify sapling fg.",
        "action": "plant_base_seeds",
        "target_world": farm_name
    })

    # Phase 4: Fetch Secondary Seed B (if applicable)
    if seed_b_plan:
        phases.append({
            "phase_id": 4,
            "name": f"Retrieve Secondary Seed B ({seed_b_plan['seed_name']})",
            "description": f"Visit storage world(s) to collect exactly {seed_b_plan['needed_count']} units. Apply immediate surplus pruning if stack overshoots.",
            "action": "storage_collect",
            "steps": seed_b_plan["steps"]
        })

        # Phase 5: Splice Secondary Seed B
        phases.append({
            "phase_id": 5,
            "name": f"Splice Secondary Seed B on {farm_name}",
            "description": f"Warp back to {farm_name}, stabilize {WORLD_STABILIZATION_DELAY_S}s, splice Seed B strictly onto verified Seed A saplings. Verify wasSpliced flag / tree fg.",
            "action": "splice_secondary_seeds",
            "target_world": farm_name
        })

    # Phase 6: Wait Maturation & Live HUD Countdown
    phases.append({
        "phase_id": 6,
        "name": "Maturation Countdown & Verification",
        "description": f"Remain idle in safe zone of {farm_name}. ImGui displays live countdown timer ({target_info['growth_time_formatted']}). Polling getExtraTile(x, y).ready == true.",
        "action": "wait_maturation",
        "duration_seconds": target_info["growth_time_seconds"]
    })

    # Phase 7: Harvest & Designated Dropping
    phases.append({
        "phase_id": 7,
        "name": "User-Triggered Harvest & Designated Drop",
        "description": f"Unlock dynamic green [ HARVEST ET ] button. Pathfind, punch mature trees, collect drops, deposit in designated drop tiles (safe threshold: {SAFE_DROP_TILE_THRESHOLD} items/tile).",
        "action": "harvest_and_drop"
    })

    # Phase 8: Farm Complete
    phases.append({
        "phase_id": 8,
        "name": f"Farm {farm_name} Completed",
        "description": f"All {capacity} trees harvested and dropped. Ready to advance to next farm in sequence.",
        "action": "farm_complete"
    })

    return phases


# ===========================================================================
# 6. LUA CODE GENERATOR HELPERS (SINGLE-THREAD ONRENDER & ASCII SAFE)
# ===========================================================================

def generate_scan_farm_capacity_lua(only_above_block: bool = True) -> str:
    """Generates ASCII-compliant Lua scanning function for GENTAHAX OnRender hook."""
    flag_str = "true" if only_above_block else "false"
    return f"""-- Made by Berk (GentaHAX-MCP repo) -> {REPO_URL}
-- Target Farm Capacity Scanner (Satisfies AGENTS.md Rule 8)
local function scanFarmCapacity(only_above_block)
    if only_above_block == nil then only_above_block = {flag_str} end
    local plantable_count = 0
    local valid_tiles = {{}}

    for y = 1, 57 do
        for x = 1, 98 do
            local c = checkTile(x, y)
            if c and c.fg == 0 then
                if only_above_block then
                    local below = checkTile(x, y + 1)
                    if below and below.fg ~= 0 and below.isCollideable then
                        plantable_count = plantable_count + 1
                        table.insert(valid_tiles, {{ x = x, y = y }})
                    end
                else
                    plantable_count = plantable_count + 1
                    table.insert(valid_tiles, {{ x = x, y = y }})
                end
            end
        end
    end
    return plantable_count, valid_tiles
end
"""


def generate_surplus_prune_lua(seed_id: int, drop_count: int) -> str:
    """Generates ASCII-compliant Lua snippet for immediate surplus pruning."""
    return f"""-- Made by Berk (GentaHAX-MCP repo) -> {REPO_URL}
-- Immediate Surplus Pruning on Ground
local function pruneSurplus(seed_id, drop_amount)
    if drop_amount <= 0 then return end
    sendPacket(2, "action|drop\\n|itemID|" .. tostring(seed_id))
    sendPacket(2, "action|dialog_return\\ndialog_name|drop_item\\nitemID|" .. tostring(seed_id) .. "|\\ncount|" .. tostring(drop_amount))
end
pruneSurplus({seed_id}, {drop_count})
"""
