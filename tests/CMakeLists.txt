add_executable(dbc-tests
    main.cpp
    test_db_config.cpp
    test_enum_registry.cpp
    test_psql_connector.cpp
)

target_link_libraries(dbc-tests PRIVATE
    mollen-dbc-schemas
    Catch2::Catch2
)

include(Catch)
catch_discover_tests(dbc-tests
    DL_PATHS $<TARGET_FILE_DIR:dbc-tests>
    DISCOVERY_MODE PRE_TEST
    # Catch2 exits with 4 when a test self-skips (SKIP()); without this
    # ctest counts the psql integration test's skip as a failure.
    PROPERTIES SKIP_RETURN_CODE 4
)
