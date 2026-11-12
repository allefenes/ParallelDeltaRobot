cmake_minimum_required(VERSION 3.22)
project(delta_description NONE)

# URDF + CAD mesh'leri. Mesh kaynağı depodaki cad/out/meshes (bağ başına STL, bağın yerel
# çerçevesinde, mm). Derlemede her bağ mesh'i malzeme bölgelerine ayrılır (renk için) ve
# share/delta_description/meshes altına kurulur. Kaynak klasör -DDELTA_CAD_OUT=... ile değişir.

find_package(ament_cmake REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(DELTA_CAD_OUT "${CMAKE_CURRENT_SOURCE_DIR}/../../../cad/out" CACHE PATH
  "CAD çıktı klasörü (meshes/ ve mass_properties.json)")
set(DELTA_ROBOT_YAML "${CMAKE_CURRENT_SOURCE_DIR}/../../../config/robot.yaml" CACHE FILEPATH
  "Robot tanımı (kol açıları ve taban yarıçapı; renk bölgeleri kol çerçevesinde tanımlı)")

if(NOT EXISTS "${DELTA_CAD_OUT}/meshes/base.stl")
  message(FATAL_ERROR "CAD mesh'leri bulunamadı: ${DELTA_CAD_OUT}/meshes")
endif()

file(GLOB DELTA_STL "${DELTA_CAD_OUT}/meshes/*.stl")
set(SPLIT_DIR "${CMAKE_CURRENT_BINARY_DIR}/meshes")
set(SPLIT_STAMP "${SPLIT_DIR}/manifest.yaml")
add_custom_command(
  OUTPUT ${SPLIT_STAMP}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/split_meshes.py
    --meshes ${DELTA_CAD_OUT}/meshes
    --rules ${CMAKE_CURRENT_SOURCE_DIR}/config/visual_materials.yaml
    --robot ${DELTA_ROBOT_YAML}
    --out ${SPLIT_DIR}
  DEPENDS ${DELTA_STL} scripts/split_meshes.py config/visual_materials.yaml ${DELTA_ROBOT_YAML}
  COMMENT "CAD mesh'leri malzeme bölgelerine ayrılıyor")
add_custom_target(split_meshes ALL DEPENDS ${SPLIT_STAMP})

install(DIRECTORY ${SPLIT_DIR}/ DESTINATION share/${PROJECT_NAME}/meshes)
install(FILES ${DELTA_CAD_OUT}/mass_properties.json DESTINATION share/${PROJECT_NAME}/config)
install(DIRECTORY urdf rviz config DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_urdf test/test_urdf.py)
endif()

ament_package()
