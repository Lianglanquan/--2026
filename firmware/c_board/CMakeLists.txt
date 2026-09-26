cmake_minimum_required(VERSION 3.20)
project(wheelbot_cboard C ASM)

option(WHEELBOT_QD4310_TEST "Run one-shot low-current QD4310 test" OFF)
option(WHEELBOT_HA8_MOTION_ENABLED "Allow HA8 joint angle commands after mechanical calibration" OFF)
set(WHEELBOT_QD4310_COUNT 1 CACHE STRING "Number of installed QD4310 wheel motors (1 or 2)")
if(NOT WHEELBOT_QD4310_COUNT MATCHES "^[12]$")
  message(FATAL_ERROR "WHEELBOT_QD4310_COUNT must be 1 or 2")
endif()

set(VENDOR_DJI "${CMAKE_CURRENT_SOURCE_DIR}/vendor/dji" CACHE PATH "DJI Development-Board-C-Examples checkout")
set(DJI_PROJECT "${VENDOR_DJI}/20.standard_robot" CACHE PATH "DJI standard robot project")

if(NOT EXISTS "${DJI_PROJECT}/MDK-ARM/standard_robot.uvprojx")
  message(FATAL_ERROR "DJI standard_robot Keil project is missing: ${DJI_PROJECT}/MDK-ARM/standard_robot.uvprojx")
endif()

set(FREERTOS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/vendor/freertos-gcc")
set(FASHIONSTAR_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/vendor/fashionstar/STM32F407/STM32F407_SDK(HAL)")
set(DJI_ROOT "${DJI_PROJECT}")
file(GLOB_RECURSE C_SOURCES CONFIGURE_DEPENDS
  "${DJI_ROOT}/Src/*.c" "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/*.c"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/*.c"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Src/*.c"
  "${DJI_ROOT}/Middlewares/Third_Party/FreeRTOS/Source/*.c"
  "${DJI_ROOT}/Middlewares/Third_Party/FreeRTOS/Source/portable/MemMang/heap_4.c"
  "${DJI_ROOT}/bsp/boards/*.c" "${DJI_ROOT}/application/*.c"
  "${DJI_ROOT}/components/devices/*.c" "${DJI_ROOT}/components/algorithm/*.c"
  "${DJI_ROOT}/components/support/*.c" "${DJI_ROOT}/components/controller/*.c")
list(FILTER C_SOURCES EXCLUDE REGEX ".*/application/referee_usart_task\\.c$")
list(FILTER C_SOURCES EXCLUDE REGEX ".*/portable/RVDS/.*")
list(APPEND C_SOURCES "${FREERTOS_ROOT}/portable/GCC/ARM_CM4F/port.c")

file(GLOB FASHIONSTAR_SOURCES CONFIGURE_DEPENDS
  "${FASHIONSTAR_ROOT}/HARDWARE/ring_buffer/ring_buffer.c"
  "${FASHIONSTAR_ROOT}/HARDWARE/user_uart/user_uart.c"
  "${FASHIONSTAR_ROOT}/HARDWARE/fashion_star_uart_servo/fashion_star_uart_servo.c")

add_executable(wheelbot_cboard ${C_SOURCES} ${FASHIONSTAR_SOURCES}
  "${CMAKE_CURRENT_SOURCE_DIR}/port/cmsis_math_compat.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/drivers/qd4310/qd4310.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/drivers/qd4310/qd4310_protocol.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/port/fashionstar_uart.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/port/fashionstar_task.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/port/wheelbot_usart6_irq.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/port/wheelbot_actuator_diag.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/communication/robot_protocol.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/communication/uart_robot_protocol.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/communication/usb_robot_protocol.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/communication/robot_control.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/startup_stm32f407ighx.s")
target_compile_definitions(wheelbot_cboard PRIVATE USE_HAL_DRIVER STM32F407xx ARM_MATH_CM4 __FPU_USED=1U __FPU_PRESENT=1U ARM_MATH_MATRIX_CHECK ARM_MATH_ROUNDING __TARGET_FPU_VFP WHEELBOT_DISABLE_BUZZER WHEELBOT_CONTROL_BUILD WHEELBOT_QD4310_COUNT=${WHEELBOT_QD4310_COUNT})
if(WHEELBOT_QD4310_TEST)
  target_compile_definitions(wheelbot_cboard PRIVATE WHEELBOT_QD4310_TEST)
endif()
if(WHEELBOT_HA8_MOTION_ENABLED)
  target_compile_definitions(wheelbot_cboard PRIVATE WHEELBOT_HA8_MOTION_ENABLED=1)
endif()
target_compile_options(wheelbot_cboard PRIVATE -include "${CMAKE_CURRENT_SOURCE_DIR}/port/wheelbot_compat.h")
target_compile_options(wheelbot_cboard PRIVATE -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -ffunction-sections -fdata-sections -fno-common -Wall -Wextra)
target_include_directories(wheelbot_cboard PRIVATE
  "${DJI_ROOT}/Inc" "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Inc" "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Inc/Legacy"
  "${DJI_ROOT}/Drivers/CMSIS/Device/ST/STM32F4xx/Include" "${DJI_ROOT}/Drivers/CMSIS/Include"
  "${DJI_ROOT}/Middlewares/Third_Party/FreeRTOS/Source/include" "${DJI_ROOT}/Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS"
  "${FREERTOS_ROOT}/portable/GCC/ARM_CM4F" "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Inc" "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc"
  "${DJI_ROOT}/application" "${DJI_ROOT}/application/protocol" "${DJI_ROOT}/bsp/boards" "${DJI_ROOT}/components/devices" "${DJI_ROOT}/components/algorithm" "${DJI_ROOT}/components/algorithm/Include" "${DJI_ROOT}/components/support" "${DJI_ROOT}/components/controller" "${CMAKE_CURRENT_SOURCE_DIR}/port"
  "${FASHIONSTAR_ROOT}/HARDWARE/ring_buffer" "${FASHIONSTAR_ROOT}/HARDWARE/user_uart"
  "${FASHIONSTAR_ROOT}/HARDWARE/fashion_star_uart_servo" "${FASHIONSTAR_ROOT}/Core/Inc"
  "${CMAKE_CURRENT_SOURCE_DIR}/drivers/qd4310"
  "${CMAKE_CURRENT_SOURCE_DIR}/communication")
target_link_options(wheelbot_cboard PRIVATE -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard "-T${CMAKE_CURRENT_SOURCE_DIR}/STM32F407IGHX_FLASH.ld" -Wl,--gc-sections,--print-memory-usage -specs=nosys.specs)
target_link_libraries(wheelbot_cboard PRIVATE "${DJI_ROOT}/components/algorithm/AHRS.lib" m)
set_target_properties(wheelbot_cboard PROPERTIES OUTPUT_NAME wheelbot_cboard SUFFIX ".elf")
add_custom_command(TARGET wheelbot_cboard POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:wheelbot_cboard> ${CMAKE_CURRENT_BINARY_DIR}/wheelbot_cboard.bin
  COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:wheelbot_cboard> ${CMAKE_CURRENT_BINARY_DIR}/wheelbot_cboard.hex)
