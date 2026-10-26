# World of Warcraft Leveling Setup Guide

## Required Software

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases)
- World of Warcraft Classic, from Classic Era through Mists of Pandaria Classic. Retail also
  works.
- From the [latest release](https://github.com/ChakraaThePanda/Archipelago-WorldofWarcraft-Leveling/releases/latest):
  `wow_leveling.apworld`, `addons.zip` and the YAML template

## Installation

1. Place `wow_leveling.apworld` in your Archipelago install's `custom_worlds` folder. Every
   player with a WoW Leveling slot needs to do this on their own machine, even if someone
   else is generating/hosting the room.
2. Add a WoW Leveling entry to your player YAML using the template. Don't set `max_level`
   higher than your game version goes (60 for Vanilla, 70 for TBC, 80 for Wrath, 85 for
   Cataclysm, 90 for Mists of Pandaria).
3. Generate or join a multiworld using your YAML.
4. Unzip `addons.zip` into your WoW `Interface/AddOns` folder. You should end up with both
   `ArchipelagoWoW` and `ArchipelagoWoW_Bridge` there.
5. Launch WoW and make sure both addons are enabled. If they show as out of date, check
   "Load out of date AddOns".
6. Open the Archipelago Launcher and click **WoW Leveling Client**. The first time, it finds
   your WoW folder automatically or asks you to pick it (change it later with `/wowdir`).
7. Connect it to your room the same way you would any other Archipelago client.
8. Run `/wow` in the client to see your characters, then pick the one for this slot with
   e.g. `/wow 1`. This is required even if you only have one, and it's remembered per slot.
9. In game, click **Sync Now** once so the addon picks up your new slot.

## Playing

- Your checks reach Archipelago when you click **Sync Now** in the addon (or log out and back
  in). WoW only saves addon data at those moments, so nothing syncs on its own.
- Every level up is a check. With achievements on, so are milestones from your Statistics
  tab (kills, quests, deaths, fishing, Hearthstone uses...).
- You can only quest in zones you've unlocked, and only level past each bracket once you've
  received its level items. **View Zones / Progress** in the addon shows both.
- Connecting an already-leveled character to a new slot? Click **Send All Previous Levels**.
- Type `/apwow` in game to open the addon.

## Notes

- Neither piece changes your characters or game files. The addon only reports your progress,
  and the client only reads and writes the addon's own saved data.
- Everyone with a WoW Leveling slot needs their own addons and their own running client.
