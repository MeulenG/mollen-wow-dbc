#ifndef SCHEMA_SPELL_ITEM_ENCHANTMENT_CONDITION_H
#define SCHEMA_SPELL_ITEM_ENCHANTMENT_CONDITION_H

#include "dbc_schema.h"

static const DbcFieldDef spell_item_enchantment_condition_fields[] = {
    { "Id",            DbcFieldType::UInt32 },
    { "LtOperandType1", DbcFieldType::UInt32 },
    { "LtOperandType2", DbcFieldType::UInt32 },
    { "LtOperandType3", DbcFieldType::UInt32 },
    { "LtOperandType4", DbcFieldType::UInt32 },
    { "LtOperandType5", DbcFieldType::UInt32 },
    { "LtOperand1",   DbcFieldType::UInt32 },
    { "LtOperand2",   DbcFieldType::UInt32 },
    { "LtOperand3",   DbcFieldType::UInt32 },
    { "LtOperand4",   DbcFieldType::UInt32 },
    { "LtOperand5",   DbcFieldType::UInt32 },
    { "Operator1",    DbcFieldType::UInt32 },
    { "Operator2",    DbcFieldType::UInt32 },
    { "Operator3",    DbcFieldType::UInt32 },
    { "Operator4",    DbcFieldType::UInt32 },
    { "Operator5",    DbcFieldType::UInt32 },
    { "RtOperandType1", DbcFieldType::UInt32 },
    { "RtOperandType2", DbcFieldType::UInt32 },
    { "RtOperandType3", DbcFieldType::UInt32 },
    { "RtOperandType4", DbcFieldType::UInt32 },
    { "RtOperandType5", DbcFieldType::UInt32 },
    { "RtOperand1",   DbcFieldType::UInt32 },
    { "RtOperand2",   DbcFieldType::UInt32 },
    { "RtOperand3",   DbcFieldType::UInt32 },
    { "RtOperand4",   DbcFieldType::UInt32 },
    { "RtOperand5",   DbcFieldType::UInt32 },
    { "Logic1",       DbcFieldType::UInt32 },
    { "Logic2",       DbcFieldType::UInt32 },
    { "Logic3",       DbcFieldType::UInt32 },
    { "Logic4",       DbcFieldType::UInt32 },
    { "Logic5",       DbcFieldType::UInt32 },
};

static const DbcSchema schema_spell_item_enchantment_condition = {
    "SpellItemEnchantmentCondition",
    spell_item_enchantment_condition_fields,
    sizeof(spell_item_enchantment_condition_fields) / sizeof(spell_item_enchantment_condition_fields[0])
};

#endif
