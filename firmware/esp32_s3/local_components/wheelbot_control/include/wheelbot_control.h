#ifndef WHEELBOT_CONTROL_H
#define WHEELBOT_CONTROL_H

#include "esp_err.h"
#include "wheelbot_esp32_core.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t wheelbot_control_start(void);
wheelbot_input_router_t *wheelbot_control_router(void);

#ifdef __cplusplus
}
#endif

#endif
