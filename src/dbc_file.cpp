#include "dbc_file.h"
#include <cstring>

DbcFile::DbcFile()
    : header_{}, record_data_(nullptr), string_block_(nullptr), data_size_(0) {
}

bool DbcFile::Load(const uint8_t* data, uint32_t size) {
    if (size < sizeof(dbc_header)) {
        return false;
    }

    memcpy(&header_, data, sizeof(dbc_header));

    if (header_.magic != DBC_MAGIC) {
        return false;
    }

    uint32_t expected_size = sizeof(dbc_header)
                           + (header_.record_count * header_.record_size)
                           + header_.string_block_size;
    if (size < expected_size) {
        return false;
    }

    record_data_ = data + sizeof(dbc_header);
    string_block_ = reinterpret_cast<const char*>(record_data_
                  + (header_.record_count * header_.record_size));
    data_size_ = size;

    return true;
}

uint32_t DbcFile::GetRecordCount() const {
    return header_.record_count;
}

uint32_t DbcFile::GetFieldCount() const {
    return header_.field_count;
}

uint32_t DbcFile::GetRecordSize() const {
    return header_.record_size;
}

uint32_t DbcFile::GetStringBlockSize() const {
    return header_.string_block_size;
}

const uint8_t* DbcFile::GetRecord(uint32_t index) const {
    if (index >= header_.record_count) {
        return nullptr;
    }
    return record_data_ + (index * header_.record_size);
}

const char* DbcFile::GetString(uint32_t offset) const {
    if (offset >= header_.string_block_size) {
        return "";
    }
    return string_block_ + offset;
}

uint32_t DbcFile::GetUInt32(uint32_t record, uint32_t field) const {
    const uint8_t* row = GetRecord(record);
    if (!row || field >= header_.field_count) {
        return 0;
    }
    uint32_t value;
    memcpy(&value, row + (field * sizeof(uint32_t)), sizeof(uint32_t));
    return value;
}

int32_t DbcFile::GetInt32(uint32_t record, uint32_t field) const {
    const uint8_t* row = GetRecord(record);
    if (!row || field >= header_.field_count) {
        return 0;
    }
    int32_t value;
    memcpy(&value, row + (field * sizeof(uint32_t)), sizeof(int32_t));
    return value;
}

float DbcFile::GetFloat(uint32_t record, uint32_t field) const {
    const uint8_t* row = GetRecord(record);
    if (!row || field >= header_.field_count) {
        return 0.0f;
    }
    float value;
    memcpy(&value, row + (field * sizeof(uint32_t)), sizeof(float));
    return value;
}

const char* DbcFile::GetStringField(uint32_t record, uint32_t field) const {
    uint32_t offset = GetUInt32(record, field);
    return GetString(offset);
}
