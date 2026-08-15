-- ArchipelagoWoW: Zones.lua
-- Static lookup table grouping known WoW zone "item names" (as granted by the
-- Archipelago server) into continent/expansion buckets for the Zones/Progress
-- panel. The exact item name strings below (including level-range suffixes
-- and the separate Pre-Cataclysm/Post-Cataclysm variants of the same zone)
-- are taken verbatim from this project's own AP world data at
-- worlds/wow_leveling/data/items.json (category "Zones"), so this table
-- matches what the server will actually grant rather than being a guess.
-- Anything NOT recognized here (a differently-worded item name, a future
-- world revision, etc.) simply falls into the "Other/Ungrouped" bucket
-- instead of erroring.

local ADDON_NAME, APW = ...

APW.Zones = APW.Zones or {}
local Zones = APW.Zones

Zones.OTHER_BUCKET = "Other/Ungrouped"

Zones.CATEGORY_ORDER = {
    "Eastern Kingdoms",
    "Kalimdor",
    "Outland",
    "Northrend",
    "Cataclysm Eastern Kingdoms",
    "Cataclysm Kalimdor",
    "Pandaria",
    Zones.OTHER_BUCKET,
}

-- zone item name (exact string granted by the AP server) -> continent/expansion bucket.
-- Pre-Cataclysm and Post-Cataclysm level-range variants of the same physical zone are
-- kept in the same continent bucket (they're the same place); "Cataclysm Eastern
-- Kingdoms"/"Cataclysm Kalimdor" are reserved for the zones that are genuinely new in
-- Cataclysm (Mount Hyjal, Vashj'ir, Deepholm, Uldum, Twilight Highlands).
Zones.ZONE_TO_CATEGORY = {
    -- Eastern Kingdoms
    ["Ghostlands (10-20)"] = "Eastern Kingdoms",
    ["Westfall (10-15)"] = "Eastern Kingdoms",
    ["Westfall (10-20)"] = "Eastern Kingdoms",
    ["Loch Modan (10-20)"] = "Eastern Kingdoms",
    ["Silverpine Forest (10-20)"] = "Eastern Kingdoms",
    ["Redridge Mountains (15-20)"] = "Eastern Kingdoms",
    ["Redridge Mountains (15-25)"] = "Eastern Kingdoms",
    ["Hillsbrad Foothills (20-25)"] = "Eastern Kingdoms",
    ["Hillsbrad Foothills (20-30)"] = "Eastern Kingdoms",
    ["Alterac Mountains (30-40)"] = "Eastern Kingdoms",
    ["Duskwood (20-25)"] = "Eastern Kingdoms",
    ["Duskwood (18-30)"] = "Eastern Kingdoms",
    ["Wetlands (20-25)"] = "Eastern Kingdoms",
    ["Wetlands (20-30)"] = "Eastern Kingdoms",
    ["Arathi Highlands (25-30)"] = "Eastern Kingdoms",
    ["Arathi Highlands (30-40)"] = "Eastern Kingdoms",
    ["Northern Stranglethorn (25-30)"] = "Eastern Kingdoms",
    ["Stranglethorn Vale (30-45)"] = "Eastern Kingdoms",
    ["The Cape of Stranglethorn (30-35)"] = "Eastern Kingdoms",
    ["The Hinterlands (30-35)"] = "Eastern Kingdoms",
    ["The Hinterlands (40-50)"] = "Eastern Kingdoms",
    ["Western Plaguelands (51-58)"] = "Eastern Kingdoms",
    ["Western Plaguelands (35-40)"] = "Eastern Kingdoms",
    ["Eastern Plaguelands (40-45)"] = "Eastern Kingdoms",
    ["Eastern Plaguelands (53-60)"] = "Eastern Kingdoms",
    ["Badlands (44-48)"] = "Eastern Kingdoms",
    ["Badlands (36-45)"] = "Eastern Kingdoms",
    ["Searing Gorge (47-51)"] = "Eastern Kingdoms",
    ["Searing Gorge (43-50)"] = "Eastern Kingdoms",
    ["Burning Steppes (49-52)"] = "Eastern Kingdoms",
    ["Burning Steppes (50-58)"] = "Eastern Kingdoms",
    ["Swamp of Sorrows (52-54)"] = "Eastern Kingdoms",
    ["Swamp of Sorrows (35-45)"] = "Eastern Kingdoms",
    ["Blasted Lands (54-60)"] = "Eastern Kingdoms",
    ["Blasted Lands (45-55)"] = "Eastern Kingdoms",

    -- Kalimdor
    ["Bloodmyst Isle (10-20)"] = "Kalimdor",
    ["Darkshore (10-20)"] = "Kalimdor",
    ["Azshara (45-55)"] = "Kalimdor",
    ["Azshara (10-20)"] = "Kalimdor",
    ["Northern Barrens (10-20)"] = "Kalimdor",
    ["The Barrens (10-25)"] = "Kalimdor",
    ["Ashenvale (20-25)"] = "Kalimdor",
    ["Ashenvale (20-30)"] = "Kalimdor",
    ["Stonetalon Mountains (25-30)"] = "Kalimdor",
    ["Stonetalon Mountains (15-25)"] = "Kalimdor",
    ["Desolace (30-35)"] = "Kalimdor",
    ["Desolace (30-40)"] = "Kalimdor",
    ["Southern Barrens (30-35)"] = "Kalimdor",
    ["Dustwallow Marsh (35-40)"] = "Kalimdor",
    ["Dustwallow Marsh (35-45)"] = "Kalimdor",
    ["Feralas (35-40)"] = "Kalimdor",
    ["Feralas (40-50)"] = "Kalimdor",
    ["Thousand Needles (40-45)"] = "Kalimdor",
    ["Thousand Needles (25-35)"] = "Kalimdor",
    ["Felwood (45-50)"] = "Kalimdor",
    ["Felwood (48-55)"] = "Kalimdor",
    ["Tanaris (45-50)"] = "Kalimdor",
    ["Tanaris (40-50)"] = "Kalimdor",
    ["Un'Goro Crater (50-55)"] = "Kalimdor",
    ["Winterspring (50-55)"] = "Kalimdor",
    ["Winterspring (55-60)"] = "Kalimdor",
    ["Silithus (55-60)"] = "Kalimdor",

    -- Outland (The Burning Crusade)
    ["Hellfire Peninsula (58-63)"] = "Outland",
    ["Zangarmarsh (60-64)"] = "Outland",
    ["Terokkar Forest (62-65)"] = "Outland",
    ["Nagrand (64-67)"] = "Outland",
    ["Blade's Edge Mountains (65-68)"] = "Outland",
    ["Shadowmoon Valley (67-70)"] = "Outland",
    ["Netherstorm (67-70)"] = "Outland",

    -- Northrend (Wrath of the Lich King)
    ["Borean Tundra (68-72)"] = "Northrend",
    ["Howling Fjord (68-72)"] = "Northrend",
    ["Dragonblight (71-75)"] = "Northrend",
    ["Grizzly Hills (73-75)"] = "Northrend",
    ["Zul'Drak (74-76)"] = "Northrend",
    ["Sholazar Basin (76-78)"] = "Northrend",
    ["Crystalsong Forest (77-80)"] = "Northrend",
    ["Icecrown (77-80)"] = "Northrend",
    ["The Storm Peaks (77-80)"] = "Northrend",

    -- New-in-Cataclysm zones
    ["Mount Hyjal (80-82)"] = "Cataclysm Kalimdor",
    ["Vashj'ir (80-82)"] = "Cataclysm Kalimdor",
    ["Deepholm (82-83)"] = "Cataclysm Kalimdor",
    ["Uldum (83-84)"] = "Cataclysm Kalimdor",
    ["Twilight Highlands (84-85)"] = "Cataclysm Eastern Kingdoms",

    -- Pandaria (Mists of Pandaria)
    ["The Jade Forest (85-86)"] = "Pandaria",
    ["Krasarang Wilds (86-87)"] = "Pandaria",
    ["Valley of the Four Winds (86-87)"] = "Pandaria",
    ["Kun-Lai Summit (87-88)"] = "Pandaria",
    ["Townlong Steppes (88-89)"] = "Pandaria",
    ["Dread Wastes (89-90)"] = "Pandaria",
}

function Zones.GetCategory(itemName)
    return Zones.ZONE_TO_CATEGORY[itemName] or Zones.OTHER_BUCKET
end

-- Groups a map[itemName]=true table into an ordered array of
-- { category = <string>, items = { <sorted item names> } }, skipping
-- categories with no unlocked items.
function Zones.GroupUnlocked(unlockedMap)
    local buckets = {}
    for _, cat in ipairs(Zones.CATEGORY_ORDER) do
        buckets[cat] = {}
    end

    for itemName, unlocked in pairs(unlockedMap or {}) do
        if unlocked then
            local cat = Zones.GetCategory(itemName)
            if not buckets[cat] then
                buckets[cat] = {}
            end
            table.insert(buckets[cat], itemName)
        end
    end

    local result = {}
    for _, cat in ipairs(Zones.CATEGORY_ORDER) do
        local items = buckets[cat]
        if items and #items > 0 then
            table.sort(items)
            table.insert(result, { category = cat, items = items })
        end
    end
    return result
end
