cmake_minimum_required(VERSION 3.22)
project(delta_core VERSION 0.1.0 LANGUAGES CXX)

# ROS'tan bağımsız çekirdek kütüphane. Kinematik ve limitler F1'de eklenir.

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(DELTA_CORE_BUILD_TESTS "Testleri derle" ON)

configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/include/delta_core/version.hpp.in
  ${CMAKE_CURRENT_BINARY_DIR}/include/delta_core/version.hpp
  @ONLY)

add_library(delta_core INTERFACE)
target_include_directories(delta_core INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/include>)

if(DELTA_CORE_BUILD_TESTS)
  enable_testing()
  find_package(GTest REQUIRED)
  add_executable(delta_core_tests tests/test_version.cpp)
  target_link_libraries(delta_core_tests PRIVATE delta_core GTest::gtest_main)
  target_compile_options(delta_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  include(GoogleTest)
  gtest_discover_tests(delta_core_tests)
endif()
