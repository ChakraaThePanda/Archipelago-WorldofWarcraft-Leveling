-- ArchipelagoWoW: Map.lua
-- Tints every not-yet-unlocked zone red on the World Map's continent-level view (the
-- zoom level that shows Kalimdor/Eastern Kingdoms/Outland/Northrend/Pandaria as a
-- selection of named zones), so a glance at the map shows what's still locked without
-- opening the Zones/Progress panel.
--
-- The overlay reuses Blizzard's OWN per-zone highlight art -- the same shaped texture
-- the game shows when you mouse over a zone's name on the continent map (confirmed
-- against the actual FrameXML/Lua source for Vanilla, Wrath, Cataclysm and retail: all
-- four route that hover effect through the identical, version-independent
-- MapHighlightDataProviderMixin in Blizzard_SharedMapDataProviders, which calls
-- C_Map.GetMapHighlightInfoAtPosition -- there is no separate "Classic doesn't have
-- shaped highlights" API to work around). That's what makes an exact zone-shaped mask
-- possible here at all: we are not tracing borders ourselves, just asking the client
-- for the same pre-baked shape Blizzard already draws, at a point known to be inside
-- the zone, and tinting it red instead of its normal white/gold.
--
-- Known, accepted limitation: a handful of zones' own highlight art is a small glow near
-- the zone's label rather than something covering the whole zone, so those don't get
-- tinted at all. Tried three shape-derived alternatives (one bounding box per zone, one
-- strip per scan row, one tile per scan point -- see MapLegacy.lua's header for the full
-- live-confirmed reasoning on its counterpart) that all covered every zone completely;
-- each looked worse in a different way (fused-together overlapping zones, or a busy
-- checkerboard texture) than this version's partial-but-clean coverage. Reverted back to
-- this on purpose; do not re-attempt those without new information that changes the
-- trade-off.
--
-- Everything below only reads ArchipelagoWoW_BridgeDB.unlockedZones -- like the rest of
-- this addon, that's only ever as fresh as the last sync/reload (see UI.lua's header
-- comment), so this overlay reflects "state as of last sync", not something that
-- updates live mid-session.

local ADDON_NAME, APW = ...

-- Everything below needs C_Map/Enum.UIMapType/the MapCanvas pin system, none of which
-- exist on a genuine pre-Legion (original 3.3.5-era) client -- see MapLegacy.lua for the
-- counterpart that runs there instead.
if not APW.Compat.HasModernMapAPI then return end

APW.Map = APW.Map or {}
local Zones = APW.Zones

local PIN_TEMPLATE = "APWLockedZoneHighlightPinTemplate"
local RED = { 1, 0, 0, 1 }
-- The highlight art itself is a dim additive glow by design (a subtle mouseover cue, not
-- meant to read as a bold wash on its own) -- see Map.xml's comment on why BLEND isn't an
-- option here. Stacking this many identical ADD copies multiplies the contributed light
-- without ever risking the opaque-background box BLEND produced; tune this (and the
-- matching HighlightTextureN layers in Map.xml) if it's still too weak/strong.
local HIGHLIGHT_LAYERS = {
    "HighlightTexture1", "HighlightTexture2", "HighlightTexture3",
    "HighlightTexture4", "HighlightTexture5", "HighlightTexture6",
}

-- ---------------------------------------------------------------------------
-- The pin: one giant (full-canvas-sized) invisible frame per locked zone, holding a
-- single visible texture positioned/sized inside it. Sizing the pin itself to the
-- whole canvas -- rather than to the zone's own on-screen footprint -- mirrors
-- MapHighlightPinMixin exactly, because C_Map.GetMapHighlightInfoAtPosition's
-- scrollChildX/Y and textureX/Y are returned as fractions of the WHOLE map, so
-- whatever frame does the math to turn them into pixels has to BE the whole map.
-- ---------------------------------------------------------------------------

APWLockedZoneHighlightPinMixin = CreateFromMixins(MapCanvasPinMixin)

function APWLockedZoneHighlightPinMixin:OnLoad()
    self:UseFrameLevelType("PIN_FRAME_LEVEL_MAP_HIGHLIGHT")
end

-- Called by a data provider right after acquiring this pin, with exactly the return
-- values of C_Map.GetMapHighlightInfoAtPosition for the zone it represents.
function APWLockedZoneHighlightPinMixin:OnAcquired(fileDataID, atlasID, texPercentageX, texPercentageY, textureX, textureY, scrollChildX, scrollChildY)
    self.fileDataID = fileDataID
    self.atlasID = atlasID
    self.texPercentageX = texPercentageX
    self.texPercentageY = texPercentageY
    self.textureX = textureX
    self.textureY = textureY
    self.scrollChildX = scrollChildX
    self.scrollChildY = scrollChildY
end

function APWLockedZoneHighlightPinMixin:OnCanvasSizeChanged()
    self:SetSize(self:GetMap():DenormalizeHorizontalSize(1.0), self:GetMap():DenormalizeVerticalSize(1.0))
    self:Redraw()
end

