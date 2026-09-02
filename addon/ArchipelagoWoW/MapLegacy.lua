-- ArchipelagoWoW: MapLegacy.lua
-- Legacy-client counterpart to Map.lua -- see Map.lua's header for what this feature does
-- and why it exists. This file is the implementation for a genuine pre-Legion (original
-- 3.3.5-era) client: it predates C_Map/the MapCanvas pin system entirely (confirmed
-- against the actual 2010 FrameXML/WorldMapFrame.lua source, not assumed), so Map.lua
-- no-ops there and this file does the work instead. On any client where the modern API
-- exists (including Blizzard's own 2022+ Wrath Classic rerelease, which -- unlike a
-- genuine 3.3.5 client -- runs on that same modern engine), this file no-ops instead.
--
-- The old client's per-zone shaped highlight art still exists (it's the same asset
-- family the modern client uses), but there's no API to look a zone up by name/index and
-- get its position on the continent map -- only a native, purely coordinate-driven
-- lookup, UpdateMapHighlight(x, y), which returns whichever zone's shape contains that
-- point (this is exactly what drives the live mouse-hover highlight in
-- WorldMapButton_OnUpdate, FrameXML/WorldMapFrame.lua, on the real client). So instead of
-- a seed point per zone -- which nothing on this client can produce without a hand-authored
-- coordinate table -- this scans a grid of points across the currently-displayed
-- continent once, discovers which zone each point falls in, and caches the shape data by
-- zone name. No hardcoded coordinates, still exactly Blizzard's own shape art, just found
-- by brute-force instead of a lookup call. Cached per continent so re-visiting one later
-- in the same session doesn't rescan.
--
-- Known, accepted limitation: a handful of zones' own highlight art is a small glow near
-- the zone's label rather than something covering the whole zone (Storm Peaks, Crystalsong
-- Forest, Icecrown, Dragonblight, Zul'Drak confirmed live on Northrend), so those don't get
-- tinted at all. Tried three alternatives that derived a shape purely from the grid scan
-- instead of reusing this art, all confirmed live to look worse:
--   1. One bounding rectangle per zone (per-zone min/max over the whole scan). Diagonally-
--      arranged zones' boxes overlap each other so much they fuse into one giant blob,
--      swallowing zone borders entirely.
--   2. One rectangle per scan row (per-row min/max instead of per-zone). Still broken for
--      the same underlying reason: summarizing a row into one span bridges straight across
--      any concave notch/bay in the zone's real shape, painting area that isn't really
--      part of it -- including bleeding into a neighbor.
--   3. One small tile per individual grid point (no summarizing at all -- a raster "pixel"
--      fill). Traced shapes correctly, including concave ones, but reads as a busy,
--      checkerboard-looking texture rather than a clean tint.
-- Reverted back to reusing Blizzard's own highlight art on purpose, preferring
-- partial-but-clean coverage over complete-but-messy. Do not re-attempt those three
-- without new information that changes the trade-off.

local ADDON_NAME, APW = ...

if APW.Compat.HasModernMapAPI then return end

local Zones = APW.Zones

-- Roughly one sample every this many pixels of the currently-displayed map. Confirmed
-- live at 24px that some real zones (Ashenvale, Duskwood) are narrow/irregular enough to
-- fall entirely between sample points and never get discovered at all; 12px fixed those.
local SAMPLE_SPACING_PX = 12

-- continentID -> zoneName -> { fileName, texPercentageX, texPercentageY, textureX,
-- textureY, scrollChildX, scrollChildY } -- exactly the shape of UpdateMapHighlight's
-- return values (minus the name itself), one entry per zone actually found on that
-- continent this session.
local shapeCacheByContinent = {}

local function ScanContinent(continentID)
    local width, height = WorldMapDetailFrame:GetWidth(), WorldMapDetailFrame:GetHeight()
    -- Not cached: a continent scanned too early (before its map texture/layout has
    -- actually settled, e.g. the very first WORLD_MAP_UPDATE after switching to it) can
    -- come back with a 0-size frame or zero zones found, and caching that empty result
    -- would permanently disable the overlay for that continent instead of just trying
    -- again on the next refresh.
    if not width or width == 0 or not height or height == 0 then return {} end

    local cache = {}
    local stepsX = math.max(1, math.floor(width / SAMPLE_SPACING_PX))
    local stepsY = math.max(1, math.floor(height / SAMPLE_SPACING_PX))

    for i = 0, stepsX do
        local gx = i / stepsX
        for j = 0, stepsY do
            local gy = j / stepsY
            local name, fileName, texPercentageX, texPercentageY, textureX, textureY, scrollChildX, scrollChildY = UpdateMapHighlight(gx, gy)
            if name and fileName and not cache[name] then
                cache[name] = {
                    fileName = fileName,
                    texPercentageX = texPercentageX,
                    texPercentageY = texPercentageY,
                    textureX = textureX,
                    textureY = textureY,
                    scrollChildX = scrollChildX,
                    scrollChildY = scrollChildY,
                }
            end
        end
    end

    if next(cache) then
        shapeCacheByContinent[continentID] = cache
    end

    return cache
