# Vendor Sources

This directory is reserved for unmodified upstream sources.

| Source | URL | Status |
|---|---|---|
| DJI RoboMaster C Board examples | https://github.com/RoboMaster/Development-Board-C-Examples | `59d12b1adcd321dbf1f9e9166aef5eb95ab657bf` |
| FashionStar SDK | https://github.com/servodevelop/servo-uart-rs485-sdk | `f72877669af0a4dc3501bb98df291cacc0a8592e` |

Selected DJI project: `20.standard_robot`; comparison projects: `8.USART_receive_and_send`, `13.spi_bmi088`, `14.CAN`, `15.freeRTOS_LED`, `16.imu_temperature_control_task`, `18.ins_task`.

Selected FashionStar project: `STM32F407/STM32F407_SDK(HAL)`.

The build must not substitute locally rewritten HAL, CMSIS, FreeRTOS, BMI088, INS, USB, or actuator drivers for these sources.
