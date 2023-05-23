cmake_minimum_required(VERSION 3.5)

project(gen_attr_list LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(TARGET attr_list_generator)
set(SAI "/usr/include/sai")

add_library(objlib OBJECT saimetadatautils.c saimetadata.c saiserialize.c)
include_directories(${SAI})
add_library(saimetadata STATIC $<TARGET_OBJECTS:objlib>)

set_target_properties(saimetadata PROPERTIES LINKER_LANGUAGE CXX)

add_executable(${TARGET} generate_attrs.cpp)

target_link_libraries(${TARGET} PRIVATE saimetadata)
target_include_directories(${TARGET} PUBLIC
    ${SAI}
    json/single_include/nlohmann)

install(TARGETS ${TARGET}
        DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
