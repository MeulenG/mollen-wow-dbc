#ifndef DBC_FILE_H
#define DBC_FILE_H

#include <cstdint>

#define DBC_MAGIC 0x43424457

struct dbc_header {
    uint32_t magic;
    uint32_t record_count;
    uint32_t field_count;
    uint32_t record_size;
    uint32_t string_block_size;
};

class DbcFile {
public:
    DbcFile();

    bool Load(const uint8_t* data, uint32_t size);

    uint32_t GetRecordCount() const;
    uint32_t GetFieldCount() const;
    uint32_t GetRecordSize() const;
    uint32_t GetStringBlockSize() const;

    const uint8_t* GetRecord(uint32_t index) const;
    const char* GetString(uint32_t offset) const;

    uint32_t GetUInt32(uint32_t record, uint32_t field) const;
    int32_t GetInt32(uint32_t record, uint32_t field) const;
    float GetFloat(uint32_t record, uint32_t field) const;
    const char* GetStringField(uint32_t record, uint32_t field) const;

private:
    dbc_header header_;
    const uint8_t* record_data_;
    const char* string_block_;
    uint32_t data_size_;
};

#endif // DBC_FILE_H
