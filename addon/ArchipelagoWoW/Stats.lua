-- ArchipelagoWoW: Stats.lua
-- Statistics-tab milestone checks (the include_achievements option). The bridge lists
-- this slot's milestones in ArchipelagoWoW_BridgeDB.statChecks ({ name, stat, threshold });
-- any whose GetStatistic(stat) has reached its threshold is queued into
-- pendingStatChecks for the next sync, the same way levels are queued into pendingChecks.
--
-- GetStatistic and the CRITERIA_UPDATE event only exist from Wrath (3.0.2) onward. On older
-- clients this whole file does nothing, which is why include_achievements' option text
-- says it needs a Wrath-or-later client.

local APW = ArchipelagoWoW

APW.Stats = APW.Stats or {}
local Stats = APW.Stats
local Core = APW.Core

-- GetStatistic returns display text, not a number: a plain count ("123"), "--" before
-- the first one, or for money stats each coin amount followed by its coin icon texture
-- ("12|TInterface\\MoneyFrame\\UI-GoldIcon:0:0:2:0|t 34|T...UI-SilverIcon...|t ...").
local COIN_COPPER = { GoldIcon = 10000, SilverIcon = 100, CopperIcon = 1 }

-- Returns a statistic's value as a number (copper, for money statistics), or 0 if it has
-- none yet. The coin pattern only allows non-digits between an amount and its icon name,
-- so it can't pick up the digits inside a previous icon's texture size arguments.
function Stats.ParseStatistic(text)
    if text == nil then
        return 0
    end
    text = tostring(text)
    local plain = tonumber((string.gsub(text, ",", "")))
    if plain then
        return plain
    end
    local total = 0
    for icon, copper in pairs(COIN_COPPER) do
        local _, _, amount = string.find(text, "(%d+)[^%d]-" .. icon)
        if amount then
            total = total + tonumber(amount) * copper
        end
    end
    return total
end

local function isPendingStat(db, name)
    for _, existing in ipairs(db.pendingStatChecks) do
        if existing == name then
            return true
        end
    end
    return false
end

-- Queues every listed milestone that's been reached and isn't already pending or acked.
-- Returns true if anything new was queued.
function Stats.Scan()
    if GetStatistic == nil then
        return false
    end
    local db = ArchipelagoWoWDB
    local bridge = ArchipelagoWoW_BridgeDB
    if not db or not bridge then
        return false
    end

    local queued = false
    for _, check in ipairs(bridge.statChecks) do
        local name = check.name
        if name and check.stat and check.threshold
            and not bridge.ackedStats[name] and not isPendingStat(db, name)
            and Stats.ParseStatistic(GetStatistic(check.stat)) >= check.threshold then
            table.insert(db.pendingStatChecks, name)
            Core.AddLog(string.format("Queued \"%s\" to send on next sync", name))
            queued = true
        end
    end
    return queued
end

-- PLAYER_ENTERING_WORLD comes after Core's PLAYER_LOGIN reconcile, so acked milestones are
-- already dropped by then. CRITERIA_UPDATE fires whenever any statistic changes.
if GetStatistic ~= nil then
    local eventFrame = CreateFrame("Frame")
    eventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
    eventFrame:RegisterEvent("CRITERIA_UPDATE")
    eventFrame:SetScript("OnEvent", function()
        if Stats.Scan() and APW.UI and APW.UI.RefreshAll then
            APW.UI.RefreshAll()
        end
    end)
end
