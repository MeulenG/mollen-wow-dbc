cmake_minimum_required(VERSION 3.16)
project(mollen-wow-dbc LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

FetchContent_Declare(
    mollen_storm
    GIT_REPOSITORY https://github.com/MeulenG/mollen-storm.git
    GIT_TAG        master
)

FetchContent_Declare(
    tomlplusplus
    GIT_REPOSITORY https://github.com/marzer/tomlplusplus.git
    GIT_TAG        v3.4.0
)

FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG        v3.5.2
)

FetchContent_MakeAvailable(mollen_storm tomlplusplus Catch2)

add_subdirectory(src)
add_subdirectory(tests)
