#include <math.h>

/* The vendor CMSIS archive is ARMCC/Pre-v4 encoded and cannot be linked by GCC.
 * These two CMSIS-compatible entry points cover the functions used by the
 * standard_robot sources; the rest of the application remains vendor code. */
float arm_sin_f32(float value) { return sinf(value); }
float arm_cos_f32(float value) { return cosf(value); }
