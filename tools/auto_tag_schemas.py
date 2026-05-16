#!/usr/bin/env python3
"""
Auto-tag WotLK DBC schemas with DbcSemantic annotations.

Walks src/schemas/wotlk/schema_*.h and rewrites field array entries that
have only the 2-element {name, type} form, adding a heuristic semantic
annotation and (where confident) an enum/FK hint:

    { "Sex",       DbcFieldType::UInt32 },
    -- becomes -->
    { "Sex",       DbcFieldType::UInt32, DbcSemantic::Enum, "Sex" },

The script is **idempotent** — fields that already carry an annotation are
detected by argument count and left untouched. So you can re-run after
hand-editing without clobbering manual fixes.

Usage:
    python tools/auto_tag_schemas.py [--dry-run] [--diff] [--dir <path>]

Heuristics are intentionally conservative. When in doubt the script leaves
a field as Default — it's better to under-annotate and review-then-fix than
to mis-tag and have wrong widgets in the editor.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


# --- Locales recognized as members of a 16-locale string cluster ---
# WotLK uses these as suffixes on localized name/description fields.
LOCALES = {
    "enUS", "koKR", "frFR", "deDE", "enCN", "enTW", "zhTW",
    "esES", "esMX", "ruRU", "jaJP", "ptPT", "itIT",
    "Unk1", "Unk2", "Unk3", "Unk4",
    "lang",  # consolidated single-locale field used in some schemas
}

# --- Exact field-name -> enum lookup table ---
# These names uniquely identify a registered enum across all DBCs.
ENUM_BY_EXACT_NAME = {
    "Sex":            "Sex",
    "SexID":          "Sex",
    "Quality":        "ItemQuality",
    "InventoryType":  "InventoryType",
    "BloodLevelID":   "BloodLevel",
    "DispelType":     "DispelType",
    "Sheath":         "Sheath",
    "SheatheType":    "Sheath",
    "Material":       "Material",
    "Bonding":        "Bonding",
    "PowerType":      "PowerType",
    "CreatureType":   "CreatureType",
}

# --- Foreign-key inferences ---
# When a field ends in "ID", we usually know what table it points at. The
# default heuristic strips "ID" and lowercases. Overrides handle the cases
# where that wouldn't yield the right table name.
FK_TARGET_OVERRIDES = {
    "RaceID":          "chrraces",
    "ClassID":         "chrclasses",
    "FactionID":       "faction",
    "FactionGroupID":  "factiongroup",
    "DisplayInfoID":   "creaturedisplayinfo",  # default — Item.dbc overrides below
    "DisplayID":       "creaturedisplayinfo",
    "MaleDisplayID":   "creaturedisplayinfo",
    "FemaleDisplayID": "creaturedisplayinfo",
    "ModelID":         "creaturemodeldata",
    "SoundID":         "soundentries",
    "NPCSoundID":      "npcsounds",
    "BaseLanguage":    "languages",
    "LanguageID":      "languages",
    "AreaID":          "areatable",
    "MapID":           "map",
    "ZoneID":          "areatable",
    "SkillLineID":     "skillline",
    "ItemID":          "item",
    "SpellID":         "spell",
    "QuestID":         "questv2",  # there may be no questv2 table; fix in review
    "AchievementID":   "achievement",
    "TitleID":         "chartitles",
}

# Per-schema FK hint overrides. Some fields like "DisplayInfoID" mean
# different tables depending on which schema they live in.
FK_BY_SCHEMA = {
    "schema_item": {
        "DisplayInfoID":  "itemdisplayinfo",
    },
    "schema_item_set": {
        "ItemID": "item",
    },
}

# Per-schema bitmask hints. A field with this name in this schema gets the
# specified enum table as its hint. Hints reference tables registered in
# src/enums/enum_registry.cpp. Most come from TrinityCore 3.3.5 source.
# Per-schema (regex-on-field-name, category, default_hidden) rules. The first
# matching rule for a field wins. Aimed primarily at Spell.dbc where 234
# columns benefit hugely from sectioning; other DBCs fall through to
# DEFAULT_CATEGORY_RULES below.
import re as _re_for_categories  # local alias to keep grouping clear

CATEGORY_RULES: dict[str, list[tuple[_re_for_categories.Pattern, str, bool]]] = {
    "schema_spell": [
        # --- Identity / display
        (_re_for_categories.compile(r"^(SpellName|Rank|Description|ToolTip)"), "Identity", False),
        (_re_for_categories.compile(r"^(spellicon|activeicon|ActiveIconID)$"), "Identity", False),
        (_re_for_categories.compile(r"^(SpellNameFlag|RankFlags|DescriptionFlags|ToolTipFlags)$"), "Identity", True),

        # --- Cost & cooldown
        (_re_for_categories.compile(r"^Mana"), "Cast", False),
        (_re_for_categories.compile(r"^(PowerType|PowerDisplayId|RuneCostID)$"), "Cast", False),
        (_re_for_categories.compile(r"^(CastingTimeIndex|RangeIndex|DurationIndex)$"), "Cast", False),
        (_re_for_categories.compile(r"^(Recovery|CategoryRecovery|StartRecovery)"), "Cast", False),

        # --- Targeting
        (_re_for_categories.compile(r"^(Targets|TargetCreatureType|MaxAffectedTargets|MaxTargetLevel|FacingCasterFlags|RequiresSpellFocus)$"), "Targeting", False),

        # --- Attributes bitmasks
        (_re_for_categories.compile(r"^Attributes(Ex\d*)?$"), "Attributes", False),

        # --- Conditions (preconditions, equipment, restrictions)
        (_re_for_categories.compile(r"^Stances"), "Conditions", False),
        (_re_for_categories.compile(r"^(Caster|Target|Exclude(Caster|Target))Aura(Spell|State|StateNot)$"), "Conditions", True),
        (_re_for_categories.compile(r"^EquippedItem"), "Conditions", True),
        (_re_for_categories.compile(r"^(MinFactionId|MinReputation|RequiredAuraVision|AreaGroupId)$"), "Conditions", True),

        # --- Effects: slot 1 visible by default, 2 and 3 hidden
        (_re_for_categories.compile(r"^(Effect[A-Za-z]*|DmgMultiplier)1$"), "Effects", False),
        (_re_for_categories.compile(r"^(Effect[A-Za-z]*|DmgMultiplier)[23]$"), "Effects", True),

        # --- Proc & interrupt
        (_re_for_categories.compile(r"^Proc"), "Proc", False),
        (_re_for_categories.compile(r"^(InterruptFlags|AuraInterruptFlags|ChannelInterruptFlags|PreventionType|StackAmount)$"), "Proc", False),

        # --- Reagents (incl totems as a sub-group)
        (_re_for_categories.compile(r"^Reagent"), "Reagents", False),
        (_re_for_categories.compile(r"^Totem"), "Reagents", False),

        # --- Visuals
        (_re_for_categories.compile(r"^SpellVisual"), "Visuals", False),
        (_re_for_categories.compile(r"^(SpellMissileID|spellmissile)$"), "Visuals", False),

        # --- Classification
        (_re_for_categories.compile(r"^(Dispel|Mechanic|SchoolMask|SpellFamilyName|SpellFamilyFlags\d*|DmgClass|Category)$"), "Classification", False),

        # --- Advanced / niche
        (_re_for_categories.compile(r"^(ModalNextSpell|SpellPriority|StanceBarOrder|SpellDescriptionVariableID|SpellDifficultyId|MaxLevel|BaseLevel|SpellLevel)$"), "Advanced", True),
    ],
}

# Fallback rules applied to every other schema. Conservative — only assigns
# obvious categories so we don't mis-label unfamiliar DBCs.
DEFAULT_CATEGORY_RULES: list[tuple[_re_for_categories.Pattern, str, bool]] = [
    # Identity-ish
    (_re_for_categories.compile(r"^(Id|Name|DisplayName|Title|Rank|Description|ToolTip)"), "Identity", False),
    (_re_for_categories.compile(r".*_(enUS|koKR|frFR|deDE|enCN|enTW|zhTW|esES|esMX|ruRU|jaJP|ptPT|itIT|Unk[1-4]|lang)$"), "Identity", False),

    # Visuals / assets
    (_re_for_categories.compile(r".*(Color|Colour|Icon|Sound|Music|Texture|Visual|Display)"), "Visuals", False),

    # Classification
    (_re_for_categories.compile(r"^Flags$"), "Classification", False),
]


BITMASK_BY_SCHEMA = {
    "schema_item":                      {"Flags": "ItemFlags"},
    "schema_achievement":               {"Flags": "AchievementFlags"},
    "schema_achievement_criteria":      {"Flags": "AchievementCriteriaFlags"},
    "schema_area_table":                {"Flags": "AreaFlags"},
    "schema_map":                       {"Flags": "MapFlags"},
    "schema_faction_template":          {"Flags": "FactionTemplateFlags"},
    "schema_vehicle_seat":              {"Flags": "VehicleSeatFlags",
                                         "FlagsB": "VehicleSeatFlagsB"},
    "schema_skill_race_class_info":     {"Flags": "SkillRaceClassInfoFlags"},
    "schema_creature_family":           {"PetFoodMask": None},  # bitmask but no named enum
    "schema_chr_races":                 {"Flags": "CharacterFlags"},
    "schema_dungeon_encounter":         {"Flags": "DungeonStatusFlag"},
    "schema_spell": {
        "Attributes":    "SpellAttr0",
        "AttributesEx":  "SpellAttr1",
        "AttributesEx2": "SpellAttr2",
        "AttributesEx3": "SpellAttr3",
        "AttributesEx4": "SpellAttr4",
        "AttributesEx5": "SpellAttr5",
        "AttributesEx6": "SpellAttr6",
        "AttributesEx7": "SpellAttr7",
    },
}

# Per-schema enum hints. Like ENUM_BY_SCHEMA but applied to fields that
# weren't picked up by the generic bitmask/enum heuristics. Used for
# per-effect-slot Effect type + Aura name fields.
EFFECT_ENUMS_BY_SCHEMA = {
    "schema_spell": {
        "Effect1":              "SpellEffects",
        "Effect2":              "SpellEffects",
        "Effect3":              "SpellEffects",
        "EffectApplyAuraName1": "SpellAuraType",
        "EffectApplyAuraName2": "SpellAuraType",
        "EffectApplyAuraName3": "SpellAuraType",
    },
}

# Per-schema enum overrides. Used when an exact field name means different
# things in different DBCs. Most notable: `ClassID` is the character class FK
# in PvP/Talent/etc., but means ItemClass enum in Item.dbc and ItemSubClass.
ENUM_BY_SCHEMA = {
    "schema_item": {
        "ClassID":     "ItemClass",
        "SubclassID":  None,  # too schema-dependent to enum
    },
    "schema_item_subclass": {
        "ClassID": "ItemClass",
    },
    "schema_item_subclass_mask": {
        "ClassID": "ItemClass",
    },
}

# Fields whose name strongly suggests boolean semantics regardless of type.
# Most are stored as UInt32 with values 0 or 1.
BOOLEAN_NAMES = {
    "Bald", "IsBald", "Visible", "Hidden", "Enabled", "IsActive",
    "IsAvailable", "Show", "InternalOnly", "AlternateRace",
}

# Substrings that, when present in a UInt32 field name, mark it as a Color.
COLOR_HINTS = ("Color", "Colour")

# Bitmask hint mapping by exact field name. Other Flags fields fall through
# to bitmask-with-no-hint (renderer shows raw hex bits).
BITMASK_HINTS = {
    "SchoolMask":           "SpellSchoolMask",
    "RaceMask":             "RaceMask",
    "ClassMask":            "ClassMask",
    "AllowableRace":        "RaceMask",
    "AllowableClass":       "ClassMask",
}


# Matches every form a field-array entry can be in:
#   { "Name", DbcFieldType::T }
#   { "Name", DbcFieldType::T, DbcSemantic::S }
#   { "Name", DbcFieldType::T, DbcSemantic::S, "hint" }
#   { "Name", DbcFieldType::T, DbcSemantic::S, "hint", "category" }
#   { "Name", DbcFieldType::T, DbcSemantic::S, "hint", "category", true }
# Intermediate slots can be `nullptr` when a later slot is set without an
# earlier one (e.g. category set on a Default-semantic field).
FIELD_RE = re.compile(
    r'^(?P<indent>\s*)\{\s*"(?P<name>[^"]+)"\s*,\s*'
    r'DbcFieldType::(?P<type>\w+)'
    r'(?:\s*,\s*DbcSemantic::(?P<sem>\w+)'
    r'(?:\s*,\s*(?:"(?P<hint>[^"]*)"|nullptr)'
    r'(?:\s*,\s*(?:"(?P<category>[^"]*)"|nullptr)'
    r'(?:\s*,\s*(?P<hidden>true|false))?'
    r')?'
    r')?'
    r')?'
    r'\s*\}(?P<trailing>\s*,?\s*)$',
    re.MULTILINE,
)


def split_locale(name: str) -> Optional[tuple[str, str]]:
    """Return (base, locale) if `name` ends in a known locale suffix."""
    if "_" not in name:
        return None
    base, _, suffix = name.rpartition("_")
    if suffix in LOCALES:
        return base, suffix
    return None


def infer(name: str, ftype: str, schema_id: str) -> Optional[tuple[str, Optional[str]]]:
    """
    Return (semantic, hint) or None if no annotation should be added.

    schema_id is the file stem (e.g. "schema_item") used for context-specific
    overrides.
    """
    # Boolean by name list
    if name in BOOLEAN_NAMES:
        return ("Boolean", None)

    # Localized string cluster
    locale = split_locale(name)
    if locale is not None:
        # hint = base name so the editor can group all 16 locales together.
        return ("LocalizedString", locale[0])

    # Color by substring — but NOT for fields ending in "ID" (those are FK
    # references TO a color, not a packed color value), and not for "Index"
    # variants which are also referencing rows elsewhere.
    if (ftype == "UInt32" and any(h in name for h in COLOR_HINTS)
            and not name.endswith("ID") and not name.endswith("Index")):
        return ("Color", None)

    # Bitmask: per-schema override > generic name match > shape-only fallback.
    per_schema_bm = BITMASK_BY_SCHEMA.get(schema_id, {})
    if name in per_schema_bm:
        return ("Bitmask", per_schema_bm[name])
    if name in BITMASK_HINTS:
        return ("Bitmask", BITMASK_HINTS[name])
    if name == "Flags" or name.endswith("Flags") or name.endswith("Mask"):
        return ("Bitmask", None)

    # Per-schema effect-enum hints (Effect type, AuraName)
    eff_enum = EFFECT_ENUMS_BY_SCHEMA.get(schema_id, {})
    if name in eff_enum:
        return ("Enum", eff_enum[name])

    # Per-schema enum override (e.g. Item.ClassID -> ItemClass)
    per_schema_enum = ENUM_BY_SCHEMA.get(schema_id, {})
    if name in per_schema_enum:
        target = per_schema_enum[name]
        if target is None:
            return None  # schema-explicit "leave as default"
        return ("Enum", target)

    # Specifically-named enum fields (global)
    if name in ENUM_BY_EXACT_NAME:
        return ("Enum", ENUM_BY_EXACT_NAME[name])

    # Foreign keys by ID suffix. Skip the "Id" primary key (always first).
    if name.endswith("ID") and name not in ("ID",):
        # Per-schema override?
        per_schema = FK_BY_SCHEMA.get(schema_id, {})
        if name in per_schema:
            return ("ForeignKey", per_schema[name])
        if name in FK_TARGET_OVERRIDES:
            return ("ForeignKey", FK_TARGET_OVERRIDES[name])
        # Default: strip "ID", lowercase.
        guess = name[:-2].lower()
        if guess:
            return ("ForeignKey", guess)
        return None

    # The literal "Id" primary key — leave Default.
    if name == "Id":
        return None

    return None


def categorize(name: str, schema_id: str) -> tuple[Optional[str], bool]:
    """Pick (category, default_hidden) for a field. Empty (None, False) if no rule matches."""
    schema_rules = CATEGORY_RULES.get(schema_id, [])
    for pat, category, hidden in schema_rules:
        if pat.match(name):
            return (category, hidden)
    # Fallback rules — only apply when no per-schema rule fired.
    for pat, category, hidden in DEFAULT_CATEGORY_RULES:
        if pat.match(name):
            return (category, hidden)
    return (None, False)


def emit_field(indent: str, name: str, ftype: str,
               semantic: Optional[str], hint: Optional[str],
               category: Optional[str], hidden: bool,
               trailing: str) -> str:
    """Render a field-array entry using the shortest form that captures all set fields."""
    parts = [f'"{name}"', f'DbcFieldType::{ftype}']

    # Each later slot forces all earlier slots to be present (positional args).
    need_sem = bool(semantic) or hint or category or hidden
    need_hint = hint is not None or category or hidden
    need_cat = category is not None or hidden
    need_hidden = hidden

    if need_sem:
        parts.append(f'DbcSemantic::{semantic or "Default"}')
    if need_hint:
        parts.append(f'"{hint}"' if hint else "nullptr")
    if need_cat:
        parts.append(f'"{category}"' if category else "nullptr")
    if need_hidden:
        parts.append("true")  # we never emit "false" — bool defaults to false

    return f'{indent}{{ {", ".join(parts)} }}{trailing}'


def annotate(text: str, schema_id: str) -> tuple[str, list[str]]:
    """Apply infer() to every 2-element field line. Returns (new_text, log)."""
    log: list[str] = []

    def replace(m: re.Match) -> str:
        indent   = m.group("indent")
        name     = m.group("name")
        ftype    = m.group("type")
        existing_sem  = m.group("sem")
        existing_hint = m.group("hint")
        existing_cat  = m.group("category")
        existing_hid  = m.group("hidden") == "true"
        trailing = m.group("trailing")

        # ---- Semantic / hint inference ----
        # Existing semantic+hint is treated as hand-tuned and preserved.
        # If only semantic is set, the tagger may add a hint.
        if existing_sem and existing_hint:
            semantic = existing_sem
            hint = existing_hint
        else:
            inferred = infer(name, ftype, schema_id)
            if inferred is None:
                semantic = existing_sem  # may be None
                hint = None
            else:
                semantic, hint = inferred

        # ---- Category / hidden inference ----
        # Existing values win — categorize() only fills blanks.
        if existing_cat:
            category = existing_cat
            hidden = existing_hid
        else:
            inferred_cat, inferred_hid = categorize(name, schema_id)
            category = inferred_cat
            hidden = existing_hid or inferred_hid

        new_line = emit_field(indent, name, ftype, semantic, hint,
                              category, hidden, trailing)

        if new_line == m.group(0):
            return m.group(0)

        changes = []
        if semantic and semantic != existing_sem:
            changes.append(f"sem={semantic}")
        if hint and hint != existing_hint:
            changes.append(f'hint="{hint}"')
        if category and category != existing_cat:
            changes.append(f'cat="{category}"')
        if hidden and not existing_hid:
            changes.append("hidden")
        if changes:
            log.append(f"  {name:<30} -> {', '.join(changes)}")
        return new_line

    new_text = FIELD_RE.sub(replace, text)
    return new_text, log


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default="src/schemas/wotlk",
                        help="schema directory (default: src/schemas/wotlk)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print summary, don't modify files")
    parser.add_argument("--diff", action="store_true",
                        help="print full per-file change log")
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    files = sorted(root.glob("schema_*.h"))
    if not files:
        print(f"error: no schema_*.h files under {root}", file=sys.stderr)
        return 1

    total_changed = 0
    total_files = 0
    for path in files:
        original = path.read_text(encoding="utf-8")
        schema_id = path.stem  # e.g. "schema_item"
        new, log = annotate(original, schema_id)
        if not log:
            continue

        total_files += 1
        total_changed += len(log)

        if args.diff:
            print(f"\n{path.name} ({len(log)} fields):")
            for line in log:
                print(line)

        if not args.dry_run:
            path.write_text(new, encoding="utf-8")

    verb = "would tag" if args.dry_run else "tagged"
    print(f"\n{verb} {total_changed} fields across {total_files} schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
