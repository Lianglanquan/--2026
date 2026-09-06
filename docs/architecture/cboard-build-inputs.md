# C Board Build Inputs

The official DJI `20.standard_robot` Keil project is the source of truth for compiler defines, include paths, source lists, startup code, linker memory layout, HAL/CMSIS/FreeRTOS versions, clock, interrupt, and DMA configuration.

The repository could not be fetched during initial provisioning because the configured proxy at `127.0.0.1:7890` was unavailable. Therefore no guessed source list or linker script is enabled yet. Run the vendor clone step, inspect the `.uvprojx`/`.uvoptx` files, and copy their values into `firmware/c_board/CMakeLists.txt` before attempting a firmware build.
