#include "enum_registry.h"

#include <cstring>

// One include per registered enum — adding a new enum is a two-line change:
// add the include here and append the table to the array below.
#include "enum_sex.h"
#include "enum_item_quality.h"
#include "enum_item_class.h"
#include "enum_inventory_type.h"
#include "enum_material.h"
#include "enum_sheath.h"
#include "enum_bonding.h"
#include "enum_spell_school.h"
#include "enum_power_type.h"
#include "enum_creature_type.h"
#include "enum_blood_level.h"
#include "enum_dispel_type.h"
#include "enum_race_mask.h"
#include "enum_class_mask.h"
#include "enum_spell_school_mask.h"
#include "enum_item_flags.h"

namespace {

const DbcEnum* const k_all_enums[] = {
    &sex_enum,
    &item_quality_enum,
    &item_class_enum,
    &inventory_type_enum,
    &material_enum,
    &sheath_enum,
    &bonding_enum,
    &spell_school_enum,
    &power_type_enum,
    &creature_type_enum,
    &blood_level_enum,
    &dispel_type_enum,
    &race_mask_enum,
    &class_mask_enum,
    &spell_school_mask_enum,
    &item_flags_enum,
};

constexpr uint32_t k_enum_count = sizeof(k_all_enums) / sizeof(k_all_enums[0]);

} // namespace

const DbcEnum* GetDbcEnum(const char* name) {
    if (!name) return nullptr;
    // Linear scan is fine — fewer than ~50 enums total expected, and lookups
    // happen at UI render time per cell, not in a hot loop.
    for (uint32_t i = 0; i < k_enum_count; i++) {
        if (std::strcmp(k_all_enums[i]->name, name) == 0) {
            return k_all_enums[i];
        }
    }
    return nullptr;
}

const DbcEnum* const* GetAllDbcEnums(uint32_t* count) {
    if (count) *count = k_enum_count;
    return k_all_enums;
}
