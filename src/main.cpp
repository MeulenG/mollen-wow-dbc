#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <map>
#include <filesystem>
#include <algorithm>

#include "mpq_archive.h"
#include "dbc_file.h"
#include "schema_registry.h"
#include "dbc_generator.h"

namespace fs = std::filesystem;

static void PrintUsage(const char* program) {
    printf("Usage: %s <data_dir> [--expansion <vanilla|tbc|wotlk>] [--locale <enUS|...>] [--generate <output_dir>] [dbc_name]\n", program);
    printf("  data_dir    Path to WoW Data directory containing MPQ files\n");
    printf("  --expansion Target expansion (default: wotlk)\n");
    printf("  --locale    Locale subdirectory to include (default: enUS)\n");
    printf("  --generate  Generate C++ headers to output directory\n");
    printf("  dbc_name    Optional: extract only this DBC (e.g. Spell)\n");
}

static std::string GetDbcName(const std::string& path) {
    size_t slash = path.find_last_of("\\/");
    std::string filename = path;
    if (slash != std::string::npos) {
        filename = path.substr(slash + 1);
    }

    size_t dot = filename.find_last_of('.');
    if (dot != std::string::npos) {
        filename = filename.substr(0, dot);
    }
    return filename;
}

static void DumpDbc(const DbcFile& dbc, const DbcSchema* schema) {
    printf("  Records: %u, Fields: %u, Record Size: %u\n",
           dbc.GetRecordCount(), dbc.GetFieldCount(), dbc.GetRecordSize());

    if (!schema) {
        printf("  (no schema registered, showing raw field count only)\n");
        return;
    }

    if (schema->field_count != dbc.GetFieldCount()) {
        printf("  WARNING: schema has %u fields, DBC has %u fields\n",
               schema->field_count, dbc.GetFieldCount());
    }

    uint32_t preview_count = 3;
    if (dbc.GetRecordCount() < preview_count) {
        preview_count = dbc.GetRecordCount();
    }

    for (uint32_t r = 0; r < preview_count; r++) {
        printf("  Row %u: ID=%u", r, dbc.GetUInt32(r, 0));

        for (uint32_t f = 1; f < schema->field_count && f < 5; f++) {
            switch (schema->fields[f].type) {
            case DbcFieldType::String:
                printf(", %s=\"%s\"", schema->fields[f].name, dbc.GetStringField(r, f));
                break;
            case DbcFieldType::Float:
                printf(", %s=%.2f", schema->fields[f].name, dbc.GetFloat(r, f));
                break;
            case DbcFieldType::Int32:
                printf(", %s=%d", schema->fields[f].name, dbc.GetInt32(r, f));
                break;
            default:
                printf(", %s=%u", schema->fields[f].name, dbc.GetUInt32(r, f));
                break;
            }
        }
        printf("\n");
    }

    if (dbc.GetRecordCount() > preview_count) {
        printf("  ... (%u more rows)\n", dbc.GetRecordCount() - preview_count);
    }
}

static Expansion ParseExpansion(const char* str) {
    if (strcmp(str, "vanilla") == 0) {
        return Expansion::Vanilla;
    }
    if (strcmp(str, "tbc") == 0) {
        return Expansion::TBC;
    }
    if (strcmp(str, "wotlk") == 0) {
        return Expansion::WotLK;
    }
    return Expansion::WotLK;
}

static const char* ExpansionName(Expansion exp) {
    switch (exp) {
    case Expansion::Vanilla:
        return "vanilla";
    case Expansion::TBC:
        return "tbc";
    case Expansion::WotLK:
        return "wotlk";
    }
    return "unknown";
}

static int MpqLoadOrder(const std::string& name) {
    if (name.find("common") == 0) {
        return 0;
    }
    if (name.find("expansion") == 0) {
        return 1;
    }
    if (name.find("lichking") == 0) {
        return 2;
    }
    if (name.find("locale-") == 0) {
        return 3;
    }
    if (name.find("lichking-locale") == 0) {
        return 4;
    }
    if (name.find("lichking-speech") == 0) {
        return 5;
    }
    if (name.find("speech-") == 0) {
        return 5;
    }
    if (name.find("wow-update") == 0) {
        return 6;
    }
    if (name.find("patch") == 0) {
        return 7;
    }
    return 99;
}

