#ifndef ENUM_ITEM_FLAGS_H
#define ENUM_ITEM_FLAGS_H

#include "dbc_enum.h"

// Item.dbc Flags column. WotLK 3.3.5a — only the commonly-set bits are
// labeled here; unknown / engine-internal bits surface as raw hex in the
// editor when Bitmask rendering encounters them.
static const DbcEnumValue item_flags_values[] = {
    {        0x1, "No Pickup"            },
    {        0x2, "Conjured"             },
    {        0x4, "Openable"             },
    {        0x8, "Heroic"               },
    {       0x10, "Deprecated"           },
    {       0x20, "No Requirements"      },
    {       0x40, "Wrapper"              },
    {       0x80, "Party Loot"           },
    {      0x100, "Refundable"           },
    {      0x200, "Charter"              },
    {      0x400, "Pet Item"             },
    {      0x800, "Usable in Arena"      },
    {     0x1000, "Throwable"            },
    {     0x2000, "Special Use"          },
    {     0x4000, "Boa When Equipped"    },  // Bind on Account
    {     0x8000, "No Reagent Cost"      },
    {    0x10000, "Mill-able"            },
    {    0x20000, "Lookup By"            },
    {    0x40000, "Prospect-able"        },
    {    0x80000, "Unique-Equipped"      },
};

static const DbcEnum item_flags_enum = {
    "ItemFlags", item_flags_values,
    sizeof(item_flags_values) / sizeof(item_flags_values[0]) };

#endif
