#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
namespace e33_cinematic {
// Game-thread-only observations; counters never authorize routing or cleanup.
struct SoundEventDiagnostics {
    uint32_t eligible_game_thread_calls=0,exact_function_frames=0,exact_directors=0;
    uint32_t player_matches=0,selected_dispatches=0,failures=0;
};
static_assert(sizeof(SoundEventDiagnostics)==24);
inline void sound_count(uint32_t& value) { if(value!=UINT32_MAX) ++value; }
inline bool sound_diagnostics_payload(void* payload,size_t size,const SoundEventDiagnostics& value) {
    if(!payload || size<sizeof(value)) return false;
    std::memset(payload,0,size);std::memcpy(payload,&value,sizeof(value));return true;
}
}
