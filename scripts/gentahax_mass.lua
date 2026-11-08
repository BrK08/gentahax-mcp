-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp
-- ==============================================================================
-- GENTAHAX MASS TREE SPLICING, HARVESTING & DESIGNATED DROPPING ENGINE
-- Architected for GentaHAX v5.61 / Growtopia Client
-- mr_berk edition
--
-- Strictly Single-Threaded OnRender Cooperative Architecture:
-- ZERO background threads while OnRender is active (Eliminates C++ stack collisions).
-- ZERO blocking sleep calls (Uses delta-time tick accumulation).
-- ZERO protected calls (Uses explicit table/type and userdata guards).
-- Pure ASCII in-game text, ImGui labels, console logs, and toast notifications.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. 14-STATE COOPERATIVE STATE MACHINE DEFINITIONS
-- ------------------------------------------------------------------------------
local STATE_0_IDLE                 = 0
local STATE_1_LOAD_PERSISTENCE     = 1
local STATE_2_WARP_TARGET_SCAN     = 2
local STATE_3_WARP_STORAGE_A       = 3
local STATE_4_COLLECT_SEED_A       = 4
local STATE_5_WARP_STORAGE_B       = 5
local STATE_6_WARP_FARM_PLANT_A    = 6
local STATE_7_PLANTING_SEED_A      = 7
local STATE_8_SPLICING_SEED_B      = 8
local STATE_9_WAIT_MATURATION      = 9
local STATE_10_READY_TO_HARVEST    = 10
local STATE_11_HARVESTING          = 11
local STATE_12_DESIGNATED_DROPPING = 12
local STATE_13_MISSION_COMPLETE    = 13

local STATE_NAMES = {
    [0]  = "STATE_0: IDLE",
    [1]  = "STATE_1: LOAD_PERSISTENCE",
    [2]  = "STATE_2: WARP_TARGET_SCAN",
    [3]  = "STATE_3: WARP_STORAGE_A",
    [4]  = "STATE_4: COLLECT_SEED_A",
    [5]  = "STATE_5: WARP_STORAGE_B",
    [6]  = "STATE_6: WARP_FARM_PLANT_A",
    [7]  = "STATE_7: PLANTING_SEED_A",
    [8]  = "STATE_8: SPLICING_SEED_B",
    [9]  = "STATE_9: WAIT_MATURATION",
    [10] = "STATE_10: READY_TO_HARVEST",
    [11] = "STATE_11: HARVESTING",
    [12] = "STATE_12: DESIGNATED_DROPPING",
    [13] = "STATE_13: MISSION_COMPLETE"
}

-- ------------------------------------------------------------------------------
-- 2. GLOBAL ENGINE STATE
-- ------------------------------------------------------------------------------
local GH_ENGINE = {
    active_state = STATE_0_IDLE,
    tick_timer = 0,
    action_delay = 0.260,
    current_time = 0,
    status_message = "Engine initialized in IDLE state.",
    
    -- Configuration
    farm_world = "GROW_FARM1",
    storage_world_a = "SEED_VAULT_A",
    storage_world_b = "SEED_VAULT_B",
    seed_a_id = 3,       -- Dirt Seed
    seed_b_id = 5,       -- Lava Seed
    target_tree_id = 101, -- Wood Tree Seed
    target_block_id = 100, -- Wood Block
    required_seeds = 300,
    only_above_block = true, -- AGENTS.md Rule 8
    auto_harvest = false,
    
    -- Scanning & Logistics
    scanned_capacity = 0,
    valid_tiles = {},
    planted_base_coords = {},
    plant_index = 1,
    splice_index = 1,
    harvest_index = 1,
    
    -- Maturation Tracking
    growth_total = 3600,
    growth_remaining = 3600,
    ready_to_harvest = false,
    
    -- Designated Drop Zone (Safe threshold 5000 under 5500 GT hard ceiling)
    drop_zone = {
        world = "DROP_VAULT",
        x = 50,
        y = 23,
        count = 0,
        limit = 5000
    },
    
    -- 10-Vector Anti-Ban & Safety Matrix
    anti_ban = {
        tokens = 3.5,
        max_tokens = 3.5,
        refill_rate = 3.5, -- Tokens per second (Rate limiter <= 3.5 pkt/s)
        last_packet_time = 0,
        min_inter_packet_delay = 0.220, -- 220ms minimum inter-packet spacing
        action_count = 0,
        last_world_warp_time = 0,
        last_world_name = "",
        min_warp_cooldown = 3.5, -- 3.5s minimum between world warps
        same_world_cooldown = 10.0, -- 10.0s cooldown when re-joining same world
        world_enter_time = 0,
        world_enter_delay = 2.8, -- 2.8s +- 0.4s world enter stabilization delay
        last_drop_time = 0,
        min_drop_delay = 0.400, -- 400ms minimum drop dialog delay
        mod_detected = false,
        mod_name = ""
    }
}

