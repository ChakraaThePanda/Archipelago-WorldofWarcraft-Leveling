-- ArchipelagoWoW: Stats.lua
-- Statistics-tab milestone checks (the include_achievements option). The bridge lists
-- this slot's milestones in ArchipelagoWoW_BridgeDB.statChecks ({ name, stat, threshold });
-- any whose GetStatistic(stat) has reached its threshold is queued into
-- pendingStatChecks for the next sync, the same way levels are queued into pendingChecks.
-- A string stat names a value computed here instead (see COMPUTED_STATS).
--
-- GetStatistic and the CRITERIA_UPDATE event only exist on clients with achievements
-- (Wrath of the Lich King or newer). On Classic Era and Burning Crusade Classic this whole
-- file does nothing, which is why include_achievements' option text says it needs Wrath
-- of the Lich King or newer.

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

-- Achievement category "Exploration"; its subcategories hold each continent's zones.
local EXPLORATION_CATEGORY = 97
-- Criteria type of "explore this area" criteria. A zone's "Explore X" achievement is made
-- only of those, which tells it apart from the metas ("Explore Kalimdor") and the rare-kill
-- achievements in the same categories, in any client language.
local CRITERIA_TYPE_EXPLORE_AREA = 43

-- Every zone exploration achievement id. Found once: the list never changes in a session
-- (an empty result isn't kept, in case it was asked for before the client was ready).
local zoneExplorationIds

local function findZoneExplorationIds()
    local ids = {}
    local categories = { EXPLORATION_CATEGORY }
    for _, category in ipairs(GetCategoryList()) do
        local _, parent = GetCategoryInfo(category)
        if parent == EXPLORATION_CATEGORY then
            table.insert(categories, category)
        end
    end
    for _, category in ipairs(categories) do
        for index = 1, GetCategoryNumAchievements(category, true) do
            local id = GetAchievementInfo(category, index)
            if id and GetAchievementNumCriteria(id) > 0
                and select(2, GetAchievementCriteriaInfo(id, 1)) == CRITERIA_TYPE_EXPLORE_AREA then
                table.insert(ids, id)
            end
        end
    end
    return ids
end

-- Zone exploration achievements this character has earned. From MoP on, achievements are
-- account-wide, so one earned only by another character (wasEarnedByMe false) doesn't count.
local function countZonesExplored()
    if not zoneExplorationIds then
        local ids = findZoneExplorationIds()
        if table.getn(ids) == 0 then
            return 0
        end
        zoneExplorationIds = ids
    end
    local count = 0
    for _, id in ipairs(zoneExplorationIds) do
        local _, _, _, completed, _, _, _, _, _, _, _, _, wasEarnedByMe = GetAchievementInfo(id)
        if completed and wasEarnedByMe ~= false then
            count = count + 1
        end
    end
    return count
end

local COMPUTED_STATS = {
    zonesExplored = countZonesExplored,
}

local function statValue(stat)
    if type(stat) == "string" then
        local compute = COMPUTED_STATS[stat]
        return compute and compute() or 0
    end
    return Stats.ParseStatistic(GetStatistic(stat))
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
            and statValue(check.stat) >= check.threshold then
            table.insert(db.pendingStatChecks, name)
            Core.AddLog(string.format("Queued \"%s\" to send on next sync", name))
            queued = true
        end
    end
    return queued
end

-- PLAYER_ENTERING_WORLD comes after Core's PLAYER_LOGIN reconcile, so acked milestones are
-- already dropped by then. CRITERIA_UPDATE fires whenever any statistic changes, and
-- ACHIEVEMENT_EARNED when a zone's exploration achievement completes.
if GetStatistic ~= nil then
    local eventFrame = CreateFrame("Frame")
    eventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
    eventFrame:RegisterEvent("CRITERIA_UPDATE")
    eventFrame:RegisterEvent("ACHIEVEMENT_EARNED")
    eventFrame:SetScript("OnEvent", function()
        if Stats.Scan() and APW.UI and APW.UI.RefreshAll then
            APW.UI.RefreshAll()
        end
    end)
end
