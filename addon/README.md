# WoW Leveling Archipelago Addon

This folder contains the in-game WoW addon half of the WoW Leveling Archipelago
(archipelago.gg) project. It does **not** contain the external bridge program
(a separate Python program built elsewhere) that holds the actual Archipelago
server connection.

## Why two addon folders?

WoW's Lua addon sandbox has never exposed sockets, HTTP, or any live file I/O
to addons, in any client version. The only persistence mechanism available to
an addon is **SavedVariables**: a Lua table that gets serialized to a `.lua`
file on disk, and only at logout or `ReloadUI()`. That means the only way data
can move between this addon and the outside world is through SavedVariables
files on disk, read/written by two different processes (the game client and
the external bridge program) at different times.

To make that safe, the addon is split into two separate folders so a file
"written by the game" and a file "written by the bridge process" are never the
same file:

### `ArchipelagoWoW/`

The real addon. Declares `## SavedVariablesPerCharacter: ArchipelagoWoWDB`.
Only this addon's own Lua code ever assigns into `ArchipelagoWoWDB` -- the
external bridge program never touches this file. It holds:

- `ui` -- saved position/shown-state for the two custom panels.
- `session` -- display-only mirror of bridge-reported info (e.g. seed name).
- `pendingChecks` -- levels detected in-game but not yet confirmed sent.
- `log` -- a capped (200-entry) activity log.

There is no `settings` table and no settings frame at all -- nothing here
needs configuring in-game. The addon has no server address/slot name/password
fields: the Archipelago connection lives entirely in the separate bridge
program, connected the same way as any other Archipelago client (its own
console/GUI, e.g. `/connect host:port`). Which WoW character the bridge
reads/writes is resolved on the bridge side (see the "Which character" note
in WoWLevelingClient.py and its `/wowchar` command), not configured from
in-game. And syncing is manual-only (see "Sync model" below) -- no auto-sync
toggle/delay to configure either.

This addon detects level-ups live via `PLAYER_LEVEL_UP`, lets the player
queue/send checks, and provides the main Archipelago panel and the
Zones/Progress panel.

### `ArchipelagoWoW_Bridge/`

A minimal sidecar addon whose sole purpose is to own a second SavedVariables
file, `ArchipelagoWoW_BridgeDB`, that the external bridge program freely
rewrites directly on disk. The main addon only ever **reads** this table --
it never writes it -- so at logout the game simply re-serializes whatever the
bridge last wrote back to the same file unchanged, with no corruption risk
from having two writers. Its Lua file is a near-empty stub that only seeds an
empty, well-shaped table the very first time the game ever loads it (before
the bridge program has run once), so the file exists in a sane shape for the
bridge to find.

This pattern -- external companion app + SavedVariables + periodic
`ReloadUI()` to sync -- is the same one used by long-established, proven-safe
WoW tools such as WeakAuras Companion and TradeSkillMaster's desktop app: no
memory reading, no packet injection, zero ban risk on retail.

## Sync model

- `PLAYER_LEVEL_UP` fires instantly in-game and queues the new level into
  `pendingChecks` (deduped against both `pendingChecks` and the bridge's
  authoritative `ackedLevels`).
- **Send All Previous Levels** queues every level from 1 up to the player's
  current level not already acked, so connecting to the wrong character/slot
  never blindly floods the server -- it's an explicit, user-initiated action.
- **Sync Now** calls `ReloadUI()`, which is what actually flushes
  `ArchipelagoWoWDB` to disk for the bridge to read, and reloads so the addon
  picks up the bridge's latest `ArchipelagoWoW_BridgeDB`. This is the *only*
  way a sync ever happens -- there is deliberately no automatic/scheduled
  reload of any kind. An automatic `ReloadUI()` firing mid-combat (e.g. right
  after a level-up mid-fight) would drop your target/casting at a genuinely
  dangerous moment, so syncing only ever happens in direct response to you
  clicking the button.
- `ReloadUI()` is a protected call: it only works when invoked synchronously,
  directly inside a real click handler. So Sync Now calls it directly with no
  indirection at all -- an earlier version routed it through a timer for a
  combat-lockdown-retry, which broke that secure chain and got blocked with
  "Interface action failed because of an addon" (confirmed live). Sync Now
  still checks `InCombatLockdown()` first, but only to refuse and ask you to
  click it again once combat ends -- never to queue an automatic retry.
