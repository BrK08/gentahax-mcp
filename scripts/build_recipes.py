#!/usr/bin/env python3
"""
Growtopia Recipe Database Compiler
Generates data/recipes.json from authoritative sources:
- Splicables.txt (832 splicing rules)
- CoreData.txt (item properties, growth times, colors)
- TreeFruitMaxDrop.txt (fruit drop limits)
- items.json (local items database)
"""

import datetime
import json
import os
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

URL_SPLICABLES = "https://raw.githubusercontent.com/NotDark/GrowtopiaItemDatabase/master/GrowtopiaItemDatabase/RecipeData/Splicables.txt"
URL_COREDATA = "https://raw.githubusercontent.com/NotDark/GrowtopiaItemDatabase/master/GrowtopiaItemDatabase/CoreData.txt"
URL_MAX_DROP = "https://raw.githubusercontent.com/NotDark/GrowtopiaItemDatabase/master/GrowtopiaItemDatabase/Data/TreeFruitMaxDrop.txt"

# Known Tier 1 Base Seeds / Catalysts
KNOWN_BASE_SEEDS = {3, 5, 11, 15, 611, 2035, 2037}

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


def fetch_or_cache(url: str, cache_file: Path) -> str:
    if cache_file.exists() and cache_file.stat().st_size > 0:
        return cache_file.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8")
    cache_file.write_text(content, encoding="utf-8")
    return content


