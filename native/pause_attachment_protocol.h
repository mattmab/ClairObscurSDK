#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionPauseAttachment = 113;
#pragma pack(push,1)
struct PauseAttachmentPacket {
    uint32_t version, operation;
    uint64_t owner, lease;
    uint32_t error, state;
    CallPacket remove;
};
#pragma pack(pop)
static_assert(sizeof(PauseAttachmentPacket)==24680);
