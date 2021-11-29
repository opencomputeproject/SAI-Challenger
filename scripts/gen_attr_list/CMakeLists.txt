cmake_minimum_required(VERSION 3.5)

project(gen_attr_list LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(TARGET attr_list_generator)
set(SAI "/usr/include/sai")

add_executable(${TARGET} generate_attrs.cpp)

target_link_libraries(${TARGET} PUBLIC
    saimetadata)
target_include_directories(${TARGET} PUBLIC
    ${SAI}/inc
    ${SAI}/meta
    ${SAI}/experimental
    json/single_include/nlohmann)

install(TARGETS ${TARGET}
        DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