def build_recipes():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_dir = DATA_DIR / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    raw_s = fetch_or_cache(URL_SPLICABLES, cache_dir / "Splicables.txt")
    raw_c = fetch_or_cache(URL_COREDATA, cache_dir / "CoreData.txt")
    raw_d = fetch_or_cache(URL_MAX_DROP, cache_dir / "TreeFruitMaxDrop.txt")

    # Load local items
    items_path = DATA_DIR / "items.json"
    with open(items_path, "r", encoding="utf-8") as f:
        items_db = json.load(f)["items"]

    # Build seed <-> item mappings
    seed_to_item = {}
    item_to_seed = {}
    for iid_str, name in items_db.items():
        iid = int(iid_str)
        clean_name = re.sub(r"\s+", " ", name).strip()
        if clean_name.endswith(" Seed"):
            base_name = clean_name[:-5].strip()
            # Try iid - 1 first
            if str(iid - 1) in items_db and re.sub(r"\s+", " ", items_db[str(iid - 1)]).strip() == base_name:
                seed_to_item[iid] = iid - 1
                item_to_seed[iid - 1] = iid
            else:
                # Find matching base item by name
                for cand_id_str, cand_name in items_db.items():
                    if re.sub(r"\s+", " ", cand_name).strip() == base_name and not cand_name.endswith(" Seed"):
                        cand_id = int(cand_id_str)
                        seed_to_item[iid] = cand_id
                        item_to_seed[cand_id] = iid
                        break

    # Register exceptions
    seed_to_item[4455] = 4454  # Mutated Seed -> Mutated Seed Core
    item_to_seed[4454] = 4455
    seed_to_item[5721] = 5720  # Faerie Face Paint Seed -> Faerie Face Paint
    item_to_seed[5720] = 5721
    # Consumable catalysts functioning as seeds
    for cat in (611, 2035, 2037):
        seed_to_item[cat] = cat
        item_to_seed[cat] = cat

    # Max Drops
    max_drops = {}
    for line in raw_d.splitlines():
        l = line.strip()
        if l and not l.startswith("//"):
            parts = l.split("|")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                max_drops[int(parts[0])] = int(parts[1])

    # CoreData
    core_items = {}
    for line in raw_c.splitlines():
        l = line.strip()
        if l and not l.startswith("//"):
            p = l.split("|")
            if len(p) >= 9 and p[0].isdigit():
                iid = int(p[0])
                core_items[iid] = {
                    "name": p[1],
                    "rarity": int(p[2]) if p[2].isdigit() else 1,
                    "category": p[4],
                    "base_color": p[5],
                    "overlay_color": p[6],
                    "growth_seconds": int(p[8]) if p[8].isdigit() else 0
                }

    def normalize_ingredient(ing_id: int) -> int:
        if ing_id in (611, 2035, 2037):
            return ing_id
        # If ingredient is even and ing_id + 1 is a seed, normalize to seed
        if str(ing_id + 1) in items_db and items_db[str(ing_id + 1)].endswith(" Seed"):
            if str(ing_id) in items_db and not items_db[str(ing_id)].endswith(" Seed"):
                return ing_id + 1
        return ing_id

    # Parse Splicables
    raw_rules_count = 0
    splicable_entries = []
    recipes_by_item = defaultdict(list)

    for line in raw_s.splitlines():
        l = line.strip()
        if not l or l.startswith("//"):
            continue
        raw_rules_count += 1
        tokens = [int(x) for x in l.split("|") if x.isdigit()]
        if len(tokens) == 3:
            t, s1, s2 = tokens[0], normalize_ingredient(tokens[1]), normalize_ingredient(tokens[2])
            splicable_entries.append({
                "target_id": t,
                "seed_a": s1,
                "seed_b": s2,
                "is_multi": False,
                "siblings": []
            })
            recipes_by_item[t].append((s1, s2, False, []))
        elif len(tokens) == 4:
            min_t, s1, s2, max_t = tokens[0], normalize_ingredient(tokens[1]), normalize_ingredient(tokens[2]), tokens[3]
            sibs = list(range(min_t, max_t + 1, 2))
            for t in sibs:
                splicable_entries.append({
                    "target_id": t,
                    "seed_a": s1,
                    "seed_b": s2,
                    "is_multi": True,
                    "siblings": sibs
                })
                recipes_by_item[t].append((s1, s2, True, sibs))

    # Calculate tiers using topological memoized search
    tier_cache = {}
    visiting = set()

    def get_tier(seed_id: int) -> int:
        if seed_id in tier_cache:
            return tier_cache[seed_id]
        if seed_id in KNOWN_BASE_SEEDS:
            tier_cache[seed_id] = 1
            return 1
        if seed_id in visiting:
            return 1
        visiting.add(seed_id)

        parent_item = seed_to_item.get(seed_id, seed_id - 1)
        if parent_item not in recipes_by_item:
            tier_cache[seed_id] = 1
            visiting.remove(seed_id)
            return 1

        cand_tiers = []
        for s_a, s_b, _, _ in recipes_by_item[parent_item]:
            cand_tiers.append(1 + max(get_tier(s_a), get_tier(s_b)))

        res = min(cand_tiers) if cand_tiers else 1
        visiting.remove(seed_id)
        tier_cache[seed_id] = res
        return res

    # Helper to resolve item name
    def get_item_name(iid: int) -> str:
        if str(iid) in items_db:
            return items_db[str(iid)]
        if iid in core_items:
            return core_items[iid]["name"]
        return f"Item {iid}"

    def get_seed_name(sid: int) -> str:
        if str(sid) in items_db:
            return items_db[str(sid)]
        if sid in (611, 2035, 2037):
            return get_item_name(sid)
        base_id = seed_to_item.get(sid, sid - 1)
        return f"{get_item_name(base_id)} Seed"

    # Assemble JSON structures
    items_out = {}
    recipes_out = {}
    by_seed_id = {}
    by_ingredient = defaultdict(list)

    # 1. Add all spliceable items
    for item_id, r_list in recipes_by_item.items():
        seed_id = item_to_seed.get(item_id, item_id + 1)
        item_name = get_item_name(item_id)
        seed_name = get_seed_name(seed_id)
        tier = get_tier(seed_id)

        c_info = core_items.get(item_id, {})
        rarity = c_info.get("rarity", 1)
        growth_sec = c_info.get("growth_seconds", 0)
        # Check seed item in coreData if block growth is 0
        if growth_sec == 0 and seed_id in core_items:
            growth_sec = core_items[seed_id].get("growth_seconds", 0)

        growth_fmt = format_duration(growth_sec)
        max_drop = max_drops.get(item_id, 4)
        base_color = c_info.get("base_color", "FFFFFF")
        overlay_color = c_info.get("overlay_color", "FFFFFF")
        category = c_info.get("category", "Foreground_Block")

        # First recipe as primary
        primary_sa, primary_sb, is_multi, sibs = r_list[0]
        ing1_item = seed_to_item.get(primary_sa, primary_sa - 1)
        ing2_item = seed_to_item.get(primary_sb, primary_sb - 1)

        ing_list = [
            {
                "seed_id": primary_sa,
                "seed_name": get_seed_name(primary_sa),
                "item_id": ing1_item,
                "item_name": get_item_name(ing1_item)
            },
            {
                "seed_id": primary_sb,
                "seed_name": get_seed_name(primary_sb),
                "item_id": ing2_item,
                "item_name": get_item_name(ing2_item)
            }
        ]

        items_out[str(item_id)] = {
            "item_id": item_id,
            "name": item_name,
            "seed_id": seed_id,
            "seed_name": seed_name,
            "rarity": rarity,
            "tier": tier,
            "category": category,
            "growth_seconds": growth_sec,
            "growth_formatted": growth_fmt,
            "max_fruit_drop": max_drop,
            "colors": {
                "base": base_color,
                "overlay": overlay_color
            },
            "recipe": {
                "type": "SPLICE",
                "is_multi_output": is_multi,
                "output_siblings": sibs,
                "ingredients": ing_list
            }
        }

        # Recipes table with dual structure support
        item_recipes = []
        for idx, (sa, sb, mult, s_list) in enumerate(r_list):
            i1 = seed_to_item.get(sa, sa - 1)
            i2 = seed_to_item.get(sb, sb - 1)
            item_recipes.append({
                "id": f"r_{item_id}_{idx+1}",
                "target_id": item_id,
                "growth_time_seconds": growth_sec,
                "rarity": rarity,
                "is_multi_output": mult,
                "output_siblings": s_list,
                "ingredient_1": {"id": sa, "name": get_seed_name(sa)},
                "ingredient_2": {"id": sb, "name": get_seed_name(sb)},
                "ingredients": [
                    {"seed_id": sa, "seed_name": get_seed_name(sa), "item_id": i1, "item_name": get_item_name(i1)},
                    {"seed_id": sb, "seed_name": get_seed_name(sb), "item_id": i2, "item_name": get_item_name(i2)}
                ]
            })
            by_ingredient[str(sa)].append(item_id)
            by_ingredient[str(sb)].append(item_id)

        recipes_out[str(item_id)] = item_recipes
        by_seed_id[str(seed_id)] = item_id

    # 2. Add Base Tier 1 Leaf Items (Dirt, Lava, Rock, Cave Background, Sand, etc.)
    base_item_ids = [2, 4, 10, 14, 442, 611, 2035, 2037]
    for b_id in base_item_ids:
        b_str = str(b_id)
        if b_str not in items_out:
            s_id = item_to_seed.get(b_id, b_id + 1)
            c_info = core_items.get(b_id, {})
            name = get_item_name(b_id)
            s_name = get_seed_name(s_id)
            growth = c_info.get("growth_seconds", 31 if b_id in (2, 4, 10, 14) else 0)
            items_out[b_str] = {
                "item_id": b_id,
                "name": name,
                "seed_id": s_id,
                "seed_name": s_name,
                "rarity": c_info.get("rarity", 1),
                "tier": 1,
                "category": c_info.get("category", "Foreground_Block"),
                "growth_seconds": growth,
                "growth_formatted": format_duration(growth),
                "max_fruit_drop": max_drops.get(b_id, 16 if b_id in (2, 4, 14) else 8),
                "colors": {
                    "base": c_info.get("base_color", "FFFFFF"),
                    "overlay": c_info.get("overlay_color", "FFFFFF")
                },
                "recipe": {
                    "type": "TERMINAL_LEAF",
                    "is_multi_output": False,
                    "output_siblings": [],
                    "ingredients": []
                }
            }
            by_seed_id[str(s_id)] = b_id

    # Deduplicate by_ingredient lists
    for k in by_ingredient:
        by_ingredient[k] = sorted(list(set(by_ingredient[k])))

    output_data = {
        "metadata": {
            "version": "1.0.0",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_rules": raw_rules_count,
            "total_spliceable_items": len(recipes_by_item),
            "total_items_in_db": len(items_out),
            "authoritative_sources": [
                URL_SPLICABLES,
                URL_COREDATA,
                URL_MAX_DROP
            ]
        },
        "items": items_out,
        "recipes": recipes_out,
        "by_seed_id": by_seed_id,
        "by_ingredient": dict(by_ingredient)
    }

    out_file = DATA_DIR / "recipes.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully compiled {out_file}!")
    print(f"Total Rules: {raw_rules_count}")
    print(f"Total Spliceable Items: {len(recipes_by_item)}")
    print(f"Total Items Stored: {len(items_out)}")
    print(f"File Size: {out_file.stat().st_size:,} bytes")


if __name__ == "__main__":
    build_recipes()
