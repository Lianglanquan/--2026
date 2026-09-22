#ifndef WHEELBOT_WIFI_H
#define WHEELBOT_WIFI_H

#include "wheelbot_esp32_core.h"

/* Starts a local SoftAP and HTTP control endpoint. */
int wheelbot_wifi_start(wheelbot_input_router_t *router);

#endif
