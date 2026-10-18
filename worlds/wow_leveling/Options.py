from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range, Toggle

# Above this max level, the seed reaches into Cataclysm/Mists content, which assumes the
# world has already been reshaped, so pre_or_post_cataclysm is forced to Post-Cataclysm.
POST_CATACLYSM_FORCED_ABOVE_LEVEL = 80


class Goal(Choice):
    """Choose how you win.
    Leveling: reach your maximum level (see 'max_level').
    Gold Hunt: find enough Gold items to win (see 'gold_hunt_amount')."""
    display_name = "Selected Goal"
    option_leveling = 0
    option_gold_hunt = 1
    default = 0


class MaxLevel(Range):
    """The level you want to reach. Every level up to this one is a check, and only zones
    and dungeons that start at or below this level are included.
    Expansion level caps: Vanilla 60, The Burning Crusade 70, Wrath of the Lich King 80,
    Cataclysm 85, Mists of Pandaria 90."""
    display_name = "Maximum Level"
    range_start = 10
    range_end = 90
    default = 80


class Faction(Choice):
    """Choose your character faction. Affects which zones are available for you to quest in."""
    display_name = "Character Faction"
    option_alliance = 0
    option_horde = 1
    default = "random"


class RandomizeClass(Toggle):
    """If enabled, you'll be given one random class to play instead of choosing it yourself.
    The client shows which class you got."""
    display_name = "Randomize Starting Class"
    default = False


class LevelItems(Choice):
    """How your level cap goes up.
    Sequential: each "Maximum Level X" item unlocks one specific level cap.
    Progressive: each "Progressive Levels" item raises your level cap to the next step,
    in order."""
    display_name = "Progressive or Sequential Level Items"
    option_sequential = 0
    option_progressive = 1
    default = 1


class EasierTransitions(Choice):
    """If enabled, you need 2 zones for each level range instead of 1 before you can level
    into it, plus the first zone of a new expansion before entering it. You get more zones
    to choose from, but need more items to progress."""
    display_name = "Easier Transitions"
    option_false = 0
    option_true = 1
    default = 0


class PreOrPostCataclysm(Choice):
    """Cataclysm changed many old zones, including their level ranges. For example,
    Feralas is level 40-50 before Cataclysm and 35-40 after. Pick the version that matches
    your game: Pre-Cataclysm for Vanilla up to Wrath of the Lich King, Post-Cataclysm for
    Cataclysm and newer. Always Post-Cataclysm if your max level is above 80."""
    display_name = "Pre or Post Cataclysm"
    option_pre_cataclysm = 0
    option_post_cataclysm = 1
    default = 0


class GoldHuntAmount(Range):
    """If your goal is Gold Hunt, how much Gold you need to find in the pool to win."""
    display_name = "Gold Amount"
    range_start = 1
    range_end = 10
    default = 10


class IncludeDungeons(Toggle):
    """If enabled, adds the leveling dungeons as extra items. They're never required to
    progress."""
    display_name = "Include Dungeons"
    default = False


class IncludeAchievements(Toggle):
    """Only works on Wrath of the Lich King or newer.
    Adds extra checks from your character's Statistics: dying once, using your
    Hearthstone, taking a flight path, earning your first gold, and killing creatures,
    completing quests and catching fish. They get a bit harder as you level, up to level 60."""
    display_name = "Include Achievements"
    default = False


@dataclass
class WoWLevelingOptions(PerGameCommonOptions):
    # How you win.
    goal: Goal
    gold_hunt_amount: GoldHuntAmount
    # How leveling unlocks.
    max_level: MaxLevel
    level_items: LevelItems
    easier_transitions: EasierTransitions
    # Your character.
    faction: Faction
    randomize_class: RandomizeClass
    # Which version of the world.
    pre_or_post_cataclysm: PreOrPostCataclysm
    # Optional extras.
    include_dungeons: IncludeDungeons
    include_achievements: IncludeAchievements
