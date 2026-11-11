cmake_minimum_required(VERSION 3.22)
project(delta_core VERSION 0.2.0 LANGUAGES CXX)

# ROS'tan bağımsız çekirdek kütüphane: kinematik, Jacobian, limitler. Sunucu, Pi kenarı,
# Python istemcisi ve web ikizi aynı kodu kullanır.

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(DELTA_CORE_BUILD_TESTS "Testleri derle" ON)
option(DELTA_CORE_BUILD_PYTHON "pybind11 Python modülünü derle" ON)
option(DELTA_CORE_COVERAGE "gcov kapsama bayraklarıyla derle" OFF)

if(DELTA_CORE_COVERAGE)
  add_compile_options(--coverage -O0 -g)
  add_link_options(--coverage)
endif()

configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/include/delta_core/version.hpp.in
  ${CMAKE_CURRENT_BINARY_DIR}/include/delta_core/version.hpp
  @ONLY)

find_package(yaml-cpp REQUIRED)

add_library(delta_core STATIC src/kinematics.cpp src/params.cpp)
target_include_directories(delta_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/include>)
target_link_libraries(delta_core PRIVATE yaml-cpp)
target_compile_options(delta_core PRIVATE -Wall -Wextra -Wpedantic -Werror)

if(DELTA_CORE_BUILD_PYTHON)
  find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
  find_package(pybind11 CONFIG REQUIRED)
  pybind11_add_module(delta_core_py python/bindings.cpp)
  target_link_libraries(delta_core_py PRIVATE delta_core)
endif()

if(DELTA_CORE_BUILD_TESTS)
  enable_testing()
  find_package(GTest REQUIRED)
  add_executable(delta_core_tests
    tests/test_version.cpp
    tests/test_kinematics.cpp
    tests/test_params.cpp)
  target_link_libraries(delta_core_tests PRIVATE delta_core GTest::gtest_main)
  target_compile_options(delta_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_definitions(delta_core_tests PRIVATE
    DELTA_ROBOT_YAML="${CMAKE_CURRENT_SOURCE_DIR}/../config/robot.yaml"
    DELTA_TEST_DATA="${CMAKE_CURRENT_SOURCE_DIR}/tests/data")
  include(GoogleTest)
  gtest_discover_tests(delta_core_tests)
endif()
