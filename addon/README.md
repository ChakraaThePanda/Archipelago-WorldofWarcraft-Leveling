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
in WoWLevelingClient.py and its `/wow` command), not configured from
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
memory reading, no packet injection, zero ban risk.

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

## Supported scope

This project targets the original, live-service WoW client patches from Vanilla
through Mists of Pandaria (2004-2013), the actual old game as it's still run today via
private-server emulation (AzerothCore, TrinityCore, and similar). It does **not**
target Blizzard's 2019+ "WoW Classic" rerelease product line, and it does not target
retail. Those are different software with different, incompatible Interface numbers
from the ones this addon targets, so loading this on a Blizzard Classic or retail
client is out of scope and unsupported (it may or may not happen to work).

## One .toc for every expansion

Each folder ships a single `<AddonName>.toc`, pinned to `## Interface: 30300` (Wrath of
the Lich King 3.3.5a), independently confirmed against the local AzerothCore 3.3.5a test
client, where every other addon already installed (`ElvUI.toc`, `Questie-335.toc`) also
targets `30300`.

That one file is enough for every expansion in scope, not just Wrath, because nothing in
the Lua code branches on the `.toc`'s declared Interface number at all. `Compat.lua`
checks whether a given global actually exists right now (`C_Map ~= nil`,
`BackdropTemplateMixin ~= nil`), which gives the correct answer on whichever original
client is actually running, Vanilla through Mists, regardless of what the `.toc` claims.
The Interface field only ever controls one thing client-side: whether the addon shows as
"out of date" (and is hidden by default) in the AddOns list on a client whose own build
number doesn't match it. If that happens, checking "Load out of date AddOns" in that
list (a checkbox that's existed since Vanilla) makes it load and run exactly the same as
on Wrath; there's no separate file to swap in for a different expansion.

Earlier revisions of this addon shipped a `_<Flavor>.toc` per expansion (one per TOC file
suffix Blizzard's own modern client understands), on the mistaken assumption that an
original-era client would pick the right one automatically. It doesn't: that
flavor-suffix convention, and the newer comma-separated `## Interface: a, b, c` list some
retail addons use for the same purpose, are both features of Blizzard's modern (2021+ and
2024+, respectively) client codebase, which a genuine pre-Legion original client, or a
private server emulating one, predates entirely and has no concept of at all. Those extra
files were removed rather than kept as dead weight; this single `.toc` is the whole story
now.

There's deliberately no `WrathClassic`/`30403` variant for Blizzard's official WotLK
Classic rerelease (see "Supported scope" above): that's a different, out-of-scope product
with its own separate interface numbering, not something this addon claims to support.

The Lua code itself (see `Compat.lua`) never branches on client flavor or
`WOW_PROJECT_ID` at all, only on the actual API surface (does this global/mixin
exist right now?). That's not just a style preference: `WOW_PROJECT_ID` and every
`WOW_PROJECT_*` named global were only added in patch 7.0 (Legion, 2016), so they
don't exist at all on a genuine original-era client, or on the local AzerothCore
3.3.5a test client (confirmed by the fact that Questie has to build its own
compatibility shim with hardcoded IDs for that environment), which describes every
client this addon actually targets. `Compat.lua` treats the absence of those modern
globals as the normal case rather than a fallback, which is the correct behavior for
every client in scope here (no `BackdropTemplate`, no `C_Map`, legacy backdrop
methods).
