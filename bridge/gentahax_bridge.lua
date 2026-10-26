--[[
  GENTAHAX MCP BRIDGE — mr_berk edition
  =====================================
  Bu script GENTAHAX Lua motorunun İÇİNDE sürekli çalışan bir bekçi thread'idir.
  Python (MCP) tarafı bridge_in.txt yazar, bu köprü okuyup çalıştırır ve
  sonucu bridge_out.txt'ye yazar. Böylece AI gerçek zamanlı oyun verisi
  okuyabilir ve kod çalıştırabilir.

  KURULUM:
    1) Bu dosyayı GENTAHAX Script klasörüne koyun
       (Windows: GENTAHAX kurulu dizin/Script/ — Android: Android/media/GENTAHAX/Script/)
    2) GENTAHAX menüde Lua Executor → gentahax_bridge.lua → Execute
    3) Hepsi bu! MCP tarafı gh_device_status ile doğrulayabilir.

  NOT: io kütüphanesi kapalı bir build'de çalışmaz; bu durumda
       bridge_out.txt oluşmaz ve MCP tarafı zaman aşımı verir.
]]

local IN_FILE  = "bridge_in.txt"
local OUT_FILE = "bridge_out.txt"
local BRIDGE_ID = "mcp_bridge_mr_berk"

-- Güvenli dosya yazma (append)
local function bridge_append(text)
    local f = io.open(OUT_FILE, "a")
    if not f then return false end
    f:write(text, "\n")
    f:close()
    return true
end

-- Komut işleyici: ID|EXEC\n<lua kodu>
local function handle_command(content)
    local cmd_id, action, code = content:match("^(%x+)|(%a+)\n(.*)$")
    if not cmd_id then
        -- eski uyumsuz format
        return false
    end

    if action == "EXEC" then
        local chunk, err = load(code, "mcp_chunk", "t", _G)
        if not chunk then
            bridge_append(cmd_id .. "|ERR|" .. tostring(err))
            return true
        end
        local ok, r1, r2, r3, r4 = pcall(chunk)
        if ok then
            local parts = {}
            for _, v in ipairs({r1, r2, r3, r4}) do
                if v ~= nil then parts[#parts + 1] = tostring(v) end
            end
            local out = table.concat(parts, " \t ")
            if out == "" then out = "OK" end
            bridge_append(cmd_id .. "|OK|" .. out)
        else
            bridge_append(cmd_id .. "|ERR|" .. tostring(r1))
        end
        return true
    elseif action == "STOP" then
        RemoveHooks()
        killAllThread()
        bridge_append(cmd_id .. "|OK|durduruldu")
        return true
    end
    return false
end

-- Ana bekçi thread
runThread(function()
    -- başlangıç sinyali
    bridge_append("0|OK|BRIDGE_READY mr_berk")
    logToConsole("[MCP BRIDGE] mr_berk köprüsü hazır — Python tarafını bekliyor")

    while true do
        sleep(250)
        local ok, err = pcall(function()
            local f = io.open(IN_FILE, "r")
            if not f then return end
            local content = f:read("*a")
            f:close()
            os.remove(IN_FILE)
            if content and #content > 0 then
                handle_command(content)
            end
        end)
        if not ok then
            -- hata durumunda çökme değil, bildirim
            pcall(function()
                bridge_append("0|ERR|bridge_loop:" .. tostring(err))
            end)
        end
    end
end, BRIDGE_ID)

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
        out[#out + 1] = string.format("%s[netID=%s,country=%s,gems=%s,pos=%s,%s]",
            tostring(p.name), tostring(p.netId), tostring(p.country),
            tostring(p.gems), tostring(p.pos.x) .. "," .. tostring(p.pos.y),
            tostring(p.ping) .. "ms")
    end
    return table.concat(out, " ; ")
end

function mcp_inventory_dump()
    local out = {}
    for _, item in pairs(getInventory()) do
        local info = getItemByID(item.id)
        out[#out + 1] = string.format("%s(id=%d) x%d",
            info and info.name or "?", item.id, item.amount)
    end
    return table.concat(out, ", ")
end

-- v1.1 (mr_berk): DÜNYA EŞYA SAYIMI — 'kac tane X var?' sorusuna GERÇEK cevap
-- getTile() vektörünü tarar; sadece OKUR, paket gonderilmez, ban riski yoktur.
function mcp_world_item_counts(ids_csv)
    local w = getWorld()
    if not w then return "ERR|NO_WORLD" end
    local want = {}
    for id in tostring(ids_csv):gmatch("%d+") do
        want[tonumber(id)] = { fg = 0, bg = 0 }
    end
    local total = 0
    for _, t in pairs(getTile()) do
        if t and t.fg ~= nil then
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

-- v1.1 (mr_berk): DÜNYA SAYIMI — tüm esyalari fg/bg adetine göre listeler
function mcp_world_census()
    local w = getWorld()
    if not w then return "ERR|NO_WORLD" end
    local fgc, bgc, total = {}, {}, 0
    for _, t in pairs(getTile()) do
        if t and t.fg ~= nil then
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

logToConsole("[MCP BRIDGE] kurulum tamam — mr_berk v1.1 (item sayimi hazir)")