end

-- ---------------------------------------------------------------------------
-- A small growing pool of plain textures parented to WorldMapDetailFrame -- there's no
-- pin/data-provider system on this client generation, so this is just SetTexture/Show/
-- Hide on a handful of reused Texture objects, the same technique Blizzard's own
-- WorldMapHighlight uses for the live mouse-hover version (FrameXML/WorldMapFrame.xml),
-- just N of them at once instead of one that follows the cursor.
-- ---------------------------------------------------------------------------

-- The highlight art itself is a dim additive glow by design (a subtle mouseover cue, not
-- meant to read as a bold wash on its own), and it has an opaque black background rather
-- than a real alpha cutout -- confirmed live: BLEND painted that background as a solid
-- black box. ADD is correct (the black background truly contributes nothing); this
-- stacks STACK_SIZE identical ADD copies per locked zone to make the red read boldly
-- without ever risking that box. Confirmed live that 3 reads clearly on Kalimdor/Eastern
-- Kingdoms' warm palette but stays faint on Northrend's cooler ice/snow tones -- doubled
-- since more ADD layers is a pure, safe brightness increase either way (never risks the
-- BLEND black-box problem, unlike grid density this doesn't affect which zones get
-- found, only how strongly). Tune this further if it's still too weak/strong anywhere.
local STACK_SIZE = 6

local texturePool = {}

-- Returns the STACK_SIZE-th texture of the given zone-slot `index` (1-based), creating
-- the whole stack for that slot on first use.
local function AcquireTexture(index, layer)
    local slot = texturePool[index]
    if not slot then
        slot = {}
        texturePool[index] = slot
    end
    local tex = slot[layer]
    if not tex then
        tex = WorldMapDetailFrame:CreateTexture(nil, "ARTWORK")
        tex:SetBlendMode("ADD")
        slot[layer] = tex
    end
    return tex
end

local function HideTexturesFrom(index)
    for i = index, #texturePool do
        for _, tex in ipairs(texturePool[i]) do
            tex:Hide()
        end
    end
end

-- Every early-out below (map hidden, cosmic/world view, zoomed into a specific zone, no
-- bridge data) funnels through this single `shown` variable instead of an early `return`,
-- so a change to any of those conditions always hides whatever was left over from the
-- PREVIOUS continent -- confirmed live: an early return here used to skip
-- HideTexturesFrom entirely, leaving the last continent's red patches floating in place
-- over the zoomed-out "whole world" cosmic view.
local function Refresh()
    local shown = 0

    if WorldMapFrame:IsShown() then
        local continentID = GetCurrentMapContinent()
        -- continentID <= 0 covers both WORLDMAP_COSMIC_ID (-1, the zoomed-out "whole
        -- world" view) and unset (0); GetCurrentMapZone() ~= WORLDMAP_WORLD_ID means
        -- zoomed into one specific zone rather than the continent overview -- neither has
        -- zone children to overlay.
        if continentID > 0 and GetCurrentMapZone() == WORLDMAP_WORLD_ID then
            local bridge = ArchipelagoWoW_BridgeDB
            if bridge then
                local unlockedMap = bridge.unlockedZones or {}
                local cache = shapeCacheByContinent[continentID] or ScanContinent(continentID)
                local width, height = WorldMapDetailFrame:GetWidth(), WorldMapDetailFrame:GetHeight()

                for zoneName, shape in pairs(cache) do
                    if Zones.IsZoneNameLocked(zoneName, unlockedMap) then
                        local texWidth = shape.textureX * width
                        local texHeight = shape.textureY * height
                        if texWidth > 0 and texHeight > 0 then
                            shown = shown + 1
                            local texturePath = "Interface\\WorldMap\\" .. shape.fileName .. "\\" .. shape.fileName .. "Highlight"
                            for layer = 1, STACK_SIZE do
                                local tex = AcquireTexture(shown, layer)
                                tex:SetVertexColor(1, 0, 0)
                                tex:SetTexCoord(0, shape.texPercentageX, 0, shape.texPercentageY)
                                tex:SetTexture(texturePath)
                                tex:ClearAllPoints()
                                tex:SetWidth(texWidth)
                                tex:SetHeight(texHeight)
                                tex:SetPoint("TOPLEFT", WorldMapDetailFrame, "TOPLEFT", shape.scrollChildX * width, -shape.scrollChildY * height)
                                tex:Show()
                            end
                        end
                    end
                end
            end
        end
    end

    HideTexturesFrom(shown + 1)
end

-- WORLD_MAP_UPDATE fires on every zoom/zone change (and on opening the map -- see
-- WorldMapFrame_OnShow's SetMapToCurrentZone call in FrameXML/WorldMapFrame.lua), which
-- is exactly the legacy-client equivalent of the modern API's OnMapChanged.
local frame = CreateFrame("Frame")
frame:RegisterEvent("WORLD_MAP_UPDATE")
frame:SetScript("OnEvent", Refresh)
