from dataclasses import dataclass

from BaseClasses import Item, ItemClassification

# Arbitrary but distinctive base -- check https://archipelago.gg (or the community ID
# registry) for collisions with any other apworld you have installed before generating
# alongside other games. Deliberately far from Northgard's own 39190000.
BASE_ID = 39280000

# Every item this world can create, hardcoded here (not loaded from JSON/a data file) --
# matching this project's other apworlds (Northgard, WEBFISHING). Ported faithfully from
# the original Manual-based WorldofWarcraft-Leveling project's data/items.json (171 real
# items, verified to match exactly) plus one added entry: Manual's engine synthesizes its
# configured filler_item_name ("Did someone say [Thunderfury...]?!", see FILLER_ITEM_NAME
# below) on the fly without it needing to be a real item.json entry, which a standalone
# World can't do -- so it's listed explicitly here as entry #172, count 1, no category.
_RAW_ITEMS: list[dict] = [
    {'count': 10, 'name': 'Gold', 'category': ['Gold'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 20', 'category': ['Maximum Levels', 'Sequential Levels', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 30', 'category': ['Maximum Levels', 'Sequential Levels', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 40', 'category': ['Maximum Levels', 'Sequential Levels', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 50', 'category': ['Maximum Levels', 'Sequential Levels', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 60', 'category': ['Maximum Levels', 'Sequential Levels', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 70', 'category': ['Maximum Levels', 'Sequential Levels', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 80', 'category': ['Maximum Levels', 'Sequential Levels', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 85', 'category': ['Maximum Levels', 'Sequential Levels', 'Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Maximum Level 90', 'category': ['Maximum Levels', 'Sequential Levels', 'Mists of Pandaria'], 'progression': True},
    {'count': 9, 'name': 'Progressive Levels', 'category': ['Maximum Levels', 'Progressive Levels'], 'progression': True},
    {'count': 1, 'name': 'Ghostlands (10-20)', 'category': ['Zones', 'Zones 10-20', 'Horde', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Westfall (10-15)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Westfall (10-20)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Bloodmyst Isle (10-20)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Darkshore (10-20)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Loch Modan (10-20)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Azshara (45-55)', 'category': ['Zones', 'Zones 50-60', 'Horde', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Azshara (10-20)', 'category': ['Zones', 'Zones 10-20', 'Horde', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Northern Barrens (10-20)', 'category': ['Zones', 'Zones 10-20', 'Horde', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'The Barrens (10-25)', 'category': ['Zones', 'Zones 10-20', 'Zones 20-30', 'Horde', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Silverpine Forest (10-20)', 'category': ['Zones', 'Zones 10-20', 'Horde', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Redridge Mountains (15-20)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Redridge Mountains (15-25)', 'category': ['Zones', 'Zones 10-20', 'Alliance', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Ashenvale (20-25)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Ashenvale (20-30)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Hillsbrad Foothills (20-25)', 'category': ['Zones', 'Zones 20-30', 'Horde', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Hillsbrad Foothills (20-30)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Alterac Mountains (30-40)', 'category': ['Zones', 'Zones 30-40', 'Alliance', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Duskwood (20-25)', 'category': ['Zones', 'Zones 20-30', 'Alliance', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Duskwood (18-30)', 'category': ['Zones', 'Zones 20-30', 'Alliance', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Wetlands (20-25)', 'category': ['Zones', 'Zones 20-30', 'Alliance', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Wetlands (20-30)', 'category': ['Zones', 'Zones 20-30', 'Alliance', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Arathi Highlands (25-30)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Arathi Highlands (30-40)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Northern Stranglethorn (25-30)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Stranglethorn Vale (30-45)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Stonetalon Mountains (25-30)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Stonetalon Mountains (15-25)', 'category': ['Zones', 'Zones 20-30', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Desolace (30-35)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Desolace (30-40)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Southern Barrens (30-35)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'The Cape of Stranglethorn (30-35)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'The Hinterlands (30-35)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'The Hinterlands (40-50)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Dustwallow Marsh (35-40)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Dustwallow Marsh (35-45)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Feralas (35-40)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Feralas (40-50)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Western Plaguelands (51-58)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Western Plaguelands (35-40)', 'category': ['Zones', 'Zones 30-40', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Eastern Plaguelands (40-45)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Eastern Plaguelands (53-60)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Thousand Needles (40-45)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Thousand Needles (25-35)', 'category': ['Zones', 'Zones 30-40', 'Horde', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Badlands (44-48)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Badlands (36-45)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Felwood (45-50)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Felwood (48-55)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Tanaris (45-50)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Tanaris (40-50)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Searing Gorge (47-51)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Searing Gorge (43-50)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Burning Steppes (49-52)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Burning Steppes (50-58)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': "Un'Goro Crater (50-55)", 'category': ['Zones', 'Zones 50-60', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Winterspring (50-55)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Winterspring (55-60)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Swamp of Sorrows (52-54)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Swamp of Sorrows (35-45)', 'category': ['Zones', 'Zones 40-50', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Blasted Lands (54-60)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Post-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Blasted Lands (45-55)', 'category': ['Zones', 'Zones 50-60', 'Vanilla', 'Pre-Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Silithus (55-60)', 'category': ['Zones', 'Zones 50-60', 'Vanilla'], 'progression': True},
    {'count': 1, 'name': 'Hellfire Peninsula (58-63)', 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Zangarmarsh (60-64)', 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Terokkar Forest (62-65)', 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Nagrand (64-67)', 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': "Blade's Edge Mountains (65-68)", 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Shadowmoon Valley (67-70)', 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Netherstorm (67-70)', 'category': ['Zones', 'Zones 60-70', 'The Burning Crusade'], 'progression': True},
    {'count': 1, 'name': 'Borean Tundra (68-72)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Howling Fjord (68-72)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Dragonblight (71-75)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Grizzly Hills (73-75)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': "Zul'Drak (74-76)", 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Sholazar Basin (76-78)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Crystalsong Forest (77-80)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Icecrown (77-80)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'The Storm Peaks (77-80)', 'category': ['Zones', 'Zones 70-80', 'Wrath of the Lich King'], 'progression': True},
    {'count': 1, 'name': 'Mount Hyjal (80-82)', 'category': ['Zones', 'Zones 80-85', 'Cataclysm'], 'progression': True},
    {'count': 1, 'name': "Vashj'ir (80-82)", 'category': ['Zones', 'Zones 80-85', 'Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Deepholm (82-83)', 'category': ['Zones', 'Zones 80-85', 'Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Uldum (83-84)', 'category': ['Zones', 'Zones 80-85', 'Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'Twilight Highlands (84-85)', 'category': ['Zones', 'Zones 80-85', 'Cataclysm'], 'progression': True},
    {'count': 1, 'name': 'The Jade Forest (85-86)', 'category': ['Zones', 'Zones 85-90', 'Mists of Pandaria'], 'progression': True},
    {'count': 1, 'name': 'Krasarang Wilds (86-87)', 'category': ['Zones', 'Zones 85-90', 'Mists of Pandaria'], 'progression': True},
    {'count': 1, 'name': 'Valley of the Four Winds (86-87)', 'category': ['Zones', 'Zones 85-90', 'Mists of Pandaria'], 'progression': True},
    {'count': 1, 'name': 'Kun-Lai Summit (87-88)', 'category': ['Zones', 'Zones 85-90', 'Mists of Pandaria'], 'progression': True},
    {'count': 1, 'name': 'Townlong Steppes (88-89)', 'category': ['Zones', 'Zones 85-90', 'Mists of Pandaria'], 'progression': True},
    {'count': 1, 'name': 'Dread Wastes (89-90)', 'category': ['Zones', 'Zones 85-90', 'Mists of Pandaria'], 'progression': True},
    {'count': 1, 'name': 'Paladin', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Warrior', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Hunter', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Shaman', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Druid', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Monk', 'category': ['Class', 'Post-Cataclysm'], 'filler': True},
    {'count': 1, 'name': 'Rogue', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Mage', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Priest', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Warlock', 'category': ['Class'], 'filler': True},
    {'count': 1, 'name': 'Alliance', 'category': ['Faction', 'Alliance'], 'filler': True},
    {'count': 1, 'name': 'Horde', 'category': ['Faction', 'Horde'], 'filler': True},
    {'count': 1, 'name': 'Ragefire Chasm (15-21)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'The Deadmines (15-21)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Wailing Caverns (15-25)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Shadowfang Keep (16-26)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Blackfathom Deeps (20-30)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Stormwind Stockade (20-30)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Gnomeregan (24-34)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Scarlet Halls (26-36)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Scarlet Monastery (28-38)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Razorfen Kraul (30-40)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Maraudon - The Wicked Grotto (30-40)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Maraudon - Foulspore Cavern (32-42)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Maraudon - Earth Song Falls (34-44)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Uldaman (35-45)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Dire Maul - Warpwood Quarter (36-46)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Scholomance (38-48)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Dire Maul - Capital Gardens (39-49)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Razorfen Downs (40-50)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Dire Maul - Gordok Commons (42-52)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Stratholme - Main Gate (42-52)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': "Zul'Farrak (44-54)", 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Stratholme - Service Entrance (46-56)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Blackrock Depths - Detention Block (47-57)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Sunken Temple (50-60)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Blackrock Depths - Upper City (51-61)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Lower Blackrock Spire (55-65)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Upper Blackrock Spire (55-65)', 'category': ['Dungeons', 'Dungeons 15-60', 'Vanilla'], 'filler': True},
    {'count': 1, 'name': 'Hellfire Ramparts (58-67)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Blood Furnace (59-68)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Slave Pens (60-69)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Underbog (61-70)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Mana-Tombs (62-71)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Auchenai Crypts (63-72)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'The Escape from Durnholde (64-73)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Sethekk Halls (65-73)', 'category': ['Dungeons', 'Dungeons 60-70', 'The Burning Crusade'], 'filler': True},
    {'count': 1, 'name': 'Utgarde Keep (68-78)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'The Nexus (69-79)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'Azjol-Nerub (70-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': "Ahn'kahet: The Old Kingdom (71-80)", 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': "Drak'Tharon Keep (72-80)", 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'The Violet Hold (73-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'Gundrak (74-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'Halls of Stone (75-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'Halls of Lightning (77-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'The Oculus (77-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'Utgarde Pinnacle (77-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'The Culling of Stratholme (78-80)', 'category': ['Dungeons', 'Dungeons 70-80', 'Wrath of the Lich King'], 'filler': True},
    {'count': 1, 'name': 'Blackrock Caverns (80-85)', 'category': ['Dungeons', 'Dungeons 80-85', 'Cataclysm'], 'filler': True},
    {'count': 1, 'name': 'Throne of the Tides (80-85)', 'category': ['Dungeons', 'Dungeons 80-85', 'Cataclysm'], 'filler': True},
    {'count': 1, 'name': 'The Stonecore (81-85)', 'category': ['Dungeons', 'Dungeons 80-85', 'Cataclysm'], 'filler': True},
    {'count': 1, 'name': 'The Vortex Pinnacle (81-85)', 'category': ['Dungeons', 'Dungeons 80-85', 'Cataclysm'], 'filler': True},
    {'count': 1, 'name': 'Grim Batol (84-85)', 'category': ['Dungeons', 'Dungeons 80-85', 'Cataclysm'], 'filler': True},
    {'count': 1, 'name': "Lost City of the Tol'vir (84-85)", 'category': ['Dungeons', 'Dungeons 80-85', 'Cataclysm'], 'filler': True},
    {'count': 1, 'name': 'Stormstout Brewery (85-90)', 'category': ['Dungeons', 'Dungeons 85-90', 'Mists of Pandaria'], 'filler': True},
    {'count': 1, 'name': 'Temple of the Jade Serpent (85-90)', 'category': ['Dungeons', 'Dungeons 85-90', 'Mists of Pandaria'], 'filler': True},
    {'count': 1, 'name': 'Shado-Pan Monastery (87-90)', 'category': ['Dungeons', 'Dungeons 85-90', 'Mists of Pandaria'], 'filler': True},
    {'count': 1, 'name': "Mogu'shan Palace (87-90)", 'category': ['Dungeons', 'Dungeons 85-90', 'Mists of Pandaria'], 'filler': True},
    {'count': 1, 'name': 'Siege of Niuzao Temple (88-90)', 'category': ['Dungeons', 'Dungeons 85-90', 'Mists of Pandaria'], 'filler': True},
    {'count': 1, 'name': 'Gate of the Setting Sun (88-90)', 'category': ['Dungeons', 'Dungeons 85-90', 'Mists of Pandaria'], 'filler': True},
    {'count': 1, 'name': 'Did someone say [Thunderfury, Blessed Blade of the Windseeker]?!', 'category': [], 'filler': True},
]

# category name -> yaml option name(s) that must ALL be truthy for items tagged with that
# category to be allowed in the pool. Currently just {"Dungeons": ["include_dungeons"]}.
_RAW_CATEGORIES: dict = {'Dungeons': {'yaml_option': ['include_dungeons']}}


class WoWLevelingItem(Item):
    game: str = "World of Warcraft Leveling"


@dataclass(frozen=True)
class ItemData:
    code: int
    classification: ItemClassification
    count: int
    category: tuple[str, ...]


def _classification(entry: dict) -> ItemClassification:
    if entry.get("progression"):
        return ItemClassification.progression
    if entry.get("filler"):
        return ItemClassification.filler
    return ItemClassification.useful


# Item IDs follow _RAW_ITEMS' own order (stable across edits to entries' *contents*,
# since re-ordering the list itself would only matter if someone reshuffles it).
item_table: dict[str, ItemData] = {
    entry["name"]: ItemData(
        BASE_ID + index,
        _classification(entry),
        entry.get("count", 1),
        tuple(entry.get("category", [])),
    )
    for index, entry in enumerate(_RAW_ITEMS)
}

# category name -> yaml option name(s) that must ALL be truthy for items tagged with that
# category to be allowed in the pool. Currently just {"Dungeons": ["include_dungeons"]},
# but built generically off _RAW_CATEGORIES so a future gated category doesn't need
# a Python code change beyond adding an entry there.
CATEGORY_YAML_GATES: dict[str, list[str]] = {
    name: meta["yaml_option"] for name, meta in _RAW_CATEGORIES.items() if "yaml_option" in meta
}

# The original Manual project's configured filler_item_name, used to pad the pool out to
# the location count once every other item has been placed/filtered.
FILLER_ITEM_NAME = "Did someone say [Thunderfury, Blessed Blade of the Windseeker]?!"

GOLD_ITEM_NAME = "Gold"
PROGRESSIVE_LEVELS_ITEM_NAME = "Progressive Levels"
ALLIANCE_ITEM_NAME = "Alliance"
HORDE_ITEM_NAME = "Horde"

# One "Maximum Level N" item per bracket boundary, in the same order as Regions.LEVEL_BRACKETS[1:].
SEQUENTIAL_LEVEL_ITEMS: list[str] = [
    "Maximum Level 20",
    "Maximum Level 30",
    "Maximum Level 40",
    "Maximum Level 50",
    "Maximum Level 60",
    "Maximum Level 70",
    "Maximum Level 80",
    "Maximum Level 85",
    "Maximum Level 90",
]

CLASS_ITEM_NAMES: list[str] = [name for name, data in item_table.items() if "Class" in data.category]

# The "Victory" event item is never created via create_item/item_table -- it has no code,
# is locked to its location, and never sent over the network. It only exists so
# multiworld.completion_condition has something to check (see Rules.py / __init__.py).
VICTORY_ITEM_NAME = "Victory"

item_name_groups: dict[str, set[str]] = {
    "Zones": {name for name, data in item_table.items() if "Zones" in data.category},
    "Dungeons": {name for name, data in item_table.items() if "Dungeons" in data.category},
    "Classes": set(CLASS_ITEM_NAMES),
}
