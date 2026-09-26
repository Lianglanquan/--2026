#ifndef WHEELBOT_COMPAT_H
#define WHEELBOT_COMPAT_H

#include <stdint.h>
#include <stdbool.h>

/* Keep the vendor struct_typedef.h guard closed after using toolchain types. */
#define STRUCT_TYPEDEF_H
#define AHRS_MIDDLEWARE_H
typedef unsigned char bool_t;
typedef float fp32;
typedef double fp64;
#define __packed __attribute__((packed))
#define traceISR_ENTER() ((void)0)
#define traceISR_EXIT() ((void)0)
#define traceISR_EXIT_TO_SCHEDULER() ((void)0)

extern void AHRS_get_height(fp32 *high);
extern void AHRS_get_latitude(fp32 *latitude);
extern fp32 AHRS_invSqrt(fp32 num);
extern fp32 AHRS_sinf(fp32 angle);

#endif
