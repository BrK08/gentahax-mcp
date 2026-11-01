--[[
  GENTAHAX MCP — Oyun İçi Köprü (Hibrit: Dosya IPC + HTTP Relay Fallback)
  mr_berk edition v2.3 (Single-Thread OnRender Mimari — Sıfır Stack Çarpışması & Sıfır Crash)

  NEDEN OnRender MİMARİSİ?
  GENTAHAX C++ motorunda runThread() ayrı bir OS thread'i açar ancak OnRender (SwapBuffers)
  ile aynı lua_State* stack'ini mutex olmadan paylaşır. İkisi aynı anda çalışırsa
  "[Render Hook] error: error in error handling" ve SIGSEGV (oyundan atma) oluşur.
  Bu köprü v2.3'te tamamen OnRender tick zamanlayıcısı üzerinde (tek thread'de) çalışır;
  böylece ImGui scriptleriyle ASLA çakışmaz ve oyundan atmaz!

  KURULUM:
  1) GENTAHAX menüden Lua Executor'da (</>) gentahax_bridge.lua seçip çalıştırın (▶).
  2) Veya tek satırlık yükleyiciyi yapıştırıp çalıştırın:
     load(makeRequest("http://127.0.0.1:8809/bridge.lua","GET",{},"",5000).content)()
]]

local IN_FILE   = "bridge_in.txt"
local OUT_FILE  = "bridge_out.txt"
local RELAY     = "http://127.0.0.1:8809"
local BRIDGE_ID = "mcp_bridge_mr_berk"
local HAS_IO    = (type(io) == "table" and type(io.open) == "function")

-- RemoveHooks çağrıldığında köprü hook'unu koru
if type(RemoveHook) == "function" and not _G._GH_RMHOOKS_WRAPPED then
    _G._GH_RMHOOKS_WRAPPED = true
    _G._GH_RAW_REMOVEHOOK  = RemoveHook
    _G._GH_RAW_REMOVEHOOKS = RemoveHooks
    _G._GH_ACTIVE_HOOKS    = {}

    local orig_add = AddHook
    AddHook = function(ev, label, fn)
        local lbl = tostring(label or "unnamed")
        if lbl ~= BRIDGE_ID then
            _G._GH_ACTIVE_HOOKS[lbl] = true
        end
        return orig_add(ev, lbl, fn)
    end

    RemoveHooks = function()
        for lbl, _ in pairs(_G._GH_ACTIVE_HOOKS or {}) do
            if lbl ~= BRIDGE_ID then
                _G._GH_RAW_REMOVEHOOK(lbl)
            end
        end
        _G._GH_ACTIVE_HOOKS = {}
    end
end

