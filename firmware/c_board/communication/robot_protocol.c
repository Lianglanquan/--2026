#include "robot_protocol.h"

#include <string.h>

#define HEADER_SIZE 8U
#define CRC_SIZE 2U
#define COMMAND_PAYLOAD_SIZE WHEELBOT_COMMAND_PAYLOAD_SIZE
#define STATE_PAYLOAD_SIZE 132U

static void put_u16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static uint16_t get_u16(const uint8_t *p) { return (uint16_t)p[0] | ((uint16_t)p[1] << 8); }
static void put_u32(uint8_t *p, uint32_t v) { for (unsigned i=0; i<4; ++i) p[i]=(uint8_t)(v>>(8U*i)); }
static uint32_t get_u32(const uint8_t *p) { uint32_t v=0; for (unsigned i=0; i<4; ++i) v|=((uint32_t)p[i])<<(8U*i); return v; }
static void put_f32(uint8_t *p, float v) { memcpy(p, &v, sizeof(v)); }
static float get_f32(const uint8_t *p) { float v; memcpy(&v, p, sizeof(v)); return v; }

uint16_t wheelbot_crc16(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xffffU;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (unsigned bit = 0; bit < 8U; ++bit) crc = (crc & 0x8000U) ? (uint16_t)((crc << 1) ^ 0x1021U) : (uint16_t)(crc << 1);
    }
    return crc;
}

static int begin_frame(uint8_t type, uint16_t sequence, uint16_t payload_size,
                       uint8_t *frame, size_t capacity, size_t *total)
{
    if (frame == NULL || total == NULL || capacity < HEADER_SIZE + payload_size + CRC_SIZE) return -1;
    frame[0] = WHEELBOT_PROTOCOL_MAGIC0; frame[1] = WHEELBOT_PROTOCOL_MAGIC1;
    frame[2] = WHEELBOT_PROTOCOL_VERSION; frame[3] = type;
    put_u16(&frame[4], payload_size); put_u16(&frame[6], sequence);
    *total = HEADER_SIZE + payload_size + CRC_SIZE; return 0;
}

static int valid_frame(const uint8_t *frame, size_t length, uint8_t type, uint16_t payload_size)
{
    return frame != NULL && length == HEADER_SIZE + payload_size + CRC_SIZE &&
           frame[0] == WHEELBOT_PROTOCOL_MAGIC0 && frame[1] == WHEELBOT_PROTOCOL_MAGIC1 &&
           frame[2] == WHEELBOT_PROTOCOL_VERSION && frame[3] == type &&
           get_u16(&frame[4]) == payload_size &&
           wheelbot_crc16(frame, HEADER_SIZE + payload_size) == get_u16(&frame[HEADER_SIZE + payload_size]);
}

int wheelbot_encode_command(uint16_t sequence, const wheelbot_command_t *c, uint8_t *f, size_t cap, size_t *len)
{
    if (c == NULL || begin_frame(WHEELBOT_MSG_COMMAND, sequence, COMMAND_PAYLOAD_SIZE, f, cap, len) != 0) return -1;
    f[8] = c->enable; f[9] = c->mode; size_t o = 10U;
    for (unsigned i=0; i<4U; ++i, o+=4U) put_f32(&f[o], c->joint_target[i]);
    for (unsigned i=0; i<2U; ++i, o+=4U) put_f32(&f[o], c->wheel_command[i]);
    put_u16(&f[34], wheelbot_crc16(f, 34U)); return 0;
}

int wheelbot_decode_command(const uint8_t *f, size_t n, uint16_t *seq, wheelbot_command_t *c)
{
    if (c == NULL || !valid_frame(f, n, WHEELBOT_MSG_COMMAND, COMMAND_PAYLOAD_SIZE)) return -1;
    if (seq != NULL) *seq = get_u16(&f[6]);
    c->enable = f[8]; c->mode = f[9]; size_t o = 10U;
    for (unsigned i=0; i<4U; ++i, o+=4U) c->joint_target[i]=get_f32(&f[o]);
    for (unsigned i=0; i<2U; ++i, o+=4U) c->wheel_command[i]=get_f32(&f[o]);
    return 0;
}

