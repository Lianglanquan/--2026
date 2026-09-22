cmake_minimum_required(VERSION 3.20)
project(wheelbot_cboard_usb_only C ASM)

set(DJI_PROJECT "${CMAKE_CURRENT_LIST_DIR}/../c_board/vendor/dji/20.standard_robot")
set(DJI_ROOT "${DJI_PROJECT}")

set(HAL_SOURCES
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ex.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ramfunc.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr_ex.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc_ex.c"
)
set(USB_SOURCES
  "${DJI_ROOT}/Src/system_stm32f4xx.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd_ex.c"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_core.c"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_ctlreq.c"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_ioreq.c"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Src/usbd_cdc.c"
  "${DJI_ROOT}/Src/usb_device.c"
  "${DJI_ROOT}/Src/usbd_conf.c"
  "${DJI_ROOT}/Src/usbd_desc.c"
  "${DJI_ROOT}/Src/usbd_cdc_if.c")

add_executable(wheelbot_cboard_usb_only
  ${HAL_SOURCES} ${USB_SOURCES}
  "${CMAKE_CURRENT_LIST_DIR}/main.c"
  "${CMAKE_CURRENT_LIST_DIR}/usb_only_it.c"
  "${CMAKE_CURRENT_LIST_DIR}/../c_board/startup_stm32f407ighx.s")

target_compile_definitions(wheelbot_cboard_usb_only PRIVATE USE_HAL_DRIVER STM32F407xx)
target_compile_options(wheelbot_cboard_usb_only PRIVATE
  -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
  -ffunction-sections -fdata-sections -fno-common -Wall -Wextra)
target_include_directories(wheelbot_cboard_usb_only PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}"
  "${DJI_ROOT}/Inc"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Inc"
  "${DJI_ROOT}/Drivers/STM32F4xx_HAL_Driver/Inc/Legacy"
  "${DJI_ROOT}/Drivers/CMSIS/Device/ST/STM32F4xx/Include"
  "${DJI_ROOT}/Drivers/CMSIS/Include"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Inc"
  "${DJI_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc")
target_link_options(wheelbot_cboard_usb_only PRIVATE
  -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
  "-T${CMAKE_CURRENT_LIST_DIR}/../c_board/STM32F407IGHX_FLASH.ld"
  -Wl,--gc-sections,--print-memory-usage -specs=nosys.specs)
set_target_properties(wheelbot_cboard_usb_only PROPERTIES OUTPUT_NAME wheelbot_cboard_usb_only SUFFIX ".elf")
add_custom_command(TARGET wheelbot_cboard_usb_only POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:wheelbot_cboard_usb_only> ${CMAKE_CURRENT_BINARY_DIR}/wheelbot_cboard_usb_only.bin
  COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:wheelbot_cboard_usb_only> ${CMAKE_CURRENT_BINARY_DIR}/wheelbot_cboard_usb_only.hex)
