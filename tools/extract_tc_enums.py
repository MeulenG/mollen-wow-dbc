#!/usr/bin/env python3
"""
Extract TrinityCore enum definitions into mollen-wow-dbc DbcEnum tables.

Pulls authoritative bit values and names from the TrinityCore 3.3.5 branch
(read via `git show` - no working-tree change required). Each TC enum becomes
one `enum_<snake>.h` file in our format with `Title Case` labels derived from
the SCREAMING_SNAKE source names.

This is a one-time codegen helper. The generated headers get hand-reviewed
and committed as the source of truth - re-running only matters if you want
to pick up newly-added bits when TC updates.

Usage:
    python tools/extract_tc_enums.py \\
        --tc C:/Users/Molle/Desktop/TrinityCore \\
        --branch origin/3.3.5 \\
        --out src/enums

    Use --dry-run to preview without writing files.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


# (file_in_tc, enum_name_in_tc, our_table_name)
# Table name is what the registry exposes; bitmask hints in schemas refer to it.
TARGETS: list[tuple[str, str, str]] = [
    # ---- Bitmasks ----
    ("src/server/game/Entities/Item/ItemTemplate.h",  "ItemFlags",                 "ItemFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "AchievementFlags",          "AchievementFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "AchievementCriteriaFlags",  "AchievementCriteriaFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "AreaFlags",                 "AreaFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "MapFlags",                  "MapFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "FactionTemplateFlags",      "FactionTemplateFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "VehicleSeatFlags",          "VehicleSeatFlags"),
    ("src/server/shared/DataStores/DBCEnums.h",       "VehicleSeatFlagsB",         "VehicleSeatFlagsB"),
    ("src/server/shared/DataStores/DBCEnums.h",       "SkillRaceClassInfoFlags",   "SkillRaceClassInfoFlags"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr0",                "SpellAttr0"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr1",                "SpellAttr1"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr2",                "SpellAttr2"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr3",                "SpellAttr3"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr4",                "SpellAttr4"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr5",                "SpellAttr5"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr6",                "SpellAttr6"),
    ("src/server/shared/SharedDefines.h",             "SpellAttr7",                "SpellAttr7"),
    ("src/server/shared/SharedDefines.h",             "CreatureTypeFlags",         "CreatureTypeFlags"),
    ("src/server/shared/SharedDefines.h",             "CharacterFlags",            "CharacterFlags"),
    ("src/server/shared/SharedDefines.h",             "UnitDynFlags",              "UnitDynFlags"),
    ("src/server/shared/SharedDefines.h",             "DungeonStatusFlag",         "DungeonStatusFlag"),

    # ---- Plain enums (not bitmasks). ----
    ("src/server/shared/SharedDefines.h",             "SpellEffects",              "SpellEffects"),
    ("src/server/game/Spells/Auras/SpellAuraDefines.h", "AuraType",                "SpellAuraType"),
    ("src/server/shared/SharedDefines.h",             "Races",                     "Race"),
    ("src/server/shared/SharedDefines.h",             "Classes",                   "Class"),
    ("src/server/shared/SharedDefines.h",             "Language",                  "Language"),
    ("src/server/shared/SharedDefines.h",             "SpellFamilyNames",          "SpellFamily"),
    ("src/server/shared/SharedDefines.h",             "SkillCategory",             "SkillCategory"),
    ("src/server/shared/SharedDefines.h",             "TotemCategory",             "TotemCategory"),
    ("src/server/shared/SharedDefines.h",             "CreatureEliteType",         "CreatureEliteType"),
]

# Tables we treat as bitmasks: filter out `_NONE = 0`-style entries because
# zero isn't a bit position. Plain enums keep value=0 entries (e.g.
# SpellSchool::Physical = 0 is meaningful).
def is_bitmask_table(name: str) -> bool:
    return ("Flags" in name or "Mask" in name
            or name.startswith("SpellAttr") or name.startswith("UnitDynFlag"))


ENUM_BLOCK_RE = re.compile(
    r'enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*\w+\s*)?\{(.+?)\}',
    re.DOTALL,
)

ENTRY_RE = re.compile(
    r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*([-+0-9xXa-fA-F]+)',
)

# TrinityCore annotates many enum entries with a UI-friendly title via a
# `// TITLE <text>` comment (sometimes followed by `DESCRIPTION <text>`).
# When present this is far more useful than the SCREAMING_SNAKE identifier
# (`SPELL_ATTR0_NEGATIVE_1` -> "Is negative spell"). We strip the trailing
# `@AttrX` disambiguator TC uses for unknown bits.
TITLE_RE = re.compile(r'//\s*TITLE\s+(.+?)(?=\s*DESCRIPTION\b|\s*$)')
TITLE_SUFFIX_RE = re.compile(r'\s*@\w+\s*$')


def tc_show(tc_path: Path, branch: str, file_path: str) -> str:
    """Read a file from a TC branch via `git show`."""
    res = subprocess.run(
        ["git", "-C", str(tc_path), "show", f"{branch}:{file_path}"],
        capture_output=True, text=True, check=True,
    )
    return res.stdout


# Names matching these patterns are treated as enum-list sentinels and skipped
# before common-prefix detection. TrinityCore terminates many enums with
# `TOTAL_FOO = N` or `MAX_FOO = N`; if we include those in the prefix scan
# they collapse the shared prefix to empty and the resulting labels keep
# their full `SPELL_EFFECT_` / `SPELL_AURA_` prefix. Skipping them gives us
# clean labels.
SENTINEL_RE = re.compile(r"^(TOTAL_|MAX_|LAST_)|_COUNT$|_END$")


def is_sentinel(name: str) -> bool:
    return bool(SENTINEL_RE.search(name))


def extract_enum_entries(source: str, enum_name: str
                         ) -> list[tuple[str, int, str | None]]:
    """
    Find the named enum in source and return its entries.

    Each entry is (NAME, value, title) where `title` is the TC `// TITLE ...`
    annotation if present, otherwise None.
    """
    for m in ENUM_BLOCK_RE.finditer(source):
        if m.group(1) != enum_name:
            continue
        body = m.group(2)
        entries: list[tuple[str, int, str | None]] = []
        for line in body.split("\n"):
            # Separate code part from comment so the value regex doesn't
            # have to deal with `//` text.
            if "//" in line:
                code, _, comment = line.partition("//")
                comment = "//" + comment
            else:
                code, comment = line, ""

            em = ENTRY_RE.match(code)
            if not em:
                continue
            name = em.group(1)
            try:
                value = int(em.group(2), 0)
            except ValueError:
                continue

            title: str | None = None
            if comment:
                tm = TITLE_RE.search(comment)
                if tm:
                    raw_title = tm.group(1).strip()
                    # Strip TC's "@AttrX" disambiguator on Unknown entries.
                    title = TITLE_SUFFIX_RE.sub("", raw_title)

            if is_sentinel(name):
                continue  # skip TOTAL_*, MAX_*, etc. so common-prefix works
            entries.append((name, value, title))
        return entries
    return []


def common_prefix(names: list[str]) -> str:
    """Return the longest SCREAMING_SNAKE prefix shared by every name."""
    if not names:
        return ""
    parts_lists = [n.split("_") for n in names]
    common: list[str] = []
    for parts in zip(*parts_lists):
        if len(set(parts)) == 1:
            common.append(parts[0])
        else:
            break
    return "_".join(common) + "_" if common else ""


def humanize(snake: str) -> str:
    """SCREAMING_SNAKE -> Title Case with spaces."""
    parts = [p for p in snake.split("_") if p]
    return " ".join(p.capitalize() for p in parts)


def camel_to_snake(name: str) -> str:
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name)
    return s.lower()


def emit_header(table_name: str,
                entries: list[tuple[str, int, str | None]],
                source_info: str) -> str:
    snake_table = camel_to_snake(table_name)
    upper_table = snake_table.upper()
    bitmask = is_bitmask_table(table_name)

    # Skip value=0 entries on bitmasks (they're "no flags").
    filtered = [(n, v, t) for (n, v, t) in entries if not (bitmask and v == 0)]
    if not filtered:
        return ""

    prefix = common_prefix([n for n, _, _ in filtered])
    rows: list[tuple[int, str]] = []
    seen_values: set[int] = set()
    for name, val, title in filtered:
        if val in seen_values:
            continue  # skip duplicate-value aliases
        seen_values.add(val)
        # Prefer TC's `// TITLE` annotation when present - it's purpose-built
        # for UI display. Fall back to humanizing the identifier.
        if title:
            label = title
        else:
            stripped = name[len(prefix):] if name.startswith(prefix) else name
            label = humanize(stripped) or stripped
        rows.append((val, label))

    if not rows:
        return ""

    # Bitmasks render as hex (matches the source style); plain enums as decimal.
    max_label = max(len(label) for _, label in rows)
    out_lines = [
        f"#ifndef ENUM_{upper_table}_H",
        f"#define ENUM_{upper_table}_H",
        "",
        '#include "dbc_enum.h"',
        "",
        f"// Extracted from TrinityCore 3.3.5 ({source_info}).",
        "// Generated by tools/extract_tc_enums.py -- re-run to refresh.",
        "//",
        "// Each entry is (bit value, display label). Labels are derived from",
        "// the SCREAMING_SNAKE source name with the common prefix stripped.",
        f"static const DbcEnumValue {snake_table}_values[] = {{",
    ]
    for val, label in rows:
        if bitmask:
            num = f"0x{val:08X}"
        else:
            num = str(val)
        pad = " " * (max_label - len(label))
        out_lines.append(f'    {{ {num:>10}, "{label}"{pad} }},')
    out_lines.extend([
        "};",
        "",
        f"static const DbcEnum {snake_table}_enum = {{",
        f'    "{table_name}", {snake_table}_values,',
        f"    sizeof({snake_table}_values) / sizeof({snake_table}_values[0]) }};",
        "",
        "#endif",
        "",
    ])
    return "\n".join(out_lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tc", required=True, help="path to TrinityCore checkout")
    ap.add_argument("--branch", default="origin/3.3.5",
                    help="git ref to read from (default: origin/3.3.5)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be generated, don't write files")
    args = ap.parse_args()

    tc_path = Path(args.tc)
    if not tc_path.is_dir():
        print(f"error: {tc_path} is not a directory", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    successes: list[tuple[str, int, Path]] = []
    failures: list[tuple[str, str]] = []

    # Cache TC file contents so we don't `git show` the same file repeatedly.
    file_cache: dict[str, str] = {}

    for file_path, enum_name, table_name in TARGETS:
        if file_path not in file_cache:
            try:
                file_cache[file_path] = tc_show(tc_path, args.branch, file_path)
            except subprocess.CalledProcessError as e:
                failures.append((enum_name, f"git show failed: {e.stderr.strip()}"))
                continue

        entries = extract_enum_entries(file_cache[file_path], enum_name)
        if not entries:
            failures.append((enum_name, "enum not found or empty"))
            continue

        content = emit_header(table_name, entries,
                              f"{enum_name} in {file_path}")
        if not content:
            failures.append((enum_name, "no usable entries after filtering"))
            continue

        snake = camel_to_snake(table_name)
        out_path = out_dir / f"enum_{snake}.h"

        if args.dry_run:
            print(f"--- {out_path.name} ({len(entries)} src, {content.count(' }')} kept) ---")
            head = "\n".join(content.split("\n")[:14])
            print(head)
            print("    ...")
            print()
        else:
            out_path.write_text(content, encoding="utf-8")

        kept = content.count("\n    { ")
        successes.append((enum_name, kept, out_path))

    verb = "would generate" if args.dry_run else "generated"
    print(f"\n{verb} {len(successes)} files:")
    for name, count, path in successes:
        print(f"  {name:32} {count:3} entries  ->  {path.name}")
    if failures:
        print("\nFailures:")
        for name, reason in failures:
            print(f"  {name}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