int wheelbot_encode_state(uint16_t sequence, const wheelbot_state_t *s, uint8_t *f, size_t cap, size_t *len)
{
    if (s == NULL || begin_frame(WHEELBOT_MSG_STATE, sequence, STATE_PAYLOAD_SIZE, f, cap, len) != 0) return -1;
    size_t o=8U; put_u32(&f[o], s->timestamp_ms); o+=4U;
    for (unsigned i=0;i<3U;++i,o+=4U) put_f32(&f[o],s->gyro[i]);
    for (unsigned i=0;i<3U;++i,o+=4U) put_f32(&f[o],s->accel[i]);
    for (unsigned i=0;i<4U;++i,o+=4U) put_f32(&f[o],s->quaternion[i]);
    for (unsigned i=0;i<3U;++i,o+=4U) put_f32(&f[o],s->rpy[i]);
    for (unsigned i=0;i<4U;++i,o+=4U) put_f32(&f[o],s->joint_position[i]);
    for (unsigned i=0;i<4U;++i,o+=4U) put_f32(&f[o],s->joint_velocity[i]);
    for (unsigned i=0;i<4U;++i) f[o++]=s->joint_status[i];
    for (unsigned i=0;i<2U;++i,o+=4U) put_f32(&f[o],s->wheel_position[i]);
    for (unsigned i=0;i<2U;++i,o+=4U) put_f32(&f[o],s->wheel_velocity[i]);
    for (unsigned i=0;i<2U;++i,o+=4U) put_f32(&f[o],s->wheel_current[i]);
    for (unsigned i=0;i<2U;++i,o+=4U) put_u32(&f[o],s->wheel_fault[i]);
    put_f32(&f[o],s->battery_voltage); o+=4U; put_u32(&f[o],s->faults);
    put_u16(&f[140], wheelbot_crc16(f, 140U)); return 0;
}

int wheelbot_decode_state(const uint8_t *f, size_t n, uint16_t *seq, wheelbot_state_t *s)
{
    if (s == NULL || !valid_frame(f,n,WHEELBOT_MSG_STATE,STATE_PAYLOAD_SIZE)) return -1;
    if (seq != NULL) *seq=get_u16(&f[6]);
    size_t o=8U; s->timestamp_ms=get_u32(&f[o]); o+=4U;
    for(unsigned i=0;i<3U;++i,o+=4U)s->gyro[i]=get_f32(&f[o]);
    for(unsigned i=0;i<3U;++i,o+=4U)s->accel[i]=get_f32(&f[o]);
    for(unsigned i=0;i<4U;++i,o+=4U)s->quaternion[i]=get_f32(&f[o]);
    for(unsigned i=0;i<3U;++i,o+=4U)s->rpy[i]=get_f32(&f[o]);
    for(unsigned i=0;i<4U;++i,o+=4U)s->joint_position[i]=get_f32(&f[o]);
    for(unsigned i=0;i<4U;++i,o+=4U)s->joint_velocity[i]=get_f32(&f[o]);
    for(unsigned i=0;i<4U;++i)s->joint_status[i]=f[o++];
    for(unsigned i=0;i<2U;++i,o+=4U)s->wheel_position[i]=get_f32(&f[o]);
    for(unsigned i=0;i<2U;++i,o+=4U)s->wheel_velocity[i]=get_f32(&f[o]);
    for(unsigned i=0;i<2U;++i,o+=4U)s->wheel_current[i]=get_f32(&f[o]);
    for(unsigned i=0;i<2U;++i,o+=4U)s->wheel_fault[i]=get_u32(&f[o]);
    s->battery_voltage=get_f32(&f[o]); o+=4U; s->faults=get_u32(&f[o]);
    return 0;
}
