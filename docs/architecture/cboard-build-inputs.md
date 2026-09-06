# C Board Build Inputs

The official DJI `20.standard_robot` Keil project is the source of truth for compiler defines, include paths, source lists, startup code, linker memory layout, HAL/CMSIS/FreeRTOS versions, clock, interrupt, and DMA configuration.

The repositories are now pinned locally. `20.standard_robot` targets `STM32F407IGHx`, defines `USE_HAL_DRIVER, STM32F407xx, ARM_MATH_CM4, __FPU_USED=1U, __FPU_PRESENT=1U`, and lists the official HAL, CMSIS, FreeRTOS, USB, BSP, application, component, and support sources in `MDK-ARM/standard_robot.uvprojx`. The project has no standalone GNU linker script; the Keil project uses its default memory layout, so a linker script must be explicitly derived and reviewed before enabling GCC linking.