-- Çıktı gönderme (io açıksa dosyaya append, kapalıysa HTTP relay'e POST)
local function bridge_append(text)
    if HAS_IO then
        local f = io.open(OUT_FILE, "a")
        if f then
            f:write(text, "\n")
            f:close()
            return true
        end
    end
    if type(makeRequest) == "function" then
        makeRequest(RELAY .. "/out", "POST", {"Content-Type: text/plain; charset=utf-8"}, tostring(text), 1500)
        return true
    end
    return false
end

-- Komut okuma (io açıksa dosyadan, kapalıysa HTTP relay'den GET)
local function bridge_poll_in()
    if HAS_IO then
        local f = io.open(IN_FILE, "r")
        if f then
            local content = f:read("*a")
            f:close()
            if type(os) == "table" and type(os.remove) == "function" then
                os.remove(IN_FILE)
            end
            if content and #content > 0 then
                return content:gsub("\r\n", "\n")
            end
        end
    end
    if type(makeRequest) == "function" then
        local resp = makeRequest(RELAY .. "/in", "GET", {}, "", 1500)
        if (type(resp) == "table" or type(resp) == "userdata") and resp.content and #resp.content > 0 then
            return resp.content:gsub("\r\n", "\n")
        end
    end
    return nil
end

-- Komut işleyici: ID|EXEC\n<lua kodu>
local function handle_command(content)
    local cmd_id, action, code = content:match("^(%x+)|(%a+)\n(.*)$")
    if not cmd_id then
        return false
    end

    if action == "EXEC" then
        local chunk, err = load(code, "mcp_chunk", "t", _G)
        if not chunk then
            bridge_append(cmd_id .. "|ERR|" .. tostring(err))
            return true
        end
        local r1, r2, r3, r4 = chunk()
        local parts = {}
        for _, v in ipairs({r1, r2, r3, r4}) do
            if v ~= nil then parts[#parts + 1] = tostring(v) end
        end
        local out = table.concat(parts, " \t ")
        if out == "" then out = "OK" end
        bridge_append(cmd_id .. "|OK|" .. out)
        return true
    elseif action == "STOP" then
        RemoveHooks()
        if type(killAllThread) == "function" then
            killAllThread()
        end
        bridge_append(cmd_id .. "|OK|durduruldu")
        return true
    end
    return false
end

-- Kullanışlı hazır sorgular (MCP bunları EXEC ile çağırır)
function mcp_world_snapshot()
    local w = getWorld()
    if not w then return "Dunya yok (menude olabilirsin)" end
    local me = getLocal()
    local players = #getPlayerlist()
    local objs = #getWorldObject()
    return string.format(
        "WORLD:%s|SIZE:%dx%d|ME:%s|GEMS:%d|POS:%s|PLAYERS:%d|DROPS:%d",
        tostring(w.name), w.width, w.height,
        me and me.name or "?", me and me.gems or 0,
        me and (me.pos.x .. "," .. me.pos.y) or "?",
        players, objs
    )
end

function mcp_player_info()
    local list = getPlayerlist()
    local out = {}
    for i, p in pairs(list) do
        if type(p) == "table" or type(p) == "userdata" then
            out[#out + 1] = string.format("%s[netID=%s,country=%s,gems=%s,pos=%s,%s]",
                tostring(p.name), tostring(p.netId), tostring(p.country),
                tostring(p.gems), tostring(p.pos and p.pos.x or "?") .. "," .. tostring(p.pos and p.pos.y or "?"),
                tostring(p.ping) .. "ms")
        end
    end
    return table.concat(out, " ; ")
end

function mcp_inventory_dump()
    local out = {}
    for _, item in pairs(getInventory()) do
        if (type(item) == "table" or type(item) == "userdata") and item.id then
            local info = getItemByID(item.id)
            out[#out + 1] = string.format("%s(id=%d) x%d",
                info and info.name or "?", item.id, item.amount or 0)
        end
    end
    return table.concat(out, ", ")
end

function mcp_world_item_counts(ids_csv)
    local w = getWorld()
    if not w then return "ERR|NO_WORLD" end
    local want = {}
    for id in tostring(ids_csv):gmatch("%d+") do
        want[tonumber(id)] = { fg = 0, bg = 0 }
    end
    local total = 0
    for _, t in pairs(getTile()) do
        if (type(t) == "table" or type(t) == "userdata") and t.fg ~= nil then
            total = total + 1
            if want[t.fg] then want[t.fg].fg = want[t.fg].fg + 1 end
            if want[t.bg] then want[t.bg].bg = want[t.bg].bg + 1 end
        end
    end
    local out = {}
    for id, c in pairs(want) do
        out[#out + 1] = string.format("%d=%d/%d", id, c.fg, c.bg)
    end
    table.sort(out)
    return string.format("WORLD:%s|SIZE:%dx%d|TILES:%d|COUNTS:%s",
        tostring(w.name), w.width, w.height, total, table.concat(out, ";"))
end

function mcp_world_census()
    local w = getWorld()
    if not w then return "ERR|NO_WORLD" end
    local fgc, bgc, total = {}, {}, 0
    for _, t in pairs(getTile()) do
        if (type(t) == "table" or type(t) == "userdata") and t.fg ~= nil then
            total = total + 1
            if t.fg and t.fg > 0 then fgc[t.fg] = (fgc[t.fg] or 0) + 1 end
            if t.bg and t.bg > 0 then bgc[t.bg] = (bgc[t.bg] or 0) + 1 end
        end
    end
    local function top(c)
        local a = {}
        for id, n in pairs(c) do a[#a + 1] = { id, n } end
        table.sort(a, function(x, y) return x[2] > y[2] end)
        local o = {}
        for i = 1, math.min(#a, 20) do
            local it = getItemByID(a[i][1])
            o[#o + 1] = tostring(a[i][1]) .. "=" .. tostring(it and it.name or "?") .. " x" .. tostring(a[i][2])
        end
        return table.concat(o, ";")
    end
    local function n(c) local m = 0 for _ in pairs(c) do m = m + 1 end return m end
    return string.format("WORLD:%s|SIZE:%dx%d|TILES:%d|DISTINCT_FG:%d|DISTINCT_BG:%d|TOP_FG:%s|TOP_BG:%s",
        tostring(w.name), w.width, w.height, total, n(fgc), n(bgc), top(fgc), top(bgc))
end

-- Tek-Thread OnRender Köprü Döngüsü (Her 0.75 saniyede bir yoklar, asla stack çakışması yapmaz)
if type(RemoveHook) == "function" then
    RemoveHook(BRIDGE_ID)
end

local poll_timer = 0
local first_ready_sent = false

AddHook("OnRender", BRIDGE_ID, function(dt)
    if not first_ready_sent then
        first_ready_sent = true
        bridge_append("0|OK|BRIDGE_READY mr_berk v2.3")
        logToConsole("[MCP BRIDGE] mr_berk v2.3 (Single-Thread OnRender) hazir!")
        if type(doToast) == "function" then
            doToast("GentaHAX MCP Bridge v2.3 Active")
        end
    end

    poll_timer = poll_timer + (tonumber(dt) or 0.016)
    if poll_timer >= 0.75 then
        poll_timer = 0
        local content = bridge_poll_in()
        if content and #content > 0 then
            handle_command(content)
        end
    end
end)
