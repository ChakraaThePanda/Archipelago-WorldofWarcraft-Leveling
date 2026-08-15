from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range, Toggle

# Category tag (as used in Items.py's _RAW_ITEMS, e.g. "The Burning Crusade") for each Expansion
# option value below, in the same order. Also doubles as the ordered list of expansions,
# used to compute how many trailing "Progressive Levels" copies / expansion-locked items
# get dropped from the pool once a lower expansion is chosen.
EXPANSION_NAMES: list[str] = [
    "Vanilla",
    "The Burning Crusade",
    "Wrath of the Lich King",
    "Cataclysm",
    "Mists of Pandaria",
]
EXPANSION_CATACLYSM = 3


class Goal(Choice):
    """Select your goal for the randomizer.
    Leveling: reach the maximum level for your selected expansion (see the 'expansion' option).
    Gold Hunt: find a set amount of Gold in the item pool to win (see the 'gold_hunt_amount'
    option)."""
    display_name = "Selected Goal"
    option_leveling = 0
    option_gold_hunt = 1
    default = 0


class Expansion(Choice):
    """This affects which items/locations exist in the randomizer, to match the max level
    you want to reach.
    vanilla = Level 60
    the_burning_crusade = Level 70
    wrath_of_the_lich_king = Level 80
    cataclysm = Level 85
    mists_of_pandaria = Level 90"""
    display_name = "Selected Expansion"
    option_vanilla = 0
    option_the_burning_crusade = 1
    option_wrath_of_the_lich_king = 2
    option_cataclysm = 3
    option_mists_of_pandaria = 4
    default = 4


class Faction(Choice):
    """Choose your character faction. Affects which zones are available for you to quest in."""
    display_name = "Character Faction"
    option_alliance = 0
    option_horde = 1
    default = "random"


class RandomizeClass(Toggle):
    """If enabled, you'll be given a single random class to play instead of choosing one
    yourself -- check your client/slot data for which one you received. No Class items will
    appear in the pool."""
    display_name = "Randomize Starting Class"
    default = False


class LevelItems(Choice):
    """Progressive adds multiple "Progressive Levels" items to the pool instead of the
    individual "Maximum Level X" items -- each copy raises your level cap to the next
    bracket in sequence, rather than to one specific fixed level."""
    display_name = "Progressive or Sequential Level Items"
    option_sequential = 0
    option_progressive = 1
    default = 1


class EasierTransitions(Choice):
    """If enabled, logic expects 2 zone items per level bracket instead of 1, plus the first
    zone item of a new expansion before letting you cross into it. This gives you more zone
    choices for your level, at the cost of needing more items to progress."""
    display_name = "Easier Transitions"
    option_false = 0
    option_true = 1
    default = 0


class PreOrPostCataclysm(Choice):
    """Whether the zones reshaped by the Cataclysm expansion (e.g. Stranglethorn Vale,
    Desolace, Feralas, Thousand Needles) appear in their pre- or post-Cataclysm state in
    the pool. Forced to Post-Cataclysm if 'expansion' is set to Cataclysm or Mists of
    Pandaria, since those expansions assume the world has already changed."""
    display_name = "Pre or Post Cataclysm"
    option_pre_cataclysm = 0
    option_post_cataclysm = 1
    default = 1


class GoldHuntAmount(Range):
    """If your goal is Gold Hunt, how much Gold you need to find in the pool to win."""
    display_name = "Gold Amount"
    range_start = 1
    range_end = 10
    default = 10


class IncludeDungeons(Toggle):
    """If enabled, adds all the various leveling dungeons to the pool as filler items. This
    has no effect on logic -- only Maximum Level and Zone items matter for that."""
    display_name = "Include Dungeons"
    default = False


@dataclass
class WoWLevelingOptions(PerGameCommonOptions):
    goal: Goal
    expansion: Expansion
    faction: Faction
    randomize_class: RandomizeClass
    level_items: LevelItems
    easier_transitions: EasierTransitions
    pre_or_post_cataclysm: PreOrPostCataclysm
    gold_hunt_amount: GoldHuntAmount
    include_dungeons: IncludeDungeons
