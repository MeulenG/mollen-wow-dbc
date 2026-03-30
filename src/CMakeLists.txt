add_library(mollen-dbc-schemas STATIC
    dbc_file.cpp
    dbc_writer.cpp
    schema_registry.cpp
    dbc_generator.cpp
)

target_include_directories(mollen-dbc-schemas PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/psql
    ${CMAKE_CURRENT_SOURCE_DIR}/schemas
    ${CMAKE_CURRENT_SOURCE_DIR}/schemas/wotlk
)

add_executable(dbc-extract
    main.cpp
)
target_link_libraries(dbc-extract PRIVATE mollen-dbc-schemas mollen-storm-mpq)
target_compile_definitions(dbc-extract PRIVATE MOLLEN_STORM_HAS_MPQ)