-- Mirrors MapHighlightPinMixin:Refresh()'s positioning math (Blizzard_SharedMapDataProviders/
-- MapHighlightDataProvider.lua) exactly, against our cached values instead of a live
-- mouse-position query.
function APWLockedZoneHighlightPinMixin:Redraw()
    local width, height = self:GetWidth(), self:GetHeight()
    if not width or width == 0 or not height or height == 0 then return end

    for _, layerKey in ipairs(HIGHLIGHT_LAYERS) do
        local tex = self[layerKey]
        tex:SetVertexColor(RED[1], RED[2], RED[3], RED[4])
        tex:SetTexCoord(0, self.texPercentageX, 0, self.texPercentageY)
        tex:ClearAllPoints()

        if self.atlasID then
            tex:SetAtlas(self.atlasID, true, "TRILINEAR")
            local x = ((self.scrollChildX + 0.5 * self.textureX) - 0.5) * width
            local y = -((self.scrollChildY + 0.5 * self.textureY) - 0.5) * height
            tex:SetPoint("CENTER", x, y)
            tex:Show()
        else
            tex:SetTexture(self.fileDataID, nil, nil, "TRILINEAR")
            local texWidth = self.textureX * width
            local texHeight = self.textureY * height
            if texWidth > 0 and texHeight > 0 then
                tex:SetWidth(texWidth)
                tex:SetHeight(texHeight)
                tex:SetPoint("TOPLEFT", self.scrollChildX * width, -self.scrollChildY * height)
                tex:Show()
            end
        end
    end
end

-- ---------------------------------------------------------------------------
-- The data provider: on every map navigation (Blizzard's MapCanvasMixin:OnMapChanged
-- calls RefreshAllData automatically -- no manual event wiring needed for that part),
-- checks whether the newly-shown map is a continent, and if so acquires one pin per
-- locked direct-or-indirect Zone-type child.
-- ---------------------------------------------------------------------------

local DataProvider = CreateFromMixins(MapCanvasDataProviderMixin)
APW.Map.DataProvider = DataProvider

function DataProvider:RefreshAllData()
    local map = self:GetMap()
    map:RemoveAllPinsByTemplate(PIN_TEMPLATE)

    local mapID = map:GetMapID()
    if not mapID then return end

    local mapInfo = C_Map.GetMapInfo(mapID)
    if not mapInfo or mapInfo.mapType ~= Enum.UIMapType.Continent then return end

    local bridge = ArchipelagoWoW_BridgeDB
    if not bridge then return end
    local unlockedMap = bridge.unlockedZones or {}

    local children = C_Map.GetMapChildrenInfo(mapID, Enum.UIMapType.Zone, true)
    if not children then return end

    for _, child in ipairs(children) do
        local zoneInfo = C_Map.GetMapInfo(child.mapID)
        local zoneName = zoneInfo and zoneInfo.name
        if zoneName and Zones.IsZoneNameLocked(zoneName, unlockedMap) then
            local minX, maxX, minY, maxY = C_Map.GetMapRectOnMap(child.mapID, mapID)
            if minX then
                local cx, cy = (minX + maxX) / 2, (minY + maxY) / 2
                local fileDataID, atlasID, texPercentageX, texPercentageY, textureX, textureY, scrollChildX, scrollChildY =
                    C_Map.GetMapHighlightInfoAtPosition(mapID, cx, cy)
                if (fileDataID and fileDataID > 0) or atlasID then
                    local pin = map:AcquirePin(PIN_TEMPLATE, fileDataID, atlasID, texPercentageX, texPercentageY, textureX, textureY, scrollChildX, scrollChildY)
                    pin:SetPosition(0.5, 0.5)
                    -- Called explicitly rather than left to the next natural resize/zoom
                    -- event: this pin was just acquired mid-RefreshAllData, and a freshly
                    -- acquired pin has no guarantee of already having a correctly-sized
                    -- frame (whereas Blizzard's own single persistent highlight pin is
                    -- created once ever and simply outlives every later resize/zoom, so
                    -- it never needs this).
                    pin:OnCanvasSizeChanged()
                end
            end
        end
    end
end

function DataProvider:OnRemoved(mapCanvas)
    MapCanvasDataProviderMixin.OnRemoved(self, mapCanvas)
    mapCanvas:RemoveAllPinsByTemplate(PIN_TEMPLATE)
end

-- ---------------------------------------------------------------------------
-- Wiring: WorldMapFrame may not exist yet at our own addon's load time on client
-- flavors where Blizzard_WorldMap is still a lazy-loaded (LoadOnDemand) addon.
-- ---------------------------------------------------------------------------

local function OnWorldMapLoaded()
    WorldMapFrame:AddDataProvider(DataProvider)
    -- AddDataProvider doesn't itself trigger a refresh -- on a client flavor where
    -- Blizzard_WorldMap is LoadOnDemand, this fires as a side effect of the player
    -- opening the map for the first time this session, which can beat our own
    -- OnMapChanged->RefreshAllData to the punch. Covers that one edge case for free.
    if WorldMapFrame:IsShown() then
        DataProvider:RefreshAllData()
    end
end

if WorldMapFrame then
    OnWorldMapLoaded()
else
    local loader = CreateFrame("Frame")
    loader:RegisterEvent("ADDON_LOADED")
    loader:SetScript("OnEvent", function(self, event, loadedAddonName)
        if loadedAddonName == "Blizzard_WorldMap" then
            OnWorldMapLoaded()
            self:UnregisterEvent("ADDON_LOADED")
        end
    end)
end
