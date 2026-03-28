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
FetchContent_MakeAvailable(mollen_storm)

add_subdirectory(src)
