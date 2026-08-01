set(MOLLEN_DBC_SOURCES
    dbc_file.cpp
    dbc_writer.cpp
    schema_registry.cpp
    dbc_generator.cpp
    dbc_naming.cpp
    enums/enum_registry.cpp
    psql/db_config.cpp
)

if(MOLLEN_DBC_ENABLE_PSQL)
    list(APPEND MOLLEN_DBC_SOURCES
        psql/psql_connector.cpp
        psql/dbc_db_import.cpp
    )
endif()

add_library(mollen-dbc-schemas STATIC ${MOLLEN_DBC_SOURCES})

target_include_directories(mollen-dbc-schemas PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/psql
    ${CMAKE_CURRENT_SOURCE_DIR}/enums
    ${CMAKE_CURRENT_SOURCE_DIR}/schemas
    ${CMAKE_CURRENT_SOURCE_DIR}/schemas/wotlk
)

target_link_libraries(mollen-dbc-schemas PUBLIC tomlplusplus::tomlplusplus)

if(MOLLEN_DBC_ENABLE_PSQL)
    target_link_libraries(mollen-dbc-schemas PUBLIC pqxx)
    target_compile_definitions(mollen-dbc-schemas PUBLIC MOLLEN_DBC_ENABLE_PSQL)
endif()

if(MOLLEN_DBC_BUILD_TOOLS)
    add_executable(dbc-extract
        main.cpp
    )
    target_link_libraries(dbc-extract PRIVATE mollen-dbc-schemas mollen-storm-mpq)
    target_compile_definitions(dbc-extract PRIVATE MOLLEN_STORM_HAS_MPQ)
endif()
