#ifndef DBC_SCHEMA_H
#define DBC_SCHEMA_H

#include <cstdint>

enum class Expansion {
    Vanilla,
    TBC,
    WotLK,
};

enum class DbcFieldType {
    UInt32,
    Int32,
    Float,
    String,
};

struct DbcFieldDef {
    const char* name;
    DbcFieldType type;
};

struct DbcSchema {
    const char* dbc_name;
    const DbcFieldDef* fields;
    uint32_t field_count;
};

#endif // DBC_SCHEMA_H
