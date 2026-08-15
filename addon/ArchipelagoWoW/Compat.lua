-- ArchipelagoWoW: Compat.lua
-- Cross-version compatibility helpers. This is the only file that should ever
-- branch on client flavor. Everything else calls into APW.Compat instead of
-- checking WOW_PROJECT_ID directly.
--
-- IMPORTANT: never hardcode the numeric WOW_PROJECT_ID values. Always compare
-- against Blizzard's own named globals (WOW_PROJECT_MAINLINE, WOW_PROJECT_CLASSIC,
-- WOW_PROJECT_BURNING_CRUSADE_CLASSIC, WOW_PROJECT_WRATH_CLASSIC,
-- WOW_PROJECT_CATACLYSM_CLASSIC, ...) since those resolve correctly on every
-- client build. On some non-Blizzard 3.3.5 client builds WOW_PROJECT_ID does not
-- exist at all (it's nil) -- all the checks below are written to fail safe (false)
-- in that case, and Compat.IsLegacyClient below picks up the fallback.

local ADDON_NAME, APW = ...

APW.Compat = APW.Compat or {}
local Compat = APW.Compat

local function isProject(namedGlobal)
    return WOW_PROJECT_ID ~= nil and namedGlobal ~= nil and WOW_PROJECT_ID == namedGlobal
end

Compat.IsMainline = isProject(WOW_PROJECT_MAINLINE)
Compat.IsVanilla = isProject(WOW_PROJECT_CLASSIC)
Compat.IsBCC = isProject(WOW_PROJECT_BURNING_CRUSADE_CLASSIC)
Compat.IsWrath = isProject(WOW_PROJECT_WRATH_CLASSIC)
Compat.IsCata = isProject(WOW_PROJECT_CATACLYSM_CLASSIC)
Compat.IsMists = isProject(WOW_PROJECT_MISTS_CLASSIC)

-- True when WOW_PROJECT_ID isn't defined at all (older/unofficial 3.3.5-era client
-- builds predate that global) or didn't match anything named above. Treated the
-- same as "old client" for API-availability purposes: no BackdropTemplate mixin,
-- assume legacy widget behavior.
Compat.IsLegacyClient = not (Compat.IsMainline or Compat.IsVanilla or Compat.IsBCC or Compat.IsCata or Compat.IsMists)

-- Only true modern Mainline (retail) requires the explicit "BackdropTemplate"
-- template string passed to CreateFrame. Every Classic-family client (and any
-- client where WOW_PROJECT_ID isn't even defined) already has backdrop methods
-- built into the base Frame widget.
Compat.NeedsBackdropTemplate = Compat.IsMainline and true or false

-- Creates a frame, adding the BackdropTemplate mixin only where required.
function Compat.CreateFrame(frameType, name, parent, template)
    if Compat.NeedsBackdropTemplate then
        if template and template ~= "" then
            template = template .. ",BackdropTemplate"
        else
            template = "BackdropTemplate"
        end
    end
    return CreateFrame(frameType, name, parent, template)
end

-- Applies a backdrop table the same way on every client flavor that supports it.
function Compat.SetBackdrop(frame, backdrop)
    if frame and frame.SetBackdrop then
        frame:SetBackdrop(backdrop)
    end
end

-- Shared basic panel backdrop definition (dialog-box style border, works on both
-- retail-with-mixin and classic-native backdrop implementations).
Compat.PANEL_BACKDROP = {
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
}

-- SetMinResize/SetMaxResize were replaced by a single SetResizeBounds call in retail
-- (10.0+); every Classic-family client (and any client where WOW_PROJECT_ID isn't even
-- defined) only has the older pair.
function Compat.SetResizeBounds(frame, minWidth, minHeight, maxWidth, maxHeight)
    if frame.SetResizeBounds then
        frame:SetResizeBounds(minWidth, minHeight, maxWidth, maxHeight)
    else
        frame:SetMinResize(minWidth, minHeight)
        frame:SetMaxResize(maxWidth, maxHeight)
    end
end
