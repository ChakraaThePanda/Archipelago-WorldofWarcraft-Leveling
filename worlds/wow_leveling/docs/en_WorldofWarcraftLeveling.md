# World of Warcraft Leveling

## What does randomization do to this game?

Normally you can quest anywhere your level allows and cross a level-cap boundary the moment
you hit that level. In this randomizer, both of those are gated behind items from the
multiworld:

- Each leveling zone (e.g. "Westfall (10-20)", "Hellfire Peninsula (58-63)") has its own
  unlock item. You can only turn in quests / gain experience in zones you've received.
- Crossing from one level-bracket into the next (e.g. level 20 into the 21-30 bracket)
  needs a level-cap item for that bracket, plus at least one zone item that covers it (two,
  if the "Easier Transitions" option is on). Crossing into a new expansion's content (60,
  70, 80, 85, 90) additionally needs that expansion's own starting zone once "Easier
  Transitions" is on.
- Level-cap items come in one of two families, chosen with the "Level Items" option:
  **Sequential** ("Maximum Level 20", "Maximum Level 30", ... one specific item per
  bracket) or **Progressive** ("Progressive Levels" -- each copy raises your cap to the
  next bracket in order, regardless of which one you receive).

## What is the goal?

Chosen with the "Selected Goal" option:
- **Leveling**: reach your chosen "Maximum Level" (anywhere from 10 to 90).
- **Gold Hunt**: find a set amount of "Gold" items in the pool (1-10, default 10).

Reaching either condition is detected automatically by the companion bridge client and
reported to the server -- nothing needs to be done manually to "declare" you've won.

## What items and locations get shuffled?

- One check per level, from "Level 01" up to your "Maximum Level", sent when you reach
  that level. There is no separate location for
  the goal itself -- reaching it is detected from your level/gold state directly (see
  above) and reported to the server without needing a location check.
- If "Include Achievements" is on (**Wrath of the Lich King or newer only**): extra checks
  from your character's Statistics, like dying once, earning your first gold, and killing
  creatures, completing quests and catching fish. They get a bit harder as you level, up to
  level 60, and you only get the ones that fit your "Maximum Level". They're sent the next
  time you click Sync.
- The item pool is built from: Gold (Gold Hunt only), level-cap items (Sequential or
  Progressive, matching your "Level Items" choice), one unlock item per leveling zone
  (only zones that start at or below your "Maximum Level", for your faction and your
  Pre/Post-Cataclysm choice), a class and
  a faction filler item per class/faction (removed from the pool if "Randomize Class" is on
  or always for your own faction, and precollected instead), and -- if "Include Dungeons" is
  on -- one filler item per leveling dungeon.

## What does another world's item look like in World of Warcraft?

There's no in-game notification from Blizzard's own client -- the companion addon/client
applies received items quietly in the background (zone and level-cap unlocks, precollected
class/faction), and reaching a new level or the goal sends its check automatically.
