cmake_minimum_required(VERSION 3.22)
project(delta_edge VERSION 0.1.0 LANGUAGES CXX)

# Raspberry Pi kenar servisi. edge_core saf mantıktır (ağ yok, saat dışarıdan verilir);
# delta_edge yürütülebilir dosyası ince bir ağ katmanıyla (Beast WebSocket + TLS) onu sarar.

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(DELTA_EDGE_BUILD_TESTS "GoogleTest testlerini derle" ON)
option(DELTA_EDGE_BUILD_APP "delta_edge yürütülebilir dosyasını derle (Boost.Beast + OpenSSL)" ON)
option(DELTA_EDGE_COVERAGE "gcov kapsama bayraklarıyla derle" OFF)
option(DELTA_EDGE_FUZZ "libFuzzer hedefini derle (yalnız clang)" OFF)

set(DELTA_EDGE_WARNINGS -Wall -Wextra -Wpedantic -Werror)

if(DELTA_EDGE_COVERAGE)
  add_compile_options(--coverage -O0 -g)
  add_link_options(--coverage)
endif()

if(DELTA_EDGE_FUZZ)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    message(FATAL_ERROR "DELTA_EDGE_FUZZ=ON clang ister: -DCMAKE_CXX_COMPILER=clang++")
  endif()
  # Tüm kütüphane ASan + UBSan ile ve libFuzzer kapsama izleriyle derlenir.
  add_compile_options(-fsanitize=fuzzer-no-link,address,undefined -fno-sanitize-recover=undefined
                      -g -O1)
  add_link_options(-fsanitize=address,undefined)
endif()

find_package(nlohmann_json 3.10 REQUIRED)
find_package(yaml-cpp REQUIRED)

add_library(edge_core STATIC
  src/config.cpp
  src/protocol.cpp
  src/gate.cpp
  src/player.cpp
  src/watchdog.cpp
  src/state.cpp
  src/mock_driver.cpp
  src/ax12_driver.cpp
  src/edge.cpp
  src/url.cpp)
target_include_directories(edge_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(edge_core PRIVATE nlohmann_json::nlohmann_json yaml-cpp)
target_compile_options(edge_core PRIVATE ${DELTA_EDGE_WARNINGS})

if(DELTA_EDGE_BUILD_APP AND NOT DELTA_EDGE_FUZZ)
  find_package(Boost 1.74 REQUIRED)
  find_package(OpenSSL REQUIRED)
  find_package(Threads REQUIRED)
  add_executable(delta_edge app/main.cpp)
  target_link_libraries(delta_edge PRIVATE edge_core Boost::boost OpenSSL::SSL OpenSSL::Crypto
                                           Threads::Threads)
  target_compile_options(delta_edge PRIVATE ${DELTA_EDGE_WARNINGS})
  target_compile_definitions(delta_edge PRIVATE DELTA_EDGE_VERSION="${PROJECT_VERSION}")
  install(TARGETS delta_edge RUNTIME DESTINATION bin)
endif()

if(DELTA_EDGE_BUILD_TESTS)
  enable_testing()
  find_package(GTest REQUIRED)
  add_executable(edge_core_tests
    tests/test_config.cpp
    tests/test_protocol.cpp
    tests/test_gate.cpp
    tests/test_player.cpp
    tests/test_watchdog.cpp
    tests/test_mock_driver.cpp
    tests/test_edge.cpp
    tests/test_url.cpp
    tests/test_architecture.cpp
    tests/test_fuzz_regressions.cpp)
  target_link_libraries(edge_core_tests PRIVATE edge_core nlohmann_json::nlohmann_json
                                                GTest::gtest_main)
  target_compile_options(edge_core_tests PRIVATE ${DELTA_EDGE_WARNINGS})
  target_compile_definitions(edge_core_tests PRIVATE
    DELTA_ROBOT_YAML="${CMAKE_CURRENT_SOURCE_DIR}/../config/robot.yaml"
    DELTA_EDGE_YAML="${CMAKE_CURRENT_SOURCE_DIR}/config/edge.yaml"
    DELTA_EDGE_SRC="${CMAKE_CURRENT_SOURCE_DIR}")
  include(GoogleTest)
  gtest_discover_tests(edge_core_tests)
endif()

if(DELTA_EDGE_FUZZ)
  add_executable(fuzz_protocol fuzz/fuzz_protocol.cpp)
  target_link_libraries(fuzz_protocol PRIVATE edge_core)
  target_link_options(fuzz_protocol PRIVATE -fsanitize=fuzzer)
  target_compile_options(fuzz_protocol PRIVATE ${DELTA_EDGE_WARNINGS})
endif()
