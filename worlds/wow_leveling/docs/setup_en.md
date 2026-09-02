# World of Warcraft Leveling Setup Guide

## Required Software

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases)
- World of Warcraft: the original, live-service client for the expansion you intend to
  play (Vanilla through Mists of Pandaria, 2004-2013), as still run today via
  private-server emulation. This project does **not** target Blizzard's 2019+ "WoW
  Classic" rerelease or retail; those are different software (your `expansion` YAML
  option should match what you're actually leveling in)
- The `wow_leveling.apworld` file, installed like any other apworld
- This repository's `addon/` folder (two addon folders, described below)

## Why two pieces?

WoW's Lua addon sandbox has never exposed sockets or live file I/O to addons, in any client
version -- so an in-game addon alone can't hold the actual Archipelago connection. This game
is played with two pieces working together:

- **The WoW addon** (`addon/ArchipelagoWoW` + `addon/ArchipelagoWoW_Bridge`, installed into
  your WoW client) detects your level-ups in-game and shows you your connection status,
  received items, and goal progress.
- **The WoW Leveling Client** (bundled inside the apworld, launched from the Archipelago
  Launcher like any other game's client) holds the actual connection to your Archipelago
  room. It talks to the addon purely by reading/writing small files on disk -- it does not
  read your game memory or inject anything into WoW.

Because WoW can only save an addon's data to disk at logout or `/reload`, syncing isn't
instant: level-ups are detected live in-game, but reaching the Archipelago server (and
items coming back) only happens when you log out/in or click **Sync Now** in the addon.
This is deliberately manual, not automatic -- an automatic reload firing mid-combat could
drop your target/casting at a dangerous moment, so nothing ever reloads the UI on its own.

## Installation

1. Place `wow_leveling.apworld` in your Archipelago install's `custom_worlds` folder. Every
   player with a WoW Leveling slot (single player or multiplayer) needs to do this on their
   own machine, even if someone else is generating/hosting the room.
2. Add a WoW Leveling entry to your player YAML -- see this repo's `World of Warcraft Leveling.yaml`
   for a ready-to-use template, and adjust `expansion`, `faction`, `goal`, and the other
   options to taste.
3. Generate or join a multiworld using your YAML.
4. Unzip this repo's `addons.zip` directly into your WoW installation's `Interface/AddOns`
   folder (so you end up with `Interface/AddOns/ArchipelagoWoW/...` and
   `Interface/AddOns/ArchipelagoWoW_Bridge/...` side by side) -- or copy both
   `addon/ArchipelagoWoW` and `addon/ArchipelagoWoW_Bridge` there yourself if you're working
   from source instead. Both folders are required -- the second one is a small sidecar the
   desktop client writes into; see `addon/README.md` for why it's a separate addon. The
   same `ArchipelagoWoW.toc`/`ArchipelagoWoW_Bridge.toc` work for every supported
   expansion, Vanilla through Mists of Pandaria; there's nothing to swap or rename.
5. Launch World of Warcraft and make sure both addons are enabled on your character-select
   AddOns list. If either shows greyed out, check "Load out of date AddOns": the shipped
   `.toc` declares one specific Interface number (see `addon/README.md`'s "One .toc for
   every expansion" section for why that's fine on any of them, not just that exact one).
6. Open the Archipelago Launcher and click **WoW Leveling Client**. This is the piece that
   actually connects to your room -- the first time it runs, it will try to auto-detect your
   WoW install folder, or ask you to pick it (change it later with `/wowdir <path>`). Both a
   flat client (WTF directly in the folder, e.g. a standalone WotLK 3.3.5 client, the
   normal layout for the private servers this project targets) and one where WTF instead
   lives one level down under a version-named subfolder are auto-detected and handled
   correctly; this is confirmed working end-to-end on a local WotLK 3.3.5 (AzerothCore)
   server.
7. Connect the client to your room the same way you would any other Archipelago client --
   server address, slot name, optional password, either via its GUI fields or `/connect
   host:port`. The addon has no server/slot/password fields of its own; the two are
   unrelated: which room you're connected to is decided here, in the client, and which WoW
   character it reads/writes for is decided by step 8 below.
8. If you have more than one character with ArchipelagoWoW data (e.g. multiple realms or
   alts under the same WoW install), run `/wow` in the client to see them listed and pin
   the one for this room with `/wow <number>`. This pin is remembered separately per room,
   so a fresh room never starts out with anything pre-selected. With only one such
   character, this is automatic; nothing to do.

## Playing

- Level up normally -- `PLAYER_LEVEL_UP` queues that level's check in-game immediately; it
  reaches the server the next time you click **Sync Now** (or log out/in).
- You can only quest effectively in zones whose unlock item you've received; the addon's
  Zones/Progress panel shows which zones are currently unlocked.
- You can only level past a bracket boundary (e.g. from 20 into the 21-30 range) once you've
  received the level-cap item(s) that bracket needs -- see
  [en_WorldofWarcraftLeveling.md](en_WorldofWarcraftLeveling.md) for exactly how that's
  gated. The Zones/Progress panel's "Level Items Received" section shows exactly which
  ones (or, for Progressive, how many copies) you've received so far.
- If your goal is Gold Hunt, the main Archipelago panel shows how much Gold you've
  received against the amount needed to win.
- If "Randomize Class" was enabled for your slot, your class was already chosen for you at
  generation time -- it isn't shown as ongoing "progress" anywhere (it's a single fixed
  choice, not something that unlocks over time), but you'll see it once in the Activity Log
  the first time you sync after connecting (e.g. "Received Paladin from Archipelago").
- Use **Send All Previous Levels** in the addon (instead of relying only on live level-ups)
  if you ever connect an existing, already-leveled character to a fresh slot.

## Notes

- Neither piece modifies your characters, quest log, or save data -- the addon only reports
  level-ups and reflects received items/goal progress back to you; the desktop client only
  reads/writes its own small SavedVariables files.
- Everyone in a multiworld with a WoW Leveling slot needs their own copy of both addons and
  their own running WoW Leveling Client, even if you're all playing on the same WoW account
  or server.
- A WoW install can have many Account/Realm/Character combinations. With only one that has
  ArchipelagoWoW data, the desktop client uses it automatically; with more than one, pin the
  right one with `/wow` (see step 8) rather than relying on "whichever logged out most
  recently", since checking mail on an unrelated alt would otherwise silently steal focus
  from the character actually playing this room. The pin is per Archipelago room, so it
  never carries over to a different room. Run `/wow` any time to see which one is currently
  pinned, what's actively syncing, or to re-pin it.
