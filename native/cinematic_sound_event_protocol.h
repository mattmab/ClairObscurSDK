#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionCinematicSoundEvent=118;
#pragma pack(push,1)
struct CinematicSoundEventPacket {
    uint32_t version,operation;
    uint64_t owner,reserved;
    uint32_t error,state,observed,failed;
    CallIdentity function,player,sound;
    uint64_t function_token;
    CallPacket play;
};
#pragma pack(pop)
static_assert(sizeof(CinematicSoundEventPacket)==24744);