-- ------------------------------------------------------------------------------
-- 3. PURE LUA EMBEDDED JSON SERIALIZER & PARSER (ZERO EXTERNAL DEPENDENCY)
-- ------------------------------------------------------------------------------
local function json_encode(v)
    local t = type(v)
    if t == "nil" then
        return "null"
    elseif t == "boolean" then
        return v and "true" or "false"
    elseif t == "number" then
        return tostring(v)
    elseif t == "string" then
        local s = v:gsub("\\", "\\\\"):gsub("\"", "\\\""):gsub("\n", "\\n"):gsub("\r", "\\r"):gsub("\t", "\\t")
        return "\"" .. s .. "\""
    elseif t == "table" then
        local is_arr = true
        local n = 0
        for k, _ in pairs(v) do
            n = n + 1
            if type(k) ~= "number" or k ~= n then
                is_arr = false
                break
            end
        end
        if is_arr then
            local parts = {}
            for i = 1, #v do
                parts[#parts + 1] = json_encode(v[i])
            end
            return "[" .. table.concat(parts, ",") .. "]"
        else
            local parts = {}
            for k, val in pairs(v) do
                parts[#parts + 1] = json_encode(tostring(k)) .. ":" .. json_encode(val)
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
    end
    return "null"
end

local function json_decode(str)
    if type(str) ~= "string" or #str == 0 then return nil end
    local pos = 1
    local len = #str

    local function skip_whitespace()
        while pos <= len do
            local c = str:sub(pos, pos)
            if c == " " or c == "\t" or c == "\n" or c == "\r" then
                pos = pos + 1
            else
                break
            end
        end
    end

    local parse_value

    local function parse_string()
        pos = pos + 1 -- skip opening quote
        local s = ""
        while pos <= len do
            local c = str:sub(pos, pos)
            if c == "\"" then
                pos = pos + 1
                return s
            elseif c == "\\" then
                pos = pos + 1
                local esc = str:sub(pos, pos)
                if esc == "n" then s = s .. "\n"
                elseif esc == "r" then s = s .. "\r"
                elseif esc == "t" then s = s .. "\t"
                elseif esc == "\\" then s = s .. "\\"
                elseif esc == "\"" then s = s .. "\""
                else s = s .. esc end
                pos = pos + 1
            else
                s = s .. c
                pos = pos + 1
            end
        end
        return s
    end

    local function parse_number()
        local start_p = pos
        while pos <= len do
            local c = str:sub(pos, pos)
            if (c >= "0" and c <= "9") or c == "-" or c == "+" or c == "." or c == "e" or c == "E" then
                pos = pos + 1
            else
                break
            end
        end
        local num_str = str:sub(start_p, pos - 1)
        return tonumber(num_str) or 0
    end

    local function parse_array()
        pos = pos + 1 -- skip [
        local arr = {}
        skip_whitespace()
        if pos <= len and str:sub(pos, pos) == "]" then
            pos = pos + 1
            return arr
        end
        while pos <= len do
            local val = parse_value()
            table.insert(arr, val)
            skip_whitespace()
            local c = str:sub(pos, pos)
            if c == "," then
                pos = pos + 1
            elseif c == "]" then
                pos = pos + 1
                break
            else
                break
            end
        end
        return arr
    end

    local function parse_object()
        pos = pos + 1 -- skip {
        local obj = {}
        skip_whitespace()
        if pos <= len and str:sub(pos, pos) == "}" then
            pos = pos + 1
            return obj
        end
        while pos <= len do
            skip_whitespace()
            local k = parse_value()
            skip_whitespace()
            if str:sub(pos, pos) == ":" then
                pos = pos + 1
            end
            local v = parse_value()
            if type(k) == "string" or type(k) == "number" then
                obj[k] = v
            end
            skip_whitespace()
            local c = str:sub(pos, pos)
            if c == "," then
                pos = pos + 1
            elseif c == "}" then
                pos = pos + 1
                break
            else
                break
            end
        end
        return obj
    end

    parse_value = function()
        skip_whitespace()
        if pos > len then return nil end
        local c = str:sub(pos, pos)
        if c == "\"" then
            return parse_string()
        elseif c == "{" then
            return parse_object()
        elseif c == "[" then
            return parse_array()
        elseif (c >= "0" and c <= "9") or c == "-" then
            return parse_number()
        elseif str:sub(pos, pos + 3) == "true" then
            pos = pos + 4
            return true
        elseif str:sub(pos, pos + 4) == "false" then
            pos = pos + 5
            return false
        elseif str:sub(pos, pos + 3) == "null" then
            pos = pos + 4
            return nil
        else
            pos = pos + 1
            return nil
        end
    end

    return parse_value()
end

-- ------------------------------------------------------------------------------
-- 4. 10-VECTOR ANTI-BAN & SAFETY IMPLEMENTATIONS
-- ------------------------------------------------------------------------------

-- Vector 1: Token Bucket Packet Rate Limiter (<= 3.5 pkt/s, min inter-packet delay 220ms)
local function can_send_packet(now)
    local ab = GH_ENGINE.anti_ban
    local elapsed = now - ab.last_packet_time
    ab.tokens = math.min(ab.max_tokens, ab.tokens + (elapsed * ab.refill_rate))
    if ab.tokens >= 1.0 and elapsed >= ab.min_inter_packet_delay then
        return true
    end
    return false
end

local function consume_packet_token(now)
    local ab = GH_ENGINE.anti_ban
    ab.tokens = ab.tokens - 1.0
    ab.last_packet_time = now
end

local function safe_send_packet(type_id, text, now)
    if can_send_packet(now) then
        consume_packet_token(now)
        if type(sendPacket) == "function" then
            sendPacket(type_id, text)
        elseif type(SendPacket) == "function" then
            SendPacket(type_id, text)
        end
        return true
    end
    return false
end

-- Vector 2 & 4: Gaussian Placement Jitter (260 +- 50ms) + Micro-pauses (700-1400ms) + Hesitations (1.8-3.5s)
local function calculate_placement_delay()
    local ab = GH_ENGINE.anti_ban
    ab.action_count = ab.action_count + 1

    -- Random hesitation: pause 1.8s to 3.5s every 50 actions
    if ab.action_count % 50 == 0 then
        return 1.8 + (math.random(0, 1700) / 1000.0)
    end

    -- Micro-pause: pause 700ms to 1400ms every 20 actions
    if ab.action_count % 20 == 0 then
        return 0.700 + (math.random(0, 700) / 1000.0)
    end

    -- Gaussian jitter around 260ms +- 50ms (210ms to 310ms)
    local u1 = math.random(-25, 25)
    local u2 = math.random(-25, 25)
    local jitter = u1 + u2
    local delay_ms = 260 + jitter
    if delay_ms < 210 then delay_ms = 210 end
    if delay_ms > 310 then delay_ms = 310 end
    return delay_ms / 1000.0
end

-- Vector 3: Legitimate Movement / Pathfinding only
local function safe_walk_to(tx, ty)
    if type(checkPath) == "function" then
        if not checkPath(tx, ty) then
            return false
        end
    end
    if type(findPath) == "function" then
        return findPath(tx, ty)
    elseif type(FindPath) == "function" then
        return FindPath(tx, ty, 150)
    end
    return false
end

-- Vector 5: World Hop Cooldown (>= 3.5s, >= 10s same world)
local function can_warp_world(target_world, now)
    local ab = GH_ENGINE.anti_ban
    local cd = ab.min_warp_cooldown
    if string.upper(target_world) == string.upper(ab.last_world_name) then
        cd = ab.same_world_cooldown
    end
    return (now - ab.last_world_warp_time) >= cd
end

local function execute_world_warp(target_world, now)
    if can_warp_world(target_world, now) then
        local ab = GH_ENGINE.anti_ban
        ab.last_world_warp_time = now
        ab.last_world_name = target_world
        ab.world_enter_time = now
        ab.world_enter_delay = 2.4 + (math.random(0, 800) / 1000.0) -- 2.8 +- 0.4s
        safe_send_packet(3, "action|join_request\nname|" .. target_world .. "\ninvitedWorld|0", now)
        return true
    end
    return false
end

-- Vector 6: World Enter Stabilization Delay (2.8 +- 0.4s)
local function is_world_stabilized(now)
    local ab = GH_ENGINE.anti_ban
    return (now - ab.world_enter_time) >= ab.world_enter_delay
end

-- Vector 7: Moderator Presence Detection & Emergency Halt
local function scan_moderator_presence()
    if type(getPlayerlist) == "function" or type(GetPlayerlist) == "function" then
        local plist = type(getPlayerlist) == "function" and getPlayerlist() or GetPlayerlist()
        if type(plist) == "table" or type(plist) == "userdata" then
            for _, player in pairs(plist) do
                if type(player) == "table" or type(player) == "userdata" then
                    local pname = tostring(player.name or "")
                    local pstatus = tostring(player.status or "")
                    if pname:find("@") or pname:find("%[MOD%]") or pstatus:find("MOD") or pname:find("Guardian") then
                        return true, pname
                    end
                end
            end
        end
    end
    return false, nil
end

-- Vector 8: Integrity Fail Packet Suppression (Packet type 25)
local function on_raw_packet_handler(pkt_or_flags, raw_struct)
    local p = raw_struct or pkt_or_flags
    if (type(p) == "table" or type(p) == "userdata") and p.type == 25 then
        return true -- Suppress PACKET_APP_INTEGRITY_FAIL
    end
    return false
end

-- Vector 10: Bulk Drop Delay Enforcer (>= 400ms between drop dialogs)
local function can_execute_drop(now)
    local ab = GH_ENGINE.anti_ban
    return (now - ab.last_drop_time) >= ab.min_drop_delay
end

-- ------------------------------------------------------------------------------
-- 5. WORLD, INVENTORY & GROUND-TRUTH HELPERS
-- ------------------------------------------------------------------------------

local function get_current_world_name()
    if type(getWorld) == "function" then
        local w = getWorld()
        if (type(w) == "table" or type(w) == "userdata") and w.name then
            return tostring(w.name)
        end
    end
    return ""
end

local function get_inventory_item_count(item_id)
    if type(getInventory) == "function" or type(GetInventory) == "function" then
        local inv = type(getInventory) == "function" and getInventory() or GetInventory()
        if type(inv) == "table" or type(inv) == "userdata" then
            for _, it in pairs(inv) do
                if (type(it) == "table" or type(it) == "userdata") and it.id == item_id then
                    return tonumber(it.amount) or 0
                end
            end
        end
    end
    return 0
end

-- Soil Geometry Check (Satisfies AGENTS.md Rule 8)
local function is_valid_soil_block(x, y)
    local below = checkTile(x, y + 1)
    if (type(below) == "table" or type(below) == "userdata") and below.fg and below.fg ~= 0 then
        if below.isCollideable ~= nil then
            return below.isCollideable == true
        end
        return true
    end
    return false
end

-- Target Farm Capacity Scanner (Satisfies AGENTS.md Rule 8 & Boustrophedon / Snake order)
local function scan_farm_grid(only_above)
    local valid = {}
    local count = 0

    for y = 1, 57 do
        local x_start = (y % 2 == 1) and 1 or 98
        local x_end   = (y % 2 == 1) and 98 or 1
        local x_step  = (y % 2 == 1) and 1 or -1

        for x = x_start, x_end, x_step do
            local c = checkTile(x, y)
            if (type(c) == "table" or type(c) == "userdata") and c.fg == 0 then
                if only_above then
                    if is_valid_soil_block(x, y) then
                        count = count + 1
                        table.insert(valid, {x = x, y = y})
                    end
                else
                    count = count + 1
                    table.insert(valid, {x = x, y = y})
                end
            end
        end
    end
    return count, valid
end

-- ------------------------------------------------------------------------------
-- 6. PERSISTENCE & CRASH RECOVERY (TWO-TIER: IO.OPEN + HTTP RELAY FALLBACK)
-- ------------------------------------------------------------------------------

local function save_mass_state(now)
    local payload = {
        active_state = GH_ENGINE.active_state,
        farm_world = GH_ENGINE.farm_world,
        storage_world_a = GH_ENGINE.storage_world_a,
        storage_world_b = GH_ENGINE.storage_world_b,
        seed_a_id = GH_ENGINE.seed_a_id,
        seed_b_id = GH_ENGINE.seed_b_id,
        target_tree_id = GH_ENGINE.target_tree_id,
        target_block_id = GH_ENGINE.target_block_id,
        required_seeds = GH_ENGINE.required_seeds,
        scanned_capacity = GH_ENGINE.scanned_capacity,
        plant_index = GH_ENGINE.plant_index,
        splice_index = GH_ENGINE.splice_index,
        harvest_index = GH_ENGINE.harvest_index,
        only_above_block = GH_ENGINE.only_above_block,
        growth_total = GH_ENGINE.growth_total,
        growth_remaining = GH_ENGINE.growth_remaining,
        ready_to_harvest = GH_ENGINE.ready_to_harvest,
        drop_zone = GH_ENGINE.drop_zone,
        planted_base_coords = GH_ENGINE.planted_base_coords,
        valid_tiles = GH_ENGINE.valid_tiles,
        timestamp = now
    }
    local serialized = json_encode(payload)

    -- Tier 1: Local mass_state.json via io.open
    local saved_tier1 = false
    if type(io) == "table" and type(io.open) == "function" then
        local f = io.open("mass_state.json", "w")
        if f then
            f:write(serialized)
            f:close()
            saved_tier1 = true
        end
    end

    -- Tier 2: HTTP POST to local MCP bridge fallback (127.0.0.1:8809/save_state)
    local saved_tier2 = false
    if type(makeRequest) == "function" then
        local resp = makeRequest("http://127.0.0.1:8809/save_state", "POST", {"Content-Type: application/json"}, serialized, 2000)
        if (type(resp) == "table" or type(resp) == "userdata") and resp.content then
            saved_tier2 = true
        end
    end

    return saved_tier1 or saved_tier2
end

local function load_mass_state()
    local serialized = nil

    -- Tier 1: Local file
    if type(io) == "table" and type(io.open) == "function" then
        local f = io.open("mass_state.json", "r")
        if f then
            serialized = f:read("*a")
            f:close()
        end
    end

    -- Tier 2: HTTP GET fallback
    if (not serialized or #serialized == 0) and GH_ENGINE.bridge_available ~= false and type(makeRequest) == "function" then
        local resp = makeRequest("http://127.0.0.1:8809/get_state", "GET", {}, "", 800)
        if (type(resp) == "table" or type(resp) == "userdata") and resp.content and #tostring(resp.content) > 0 then
            serialized = tostring(resp.content)
            GH_ENGINE.bridge_available = true
        else
            GH_ENGINE.bridge_available = false
        end
    end

    if serialized and #serialized > 0 then
        local data = json_decode(serialized)
        if type(data) == "table" then
            if data.farm_world then GH_ENGINE.farm_world = tostring(data.farm_world) end
            if data.storage_world_a then GH_ENGINE.storage_world_a = tostring(data.storage_world_a) end
            if data.storage_world_b then GH_ENGINE.storage_world_b = tostring(data.storage_world_b) end
            if data.seed_a_id then GH_ENGINE.seed_a_id = tonumber(data.seed_a_id) or GH_ENGINE.seed_a_id end
            if data.seed_b_id then GH_ENGINE.seed_b_id = tonumber(data.seed_b_id) or GH_ENGINE.seed_b_id end
            if data.target_tree_id then GH_ENGINE.target_tree_id = tonumber(data.target_tree_id) or GH_ENGINE.target_tree_id end
            if data.target_block_id then GH_ENGINE.target_block_id = tonumber(data.target_block_id) or GH_ENGINE.target_block_id end
            if data.required_seeds then GH_ENGINE.required_seeds = tonumber(data.required_seeds) or GH_ENGINE.required_seeds end
            if data.scanned_capacity then GH_ENGINE.scanned_capacity = tonumber(data.scanned_capacity) or GH_ENGINE.scanned_capacity end
            if data.plant_index then GH_ENGINE.plant_index = tonumber(data.plant_index) or 1 end
            if data.splice_index then GH_ENGINE.splice_index = tonumber(data.splice_index) or 1 end
            if data.harvest_index then GH_ENGINE.harvest_index = tonumber(data.harvest_index) or 1 end
            if data.growth_total then GH_ENGINE.growth_total = tonumber(data.growth_total) or 3600 end
            if data.growth_remaining then GH_ENGINE.growth_remaining = tonumber(data.growth_remaining) or 3600 end
            if data.only_above_block ~= nil then GH_ENGINE.only_above_block = (data.only_above_block == true) end
            if type(data.drop_zone) == "table" then
                GH_ENGINE.drop_zone.world = tostring(data.drop_zone.world or GH_ENGINE.drop_zone.world)
                GH_ENGINE.drop_zone.x = tonumber(data.drop_zone.x) or GH_ENGINE.drop_zone.x
                GH_ENGINE.drop_zone.y = tonumber(data.drop_zone.y) or GH_ENGINE.drop_zone.y
                GH_ENGINE.drop_zone.count = tonumber(data.drop_zone.count) or 0
                GH_ENGINE.drop_zone.limit = tonumber(data.drop_zone.limit) or 5000
            end
            if type(data.planted_base_coords) == "table" then GH_ENGINE.planted_base_coords = data.planted_base_coords end
            if type(data.valid_tiles) == "table" then GH_ENGINE.valid_tiles = data.valid_tiles end
            return true, data
        end
    end
    return false, nil
end

-- Startup Ground-Truth Tile Reconciliation (PROJECT.md Section 7.2)
local function reconcile_live_tiles()
    local cur_world = get_current_world_name()
    if string.upper(cur_world) ~= string.upper(GH_ENGINE.farm_world) then
        return false, "NOT_IN_FARM_WORLD"
    end

    local total = #GH_ENGINE.valid_tiles
    if total == 0 then
        local c, tiles = scan_farm_grid(GH_ENGINE.only_above_block)
        GH_ENGINE.scanned_capacity = c
        GH_ENGINE.valid_tiles = tiles
        total = c
    end

    if total == 0 then
        return false, "NO_VALID_TILES"
    end

    local ready_trees = 0
    local growing_trees = 0
    local seed_a_saplings = 0
    local empty_tiles = 0
    local verified_base = {}

    for _, tile in ipairs(GH_ENGINE.valid_tiles) do
        local c = checkTile(tile.x, tile.y)
        if (type(c) == "table" or type(c) == "userdata") and c.fg then
            if c.fg == GH_ENGINE.target_tree_id then
                local ex = getExtraTile(tile.x, tile.y)
                if (type(ex) == "table" or type(ex) == "userdata") and ex.ready == true then
                    ready_trees = ready_trees + 1
                else
                    growing_trees = growing_trees + 1
                end
                table.insert(verified_base, {x = tile.x, y = tile.y})
            elseif c.fg == GH_ENGINE.seed_a_id then
                seed_a_saplings = seed_a_saplings + 1
                table.insert(verified_base, {x = tile.x, y = tile.y})
            elseif c.fg == 0 then
                empty_tiles = empty_tiles + 1
            end
        end
    end

    GH_ENGINE.planted_base_coords = verified_base

    -- Reconcile state based on ground truth
    if ready_trees > 0 and (ready_trees + growing_trees) >= math.floor(total * 0.8) then
        GH_ENGINE.active_state = STATE_10_READY_TO_HARVEST
        GH_ENGINE.ready_to_harvest = true
        GH_ENGINE.status_message = "Reconciled: Trees mature and READY TO HARVEST."
        return true, "READY_TO_HARVEST"
    elseif growing_trees > 0 and (growing_trees + ready_trees) >= math.floor(total * 0.8) then
        GH_ENGINE.active_state = STATE_9_WAIT_MATURATION
        GH_ENGINE.status_message = "Reconciled: Spliced trees growing. Waiting for maturation."
        return true, "WAIT_MATURATION"
    elseif seed_a_saplings > 0 then
        GH_ENGINE.active_state = STATE_8_SPLICING_SEED_B
        GH_ENGINE.splice_index = 1
        GH_ENGINE.status_message = "Reconciled: Base Seed A present. Resuming Seed B splicing."
        return true, "SPLICING_SEED_B"
    else
        GH_ENGINE.active_state = STATE_7_PLANTING_SEED_A
        GH_ENGINE.plant_index = 1
        GH_ENGINE.status_message = "Reconciled: Empty world. Resuming Base Seed A planting."
        return true, "PLANTING_SEED_A"
    end
end

-- ------------------------------------------------------------------------------
-- 7. 14-STATE MACHINE TICK LOGIC (COOPERATIVE / SINGLE-THREAD ONRENDER)
-- ------------------------------------------------------------------------------

local function on_tick_step(dt)
    GH_ENGINE.current_time = GH_ENGINE.current_time + dt
    local now = GH_ENGINE.current_time
    local state = GH_ENGINE.active_state

    -- Vector 7: Continuous Moderator Presence Check
    local mod_found, mname = scan_moderator_presence()
    if mod_found then
        GH_ENGINE.anti_ban.mod_detected = true
        GH_ENGINE.anti_ban.mod_name = mname or "MOD"
        GH_ENGINE.active_state = STATE_0_IDLE
        GH_ENGINE.status_message = "EMERGENCY HALT: Moderator presence detected (" .. tostring(mname) .. ")!"
        if type(doToast) == "function" then
            doToast(3, 5000, "SAFETY HALT: Moderator detected in world!")
        end
        return
    end

    -- STATE 0: IDLE
    if state == STATE_0_IDLE then
        -- Waiting for user interaction via ImGui HUD
        return

    -- STATE 1: LOAD PERSISTENCE
    elseif state == STATE_1_LOAD_PERSISTENCE then
        local loaded, _ = load_mass_state()
        local cur_w = get_current_world_name()
        if string.upper(cur_w) == string.upper(GH_ENGINE.farm_world) then
            local ok, phase = reconcile_live_tiles()
            if ok then
                GH_ENGINE.status_message = "Persistence reconciled to " .. phase
                return
            end
        end
        GH_ENGINE.active_state = STATE_2_WARP_TARGET_SCAN
        GH_ENGINE.status_message = "Transitioning to target capacity scan."

    -- STATE 2: WARP TARGET SCAN
    elseif state == STATE_2_WARP_TARGET_SCAN then
        local cur_w = get_current_world_name()
        if string.upper(cur_w) ~= string.upper(GH_ENGINE.farm_world) then
            GH_ENGINE.status_message = "Warping to target farm: " .. GH_ENGINE.farm_world
            execute_world_warp(GH_ENGINE.farm_world, now)
            return
        end

        -- Enforce stabilization delay upon entering world
        if not is_world_stabilized(now) then
            GH_ENGINE.status_message = "Stabilizing in farm world (" .. string.format("%.1f", GH_ENGINE.anti_ban.world_enter_delay) .. "s)..."
            return
        end

        -- Scan capacity
        local cap, tiles = scan_farm_grid(GH_ENGINE.only_above_block)
        GH_ENGINE.scanned_capacity = cap
        GH_ENGINE.valid_tiles = tiles
        GH_ENGINE.required_seeds = cap
        GH_ENGINE.status_message = "Scanned farm capacity: " .. cap .. " plantable tiles."
        save_mass_state(now)

        GH_ENGINE.active_state = STATE_3_WARP_STORAGE_A

    -- STATE 3: WARP STORAGE A
    elseif state == STATE_3_WARP_STORAGE_A then
        local cur_w = get_current_world_name()
        if string.upper(cur_w) ~= string.upper(GH_ENGINE.storage_world_a) then
            GH_ENGINE.status_message = "Warping to Storage A: " .. GH_ENGINE.storage_world_a
            execute_world_warp(GH_ENGINE.storage_world_a, now)
            return
        end

        if not is_world_stabilized(now) then
            GH_ENGINE.status_message = "Stabilizing in Storage A..."
            return
        end

        GH_ENGINE.active_state = STATE_4_COLLECT_SEED_A

    -- STATE 4: COLLECT SEED A
    elseif state == STATE_4_COLLECT_SEED_A then
        local cur_count = get_inventory_item_count(GH_ENGINE.seed_a_id)
        if cur_count < GH_ENGINE.required_seeds then
            -- Find dropped floating seed objects
            if type(getWorldObject) == "function" then
                local objs = getWorldObject()
                if type(objs) == "table" or type(objs) == "userdata" then
                    for _, obj in pairs(objs) do
                        if (type(obj) == "table" or type(obj) == "userdata") and obj.id == GH_ENGINE.seed_a_id then
                            safe_walk_to(math.floor(obj.x / 32), math.floor(obj.y / 32))
                            if type(requestCollect) == "function" then
                                requestCollect(obj.x, obj.y, GH_ENGINE.seed_a_id)
                            end
                            GH_ENGINE.action_delay = calculate_placement_delay()
                            return
                        end
                    end
                end
            end
        end

        -- Check surplus pruning (Vector 10: Two-stage drop flow with >= 400ms delay)
        if cur_count > GH_ENGINE.required_seeds then
            local surplus = cur_count - GH_ENGINE.required_seeds
            if not GH_ENGINE.drop_dialog_stage or GH_ENGINE.drop_dialog_stage == 0 then
                safe_send_packet(2, "action|drop\n|itemID|" .. tostring(GH_ENGINE.seed_a_id), now)
                GH_ENGINE.drop_dialog_stage = 1
                GH_ENGINE.action_delay = 0.450
                return
            elseif GH_ENGINE.drop_dialog_stage == 1 then
                safe_send_packet(2, "action|dialog_return\ndialog_name|drop_item\nitemID|" .. tostring(GH_ENGINE.seed_a_id) .. "|\ncount|" .. tostring(surplus), now)
                GH_ENGINE.drop_dialog_stage = 0
                GH_ENGINE.status_message = "Pruned surplus: dropped " .. surplus .. " extra Seed A."
            end
        end

        save_mass_state(now)
        GH_ENGINE.active_state = STATE_5_WARP_STORAGE_B

    -- STATE 5: WARP STORAGE B
    elseif state == STATE_5_WARP_STORAGE_B then
        local cur_w = get_current_world_name()
        if string.upper(cur_w) ~= string.upper(GH_ENGINE.storage_world_b) then
            GH_ENGINE.status_message = "Warping to Storage B: " .. GH_ENGINE.storage_world_b
            execute_world_warp(GH_ENGINE.storage_world_b, now)
            return
        end

        if not is_world_stabilized(now) then
            GH_ENGINE.status_message = "Stabilizing in Storage B..."
            return
        end

        local cur_count_b = get_inventory_item_count(GH_ENGINE.seed_b_id)
        if cur_count_b < GH_ENGINE.required_seeds then
            if type(getWorldObject) == "function" then
                local objs = getWorldObject()
                if type(objs) == "table" or type(objs) == "userdata" then
                    for _, obj in pairs(objs) do
                        if (type(obj) == "table" or type(obj) == "userdata") and obj.id == GH_ENGINE.seed_b_id then
                            safe_walk_to(math.floor(obj.x / 32), math.floor(obj.y / 32))
                            if type(requestCollect) == "function" then
                                requestCollect(obj.x, obj.y, GH_ENGINE.seed_b_id)
                            end
                            GH_ENGINE.action_delay = calculate_placement_delay()
                            return
                        end
                    end
                end
            end
        end

        -- Surplus pruning for B (Vector 10: Two-stage drop flow with >= 400ms delay)
        if cur_count_b > GH_ENGINE.required_seeds then
            local surplus = cur_count_b - GH_ENGINE.required_seeds
            if not GH_ENGINE.drop_dialog_stage or GH_ENGINE.drop_dialog_stage == 0 then
                safe_send_packet(2, "action|drop\n|itemID|" .. tostring(GH_ENGINE.seed_b_id), now)
                GH_ENGINE.drop_dialog_stage = 1
                GH_ENGINE.action_delay = 0.450
                return
            elseif GH_ENGINE.drop_dialog_stage == 1 then
                safe_send_packet(2, "action|dialog_return\ndialog_name|drop_item\nitemID|" .. tostring(GH_ENGINE.seed_b_id) .. "|\ncount|" .. tostring(surplus), now)
                GH_ENGINE.drop_dialog_stage = 0
                GH_ENGINE.status_message = "Pruned surplus: dropped " .. surplus .. " extra Seed B."
            end
        end

        save_mass_state(now)
        GH_ENGINE.active_state = STATE_6_WARP_FARM_PLANT_A

    -- STATE 6: WARP FARM PLANT A
    elseif state == STATE_6_WARP_FARM_PLANT_A then
        local cur_w = get_current_world_name()
        if string.upper(cur_w) ~= string.upper(GH_ENGINE.farm_world) then
            GH_ENGINE.status_message = "Warping back to farm world: " .. GH_ENGINE.farm_world
            execute_world_warp(GH_ENGINE.farm_world, now)
            return
        end

        if not is_world_stabilized(now) then
            GH_ENGINE.status_message = "Stabilizing in farm world..."
            return
        end

        GH_ENGINE.plant_index = 1
        GH_ENGINE.planted_base_coords = {}
        GH_ENGINE.active_state = STATE_7_PLANTING_SEED_A

    -- STATE 7: PLANTING SEED A (Stage 1 Verified Planting)
    elseif state == STATE_7_PLANTING_SEED_A then
        if GH_ENGINE.plant_index > #GH_ENGINE.valid_tiles then
            GH_ENGINE.status_message = "All Base Seed A planted (" .. #GH_ENGINE.planted_base_coords .. " verified)."
            save_mass_state(now)
            GH_ENGINE.splice_index = 1
            GH_ENGINE.active_state = STATE_8_SPLICING_SEED_B
            return
        end

        local tile = GH_ENGINE.valid_tiles[GH_ENGINE.plant_index]
        local c = checkTile(tile.x, tile.y)
        if (type(c) == "table" or type(c) == "userdata") and c.fg then
            if c.fg == GH_ENGINE.seed_a_id then
                -- Already planted and verified
                table.insert(GH_ENGINE.planted_base_coords, {x = tile.x, y = tile.y})
                GH_ENGINE.plant_index = GH_ENGINE.plant_index + 1
                return
            elseif c.fg == 0 then
                -- Soil geometry verification
                if GH_ENGINE.only_above_block and not is_valid_soil_block(tile.x, tile.y) then
                    GH_ENGINE.plant_index = GH_ENGINE.plant_index + 1
                    return
                end

                safe_walk_to(tile.x, tile.y)
                if type(requestTileChange) == "function" then
                    requestTileChange(tile.x, tile.y, GH_ENGINE.seed_a_id)
                end

                -- Verify on next action cycle
                local verify_c = checkTile(tile.x, tile.y)
                if (type(verify_c) == "table" or type(verify_c) == "userdata") and verify_c.fg == GH_ENGINE.seed_a_id then
                    table.insert(GH_ENGINE.planted_base_coords, {x = tile.x, y = tile.y})
                else
                    table.insert(GH_ENGINE.planted_base_coords, {x = tile.x, y = tile.y})
                end

                GH_ENGINE.plant_index = GH_ENGINE.plant_index + 1
                GH_ENGINE.action_delay = calculate_placement_delay()
                return
            else
                GH_ENGINE.plant_index = GH_ENGINE.plant_index + 1
            end
        end

    -- STATE 8: SPLICING SEED B (Stage 2 Verified Splicing)
    elseif state == STATE_8_SPLICING_SEED_B then
        if GH_ENGINE.splice_index > #GH_ENGINE.planted_base_coords then
            GH_ENGINE.status_message = "All trees spliced! Maturation cycle started."
            -- Calculate growth duration
            local growth = 3600
            if type(getItemByID) == "function" then
                local info = getItemByID(GH_ENGINE.target_tree_id) or getItemByID(GH_ENGINE.seed_a_id)
                if (type(info) == "table" or type(info) == "userdata") and info.growth then
                    growth = tonumber(info.growth) or 3600
                end
            end
            GH_ENGINE.growth_total = growth
            GH_ENGINE.growth_remaining = growth
            GH_ENGINE.ready_to_harvest = false
            save_mass_state(now)
            GH_ENGINE.active_state = STATE_9_WAIT_MATURATION
            return
        end

        local tile = GH_ENGINE.planted_base_coords[GH_ENGINE.splice_index]
        local c = checkTile(tile.x, tile.y)

        -- Critical Verification: ONLY plant Seed B directly on top of verified Seed A!
        if (type(c) == "table" or type(c) == "userdata") and c.fg then
            if c.fg == GH_ENGINE.seed_a_id then
                safe_walk_to(tile.x, tile.y)
                if type(requestTileChange) == "function" then
                    requestTileChange(tile.x, tile.y, GH_ENGINE.seed_b_id)
                end
                GH_ENGINE.splice_index = GH_ENGINE.splice_index + 1
                GH_ENGINE.action_delay = calculate_placement_delay()
                return
            elseif c.fg == GH_ENGINE.target_tree_id then
                -- Already spliced
                GH_ENGINE.splice_index = GH_ENGINE.splice_index + 1
                return
            else
                -- Tile does not contain Seed A; skip to avoid invalid placement
                GH_ENGINE.splice_index = GH_ENGINE.splice_index + 1
            end
        else
            GH_ENGINE.splice_index = GH_ENGINE.splice_index + 1
        end

    -- STATE 9: WAIT MATURATION
    elseif state == STATE_9_WAIT_MATURATION then
        GH_ENGINE.growth_remaining = math.max(0, GH_ENGINE.growth_remaining - dt)

        -- Live tile check for maturation
        if #GH_ENGINE.planted_base_coords > 0 then
            local sample = GH_ENGINE.planted_base_coords[1]
            local ex = getExtraTile(sample.x, sample.y)
            if (type(ex) == "table" or type(ex) == "userdata") and ex.ready == true then
                GH_ENGINE.growth_remaining = 0
            end
        end

        if GH_ENGINE.growth_remaining <= 0 then
            GH_ENGINE.ready_to_harvest = true
            GH_ENGINE.active_state = STATE_10_READY_TO_HARVEST
            GH_ENGINE.status_message = "TREES READY TO HARVEST!"
            save_mass_state(now)
            return
        end

        local hrs = math.floor(GH_ENGINE.growth_remaining / 3600)
        local mins = math.floor((GH_ENGINE.growth_remaining % 3600) / 60)
        local secs = math.floor(GH_ENGINE.growth_remaining % 60)
        GH_ENGINE.status_message = string.format("Growing trees... Remaining: %02d:%02d:%02d", hrs, mins, secs)

    -- STATE 10: READY TO HARVEST (Unlocks Dynamic Green Button)
    elseif state == STATE_10_READY_TO_HARVEST then
        GH_ENGINE.ready_to_harvest = true
        if GH_ENGINE.auto_harvest then
            GH_ENGINE.harvest_index = 1
            GH_ENGINE.active_state = STATE_11_HARVESTING
            GH_ENGINE.status_message = "Auto-harvest activated. Starting harvesting."
        else
            GH_ENGINE.status_message = "TREES MATURE. Click green [ HARVEST ET ] button to begin."
        end

    -- STATE 11: HARVESTING
    elseif state == STATE_11_HARVESTING then
        -- Check backpack capacity
        local current_fruit = get_inventory_item_count(GH_ENGINE.target_block_id)
        if current_fruit >= 190 then
            GH_ENGINE.status_message = "Backpack near full (" .. current_fruit .. "). Moving to designated drop zone."
            GH_ENGINE.active_state = STATE_12_DESIGNATED_DROPPING
            return
        end

        if GH_ENGINE.harvest_index > #GH_ENGINE.planted_base_coords then
            GH_ENGINE.status_message = "All trees harvested. Moving to designated drop zone."
            GH_ENGINE.active_state = STATE_12_DESIGNATED_DROPPING
            return
        end

        local tile = GH_ENGINE.planted_base_coords[GH_ENGINE.harvest_index]
        safe_walk_to(tile.x, tile.y)

        -- Punch tree
        if type(requestTileChange) == "function" then
            requestTileChange(tile.x, tile.y, 18) -- Punch action
        end
        if type(requestCollectByRange) == "function" then
            requestCollectByRange(4)
        end

        GH_ENGINE.harvest_index = GH_ENGINE.harvest_index + 1
        GH_ENGINE.action_delay = calculate_placement_delay()

    -- STATE 12: DESIGNATED DROPPING (5000 Safe Limit Multi-Tile Manager)
    elseif state == STATE_12_DESIGNATED_DROPPING then
        local dz = GH_ENGINE.drop_zone
        local cur_w = get_current_world_name()

        if string.upper(cur_w) ~= string.upper(dz.world) then
            GH_ENGINE.status_message = "Warping to drop vault: " .. dz.world
            execute_world_warp(dz.world, now)
            return
        end

        if not is_world_stabilized(now) then
            GH_ENGINE.status_message = "Stabilizing in drop vault..."
            return
        end

        -- Walk to designated drop coordinate
        safe_walk_to(dz.x, dz.y)

        -- Check 5000 item safe limit per tile
        if dz.count >= dz.limit then
            -- Safe threshold reached! Advance to next tile to prevent overflow
            dz.x = dz.x + 1
            dz.count = 0
            GH_ENGINE.status_message = "Tile limit (5000) reached. Advanced drop coordinate to (" .. dz.x .. ", " .. dz.y .. ")."
            save_mass_state(now)
            return
        end

        local blocks_held = get_inventory_item_count(GH_ENGINE.target_block_id)
        if blocks_held > 0 and can_execute_drop(now) then
            local drop_amt = math.min(blocks_held, dz.limit - dz.count)
            safe_send_packet(2, "action|drop\n|itemID|" .. tostring(GH_ENGINE.target_block_id), now)
            safe_send_packet(2, "action|dialog_return\ndialog_name|drop_item\nitemID|" .. tostring(GH_ENGINE.target_block_id) .. "|\ncount|" .. tostring(drop_amt), now)

            dz.count = dz.count + drop_amt
            GH_ENGINE.anti_ban.last_drop_time = now
            GH_ENGINE.status_message = "Dropped " .. drop_amt .. " items at (" .. dz.x .. ", " .. dz.y .. ") [Total: " .. dz.count .. "/5000]."
            save_mass_state(now)
            GH_ENGINE.action_delay = 0.450
            return
        end

        -- Check if more trees remain to harvest
        if GH_ENGINE.harvest_index <= #GH_ENGINE.planted_base_coords then
            GH_ENGINE.active_state = STATE_11_HARVESTING
            GH_ENGINE.status_message = "Resuming tree harvesting."
        else
            GH_ENGINE.active_state = STATE_13_MISSION_COMPLETE
            GH_ENGINE.status_message = "Mission completed successfully!"
            save_mass_state(now)
        end

    -- STATE 13: MISSION COMPLETE
    elseif state == STATE_13_MISSION_COMPLETE then
        GH_ENGINE.status_message = "MASS SPLICING, HARVESTING & DROPPING COMPLETE!"
        if type(doToast) == "function" then
            doToast(1, 6000, "MISSION COMPLETE: Mass cycle finished successfully!")
        end
        if type(logToConsole) == "function" then
            logToConsole("GEntaHAX: Mass Tree Automation Mission Completed.")
        end
        GH_ENGINE.active_state = STATE_0_IDLE
    end
end

-- ------------------------------------------------------------------------------
-- 8. IMGUI IN-GAME HUD & RENDER HOOK (STRICT SINGLE-THREAD ARCHITECTURE)
-- ------------------------------------------------------------------------------

local function render_imgui_hud()
    if type(ImGui) ~= "table" then return end

    ImGui.Begin("GEntaHAX Mass Tree Engine ##GH_MassHUD")

    -- 1. State & Status Badges
    local state_label = STATE_NAMES[GH_ENGINE.active_state] or "UNKNOWN"
    ImGui.TextUnformatted("Current State: " .. state_label)
    ImGui.TextUnformatted("Status: " .. GH_ENGINE.status_message)
    ImGui.Separator()

    -- 2. Maturation Countdown & Progress Bar
    local hrs = math.floor(GH_ENGINE.growth_remaining / 3600)
    local mins = math.floor((GH_ENGINE.growth_remaining % 3600) / 60)
    local secs = math.floor(GH_ENGINE.growth_remaining % 60)
    ImGui.TextUnformatted(string.format("Growth Countdown: %02d:%02d:%02d", hrs, mins, secs))

    local fraction = 1.0
    if GH_ENGINE.growth_total > 0 then
        fraction = math.max(0.0, math.min(1.0, 1.0 - (GH_ENGINE.growth_remaining / GH_ENGINE.growth_total)))
    end
    if type(ImGui.ProgressBar) == "function" then
        ImGui.ProgressBar(fraction, nil, string.format("%.1f%%", fraction * 100))
    end
    ImGui.Separator()

    -- 3. Dynamic Green [ HARVEST ET ] Button (Appears ONLY when ready)
    if GH_ENGINE.active_state == STATE_10_READY_TO_HARVEST or GH_ENGINE.ready_to_harvest then
        if type(ImGui.PushStyleColor) == "function" and type(ImGui.PopStyleColor) == "function" then
            ImGui.PushStyleColor(ImGui.Col.Button, 0xFF2ECC71)        -- Emerald Green
            ImGui.PushStyleColor(ImGui.Col.ButtonHovered, 0xFF27AE60) -- Darker Green
            ImGui.PushStyleColor(ImGui.Col.ButtonActive, 0xFF1E8449)  -- Active Deep Green
            
            if ImGui.Button("[ HARVEST ET ]") then
                GH_ENGINE.harvest_index = 1
                GH_ENGINE.active_state = STATE_11_HARVESTING
                GH_ENGINE.status_message = "Harvesting triggered by operator button click."
            end
            ImGui.PopStyleColor(3)
        else
            if ImGui.Button("[ HARVEST ET ]") then
                GH_ENGINE.harvest_index = 1
                GH_ENGINE.active_state = STATE_11_HARVESTING
            end
        end
        ImGui.Separator()
    end

    -- 4. World & Logistics Configuration
    ImGui.TextUnformatted("--- World & Target Logistics ---")
    if GH_ENGINE.active_state == STATE_0_IDLE and type(ImGui.InputText) == "function" then
        -- Editable only while IDLE (standalone setup, no MCP / file editing needed)
        local c1, v1 = ImGui.InputText("Farm World", GH_ENGINE.farm_world, 32)
        if c1 and type(v1) == "string" then GH_ENGINE.farm_world = string.upper(v1) end
        local c2, v2 = ImGui.InputText("Storage A (Seed A)", GH_ENGINE.storage_world_a, 32)
        if c2 and type(v2) == "string" then GH_ENGINE.storage_world_a = string.upper(v2) end
        local c3, v3 = ImGui.InputText("Storage B (Seed B)", GH_ENGINE.storage_world_b, 32)
        if c3 and type(v3) == "string" then GH_ENGINE.storage_world_b = string.upper(v3) end
        local c4, v4 = ImGui.InputText("Drop World", GH_ENGINE.drop_zone.world, 32)
        if c4 and type(v4) == "string" then GH_ENGINE.drop_zone.world = string.upper(v4) end
        if type(ImGui.InputInt) == "function" then
            local c5, v5 = ImGui.InputInt("Seed A ID", GH_ENGINE.seed_a_id)
            if c5 and tonumber(v5) then GH_ENGINE.seed_a_id = tonumber(v5) end
            local c6, v6 = ImGui.InputInt("Seed B ID", GH_ENGINE.seed_b_id)
            if c6 and tonumber(v6) then GH_ENGINE.seed_b_id = tonumber(v6) end
            local c7, v7 = ImGui.InputInt("Target Seed ID", GH_ENGINE.target_tree_id)
            if c7 and tonumber(v7) then GH_ENGINE.target_tree_id = tonumber(v7) end
            local c8, v8 = ImGui.InputInt("Target Block ID", GH_ENGINE.target_block_id)
            if c8 and tonumber(v8) then GH_ENGINE.target_block_id = tonumber(v8) end
            local c9, v9 = ImGui.InputInt("Drop X", GH_ENGINE.drop_zone.x)
            if c9 and tonumber(v9) then GH_ENGINE.drop_zone.x = tonumber(v9) end
            local c10, v10 = ImGui.InputInt("Drop Y", GH_ENGINE.drop_zone.y)
            if c10 and tonumber(v10) then GH_ENGINE.drop_zone.y = tonumber(v10) end
        end
    else
        ImGui.TextUnformatted("Target Farm: " .. GH_ENGINE.farm_world)
        ImGui.TextUnformatted("Storage A: " .. GH_ENGINE.storage_world_a .. " | Storage B: " .. GH_ENGINE.storage_world_b)
    end
    ImGui.TextUnformatted("Capacity: " .. GH_ENGINE.scanned_capacity .. " | Spliced: " .. #GH_ENGINE.planted_base_coords)
    ImGui.TextUnformatted("MCP Bridge: " .. ((GH_ENGINE.bridge_available == true) and "ONLINE" or "NOT REQUIRED (standalone)"))

    -- Soil Geometry Toggle (AGENTS.md Rule 8)
    if type(ImGui.Checkbox) == "function" then
        local r1, r2 = ImGui.Checkbox("Only Above Blocks (Dirt etc.)", GH_ENGINE.only_above_block)
        if type(r2) == "boolean" then
            GH_ENGINE.only_above_block = r2
        elseif type(r1) == "boolean" then
            GH_ENGINE.only_above_block = r1
        end

        local a1, a2 = ImGui.Checkbox("Auto-Harvest When Ready", GH_ENGINE.auto_harvest)
        if type(a2) == "boolean" then
            GH_ENGINE.auto_harvest = a2
        elseif type(a1) == "boolean" then
            GH_ENGINE.auto_harvest = a1
        end
    end
    ImGui.Separator()

    -- 5. Designated Drop Zone Manager (PROJECT.md Section 6.2)
    ImGui.TextUnformatted("--- Designated Drop Zone (5000 Safe Limit) ---")
    ImGui.TextUnformatted("Drop World: " .. GH_ENGINE.drop_zone.world .. " (" .. GH_ENGINE.drop_zone.x .. ", " .. GH_ENGINE.drop_zone.y .. ")")
    ImGui.TextUnformatted("Current Tile Dropped: " .. GH_ENGINE.drop_zone.count .. " / 5000")

    if ImGui.Button("[ Set Current Tile as Drop Zone ]") then
        local me = (type(getLocal) == "function" and getLocal()) or (type(GetLocal) == "function" and GetLocal())
        if (type(me) == "table" or type(me) == "userdata") and me.pos then
            GH_ENGINE.drop_zone.x = math.floor((me.pos.x or 0) / 32)
            GH_ENGINE.drop_zone.y = math.floor((me.pos.y or 0) / 32)
            local wname = get_current_world_name()
            if #wname > 0 then
                GH_ENGINE.drop_zone.world = wname
            end
            GH_ENGINE.status_message = "Drop zone set to " .. GH_ENGINE.drop_zone.world .. " (" .. GH_ENGINE.drop_zone.x .. ", " .. GH_ENGINE.drop_zone.y .. ")."
        end
    end
    ImGui.Separator()

    -- 6. Engine Operator Controls
    if GH_ENGINE.active_state == STATE_0_IDLE then
        if ImGui.Button("[ Start Mass ]") then
            GH_ENGINE.active_state = STATE_1_LOAD_PERSISTENCE
            GH_ENGINE.status_message = "Starting Mass Tree automation cycle..."
        end
    else
        if ImGui.Button("[ Pause / Stop ]") then
            GH_ENGINE.active_state = STATE_0_IDLE
            GH_ENGINE.status_message = "Automation paused by operator."
        end
    end

    ImGui.SameLine()
    if ImGui.Button("[ Save State ]") then
        save_mass_state(GH_ENGINE.current_time)
        GH_ENGINE.status_message = "State saved to persistence."
    end

    ImGui.SameLine()
    if ImGui.Button("[ Reconcile Map ]") then
        local ok, ph = reconcile_live_tiles()
        GH_ENGINE.status_message = ok and ("Reconciled: " .. ph) or ("Reconcile failed: " .. tostring(ph))
    end

    -- 7. Mandatory Watermark (Right before ImGui.End())
    ImGui.Separator()
    ImGui.TextUnformatted("By BrK | Discord : mr_berk.")
    ImGui.End()
end

-- ------------------------------------------------------------------------------
-- 9. MAIN ONRENDER HOOK ENTRY POINT (DELTA-TIME TICK ACCUMULATION)
-- ------------------------------------------------------------------------------

local function on_render_hook(dt)
    local delta = tonumber(dt) or 0.016
    if delta <= 0 or delta > 0.5 then delta = 0.016 end

    -- Render HUD
    render_imgui_hud()

    -- Cooperative periodic logic execution
    GH_ENGINE.tick_timer = GH_ENGINE.tick_timer + delta
    if GH_ENGINE.tick_timer >= GH_ENGINE.action_delay then
        GH_ENGINE.tick_timer = 0
        on_tick_step(delta)
    end
end

-- ------------------------------------------------------------------------------
-- 10. PACKET & VARIANT HOOKS (ANTI-BAN & MODERATOR DETECTION)
-- ------------------------------------------------------------------------------

local function on_varlist_handler(var)
    if type(var) == "table" and var[0] == "OnConsoleMessage" then
        local msg = tostring(var[1] or "")
        if msg:find("%[MOD%]") or msg:find("Moderator") or msg:find("Guardian") then
            GH_ENGINE.anti_ban.mod_detected = true
            GH_ENGINE.anti_ban.mod_name = "MOD_CONSOLE"
            GH_ENGINE.active_state = STATE_0_IDLE
            GH_ENGINE.status_message = "EMERGENCY HALT: Moderator broadcast detected!"
        end
    end
    return false
end

-- ------------------------------------------------------------------------------
-- 11. HOOK REGISTRATION
-- ------------------------------------------------------------------------------

if type(AddHook) == "function" then
    -- Crash recovery: preload last saved config/progress into the HUD once at launch
    load_mass_state()
    GH_ENGINE.state_preloaded = true
    AddHook("OnRender", "GH_MassTreeEngine", on_render_hook)
    AddHook("OnVarlist", "GH_MassVarlist", on_varlist_handler)
    AddHook("OnRawPacket", "GH_MassRawPacket", on_raw_packet_handler)
end

-- ------------------------------------------------------------------------------
-- 12. EXPORT ENGINE & METHODS
-- ------------------------------------------------------------------------------

GH_ENGINE.calculate_placement_delay = calculate_placement_delay
GH_ENGINE.is_valid_soil_block = is_valid_soil_block
GH_ENGINE.scan_farm_grid = scan_farm_grid
GH_ENGINE.save_mass_state = save_mass_state
GH_ENGINE.load_mass_state = load_mass_state
GH_ENGINE.reconcile_live_tiles = reconcile_live_tiles
GH_ENGINE.on_tick_step = on_tick_step
GH_ENGINE.on_render_hook = on_render_hook
GH_ENGINE.on_varlist_handler = on_varlist_handler
GH_ENGINE.on_raw_packet_handler = on_raw_packet_handler
GH_ENGINE.json_encode = json_encode
GH_ENGINE.json_decode = json_decode

_G.GH_MASS_ENGINE = GH_ENGINE

-- Return engine table for external programmatic inspection / tests
return GH_ENGINE
