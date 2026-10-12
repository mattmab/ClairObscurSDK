#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
namespace e33_cinematic {
// All updates and snapshots run on the verified game thread. These counters
// describe matching only; they neither grant ownership nor alter routing.
struct WidgetDiagnostics {
    uint32_t eligible_game_thread_calls=0,exact_frames=0,root_misses=0,owned_matches=0,failed=0;
};
static_assert(sizeof(WidgetDiagnostics)==20);
inline void widget_count(uint32_t& value) { if(value!=UINT32_MAX) ++value; }
inline bool widget_diagnostics_payload(void* payload,size_t size,const WidgetDiagnostics& value) {
    if(!payload || size<sizeof(value)) return false;
    std::memset(payload,0,size);
    std::memcpy(payload,&value,sizeof(value));
    return true;
}
}