- On every login/reload, the addon reconciles: drops from `pendingChecks`
  anything now present in the bridge's `ackedLevels`, and folds any new
  bridge `incoming` entries into the activity log.
- All UI copy is honest about this: connection status, received items, and
  "last sync" times reflect the state as of the last `ReloadUI()`/login, never
  literally live.

## Panels

- **Archipelago** (`/apwow`, or the "View Zones / Progress" button's sibling): connection
  status, seed name, expansion/faction/goal (faction and goal are display-cased for
  reading -- "Alliance", "Goal: Leveling" -- but the underlying values compared in code
  stay the raw snake_case Options.py identifiers), Gold Hunt progress (`Gold: X/Y`) when
  that's the active goal, how many levels are queued to send, **Send All Previous
  Levels**, **Sync Now**, **View Zones / Progress**, and the activity log.
- **Zones / Progress** (`/apwow zones`): a "Current level cap: N (as of last sync)"
  subtitle computed from whichever level-cap items have actually been received
  (Sequential: highest `Maximum Level` item; Progressive: `Progressive Levels` count
  mapped to its bracket -- see `WoWLevelingClient._current_level_cap`), a "Level Items
  Received" section (counts, not just presence -- a Progressive count of 3 is shown as
  "Progressive Levels x3"), and "Zones Unlocked" grouped by continent (see `Zones.lua`).
  Has its own small **Sync** button in the top-left corner so this panel doesn't need the
  main Archipelago panel kept open just to reach that button. Classes/Factions are
  deliberately NOT shown here -- both are a single fixed choice known from the moment you
  connect (a class only if `randomize_class` was on; you'll see it once in the Archipelago
  panel's activity log, e.g. "Received Paladin from Archipelago"), never something that
  progressively unlocks.

Both panels are draggable and resizable (drag the bottom-right grip), and remember their
position, size, and open/closed state across reloads (persisted the same way as
`pendingChecks`/the log, in `ArchipelagoWoWDB.ui`) -- confirmed live that this needs the
open/closed value to be read *before* `CreateMainPanel`/`CreateZonesPanel` run, since a
freshly created frame is shown by default, so their own `frame:Hide()` call fires
`OnHide` and would otherwise clobber the persisted value first.

## Multi-version packaging

Both folders use the standard multi-TOC packaging convention (one shared set
of `.lua` files, several `.toc` files differing only by `## Interface:`):

| TOC file suffix | Client flavor | Interface number | Source |
| --- | --- | --- | --- |
| *(none)* | Retail / Mainline | 120007 | `TomTom.toc` / `TomTom_Mainline.toc`, installed under `_retail_` |
| `_Wrath` | Wrath Classic | 30300 | Matches the local AzerothCore 3.3.5a test client (`ElvUI.toc`, `Questie-335.toc` installed there both target 30300) |
| `_Vanilla` | Classic Era | 11508 | `TomTom_Vanilla.toc` |
| `_Cata` | Cataclysm Classic | 40401 | `TomTom_Cata.toc` |

Note on the Wrath number: official Blizzard "WotLK Classic" (the
currently-sold Battle.net service) reports interface `30403` (see
`Questie-WOTLKC.toc`, also installed locally). This project's only real test
client is the local AzerothCore 3.3.5a server, which -- like every other addon
already installed there -- expects `30300`. If you ever target the official
Blizzard WotLK Classic service instead, bump `ArchipelagoWoW_Wrath.toc` (and
its Bridge counterpart) to `30403`, or ship a second `_WrathClassic` TOC pair
for it and check "Load out of date AddOns" isn't otherwise needed.

Client-flavor branching in the Lua code itself (see `Compat.lua`) is done only
by comparing `WOW_PROJECT_ID` against Blizzard's named globals
(`WOW_PROJECT_MAINLINE`, `WOW_PROJECT_CLASSIC`,
`WOW_PROJECT_BURNING_CRUSADE_CLASSIC`, `WOW_PROJECT_WRATH_CLASSIC`,
`WOW_PROJECT_CATACLYSM_CLASSIC`, ...), never hardcoded numeric IDs. Note that
on the local AzerothCore 3.3.5a client specifically, `WOW_PROJECT_ID` isn't
defined as a real global at all (confirmed by the fact that Questie has to
build its own compatibility shim with hardcoded IDs for that environment) --
`Compat.lua` treats that as the same "legacy client" fallback as any other
pre-Legion-API client, which is the correct behavior for it anyway (no
`BackdropTemplate`, legacy backdrop methods).
