cmake_minimum_required(VERSION 3.20)
project(wheelbot_cboard C ASM)

set(VENDOR_DJI "${CMAKE_CURRENT_SOURCE_DIR}/vendor/dji" CACHE PATH "DJI Development-Board-C-Examples checkout")
set(DJI_PROJECT "${VENDOR_DJI}/20.standard_robot" CACHE PATH "DJI standard robot project")

if(NOT EXISTS "${DJI_PROJECT}")
  message(FATAL_ERROR "DJI vendor source missing: ${DJI_PROJECT}. Clone the official repository into firmware/c_board/vendor/dji and record its commit first.")
endif()

message(FATAL_ERROR "Vendor source inventory is required before enabling the target. See docs/architecture/cboard-build-inputs.md.")
