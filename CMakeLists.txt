cmake_minimum_required(VERSION 3.16)
project(mollen-wow-dbc LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Standalone builds get the CLI tool and tests; embedded builds (FetchContent
# from the engine) get just the library by default.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(_mwd_standalone ON)
else()
    set(_mwd_standalone OFF)
endif()

option(MOLLEN_DBC_ENABLE_PSQL "PostgreSQL import support (requires pqxx)" ON)
option(MOLLEN_DBC_BUILD_TOOLS "Build the dbc-extract CLI (requires mollen-storm)" ${_mwd_standalone})
option(MOLLEN_DBC_BUILD_TESTS "Build the Catch2 test suite" ${_mwd_standalone})

include(FetchContent)

# tomlplusplus is always needed: db_config (toml parsing) is part of the core
# library even in psql-less builds.
FetchContent_Declare(
    tomlplusplus
    GIT_REPOSITORY https://github.com/marzer/tomlplusplus.git
    GIT_TAG        v3.4.0
)
FetchContent_MakeAvailable(tomlplusplus)

if(MOLLEN_DBC_BUILD_TOOLS)
    FetchContent_Declare(
        mollen_storm
        GIT_REPOSITORY https://github.com/MeulenG/mollen-storm.git
        GIT_TAG        master
    )
    FetchContent_MakeAvailable(mollen_storm)
endif()

if(MOLLEN_DBC_BUILD_TESTS)
    FetchContent_Declare(
        Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG        v3.5.2
    )
    FetchContent_MakeAvailable(Catch2)

    # Must be enabled at the top level or ctest run from the build root
    # finds no tests (enable_testing() in a subdirectory only registers
    # that subdirectory's own scope).
    include(CTest)
endif()

add_subdirectory(src)

if(MOLLEN_DBC_BUILD_TESTS)
    add_subdirectory(tests)
endif()