static std::vector<fs::path> CollectMpqs(const fs::path& data_dir, const std::string& locale) {
    std::vector<fs::path> mpqs;

    for (const auto& entry : fs::directory_iterator(data_dir)) {
        if (!entry.is_regular_file()) {
            continue;
        }
        auto ext = entry.path().extension().string();
        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
        if (ext == ".mpq") {
            mpqs.push_back(entry.path());
        }
    }

    fs::path locale_dir = data_dir / locale;
    if (fs::is_directory(locale_dir)) {
        for (const auto& entry : fs::directory_iterator(locale_dir)) {
            if (!entry.is_regular_file()) {
                continue;
            }
            auto ext = entry.path().extension().string();
            std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
            if (ext == ".mpq") {
                mpqs.push_back(entry.path());
            }
        }
    }

    std::sort(mpqs.begin(), mpqs.end(), [](const fs::path& a, const fs::path& b) {
        std::string na = a.stem().string();
        std::string nb = b.stem().string();
        std::transform(na.begin(), na.end(), na.begin(), ::tolower);
        std::transform(nb.begin(), nb.end(), nb.begin(), ::tolower);
        int oa = MpqLoadOrder(na);
        int ob = MpqLoadOrder(nb);
        if (oa != ob) {
            return oa < ob;
        }
        return na < nb;
    });

    return mpqs;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        PrintUsage(argv[0]);
        return 1;
    }

    const char* data_dir = nullptr;
    const char* target_dbc = nullptr;
    const char* locale = "enUS";
    const char* generate_dir = nullptr;
    Expansion expansion = Expansion::WotLK;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--expansion") == 0) {
            if (i + 1 < argc) {
                expansion = ParseExpansion(argv[++i]);
            } else {
                printf("Error: --expansion requires a value (vanilla, tbc, wotlk)\n");
                return 1;
            }
        } else if (strcmp(argv[i], "--locale") == 0) {
            if (i + 1 < argc) {
                locale = argv[++i];
            } else {
                printf("Error: --locale requires a value (e.g. enUS)\n");
                return 1;
            }
        } else if (strcmp(argv[i], "--generate") == 0) {
            if (i + 1 < argc) {
                generate_dir = argv[++i];
            } else {
                printf("Error: --generate requires an output directory\n");
                return 1;
            }
        } else if (!data_dir) {
            data_dir = argv[i];
        } else {
            target_dbc = argv[i];
        }
    }

    if (!data_dir) {
        PrintUsage(argv[0]);
        return 1;
    }

    if (!fs::is_directory(data_dir)) {
        printf("Not a directory: %s\n", data_dir);
        return 1;
    }

    printf("Data directory: %s (expansion: %s, locale: %s)\n",
           data_dir, ExpansionName(expansion), locale);

    std::vector<fs::path> mpq_paths = CollectMpqs(data_dir, locale);
    if (mpq_paths.empty()) {
        printf("No MPQ files found.\n");
        return 1;
    }

    printf("Found %zu MPQ files:\n", mpq_paths.size());
    for (const auto& p : mpq_paths) {
        printf("  %s\n", p.filename().string().c_str());
    }
    printf("\n");

    std::map<std::string, std::vector<uint8_t>> dbc_data;

    for (const auto& mpq_path : mpq_paths) {
        MpqArchive mpq;
        if (!mpq.Open(mpq_path.string().c_str())) {
            printf("Failed to open: %s\n", mpq_path.filename().string().c_str());
            continue;
        }

        std::vector<std::string> files = mpq.GetListFile();
        for (const std::string& f : files) {
            if (f.size() <= 4) {
                continue;
            }
            std::string ext = f.substr(f.size() - 4);
            if (ext != ".dbc" && ext != ".DBC") {
                continue;
            }

            std::string name = GetDbcName(f);
            if (target_dbc && name != target_dbc) {
                continue;
            }

            std::vector<uint8_t> raw = mpq.ExtractFile(f.c_str());
            if (!raw.empty()) {
                dbc_data[name] = std::move(raw);
            }
        }

        mpq.Close();
    }

    printf("Resolved %zu unique DBC files.\n\n", dbc_data.size());

    for (const auto& [name, raw] : dbc_data) {
        printf("[%s]\n", name.c_str());

        DbcFile dbc;
        if (!dbc.Load(raw.data(), (uint32_t)raw.size())) {
            printf("  Failed to parse DBC header.\n\n");
            continue;
        }

        const DbcSchema* schema = GetSchema(expansion, name.c_str());

        if (generate_dir) {
            GenerateHeader(dbc, schema, generate_dir);
        } else {
            DumpDbc(dbc, schema);
        }
        printf("\n");
    }

    return 0;
}
