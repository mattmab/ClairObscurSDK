#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionMusicAudioOwner=117;
#pragma pack(push,1)
struct MusicAudioOwnerPacket {
    uint32_t version,operation;
    uint64_t owner,reserved;
    uint32_t error,state;
    CallIdentity original,isolated,audio_class;
    uint64_t original_token,isolated_token;
    CallPacket stop,destroy;
};
#pragma pack(pop)
static_assert(sizeof(MusicAudioOwnerPacket)==49392);
