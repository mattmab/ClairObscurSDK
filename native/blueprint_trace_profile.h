#pragma once
#include "invocation_protocol.h"

// Observation-only build profile, never permission to invoke a Blueprint.
// 218a2478...: 1413937a0 enters 1413938a0 with the caller's FFrame locals.
inline bool blueprint_damage_schema(const CallPacket& p) {
#ifdef E33_BLUEPRINT_TRACE_SESSION
    if (p.function_flags != 0x0c020000 || p.entry_rva != 0x13937a0 ||
        p.parameter_size != 32 || p.return_offset != 65535 || p.field_count != 4) return false;
    constexpr const char* names[] = {"TargetCharacter", "SourceCharacter", "ReceivedDamages", "BattleDamages"};
    for (unsigned i = 0; i < 4; ++i) {
        const auto& f = p.fields[i];
        if (std::strcmp(f.name, names[i]) || f.kind != (i == 2 ? CallDouble : CallObject) ||
            f.offset != i * 8 || f.width != 8 || f.dimension != 1 || (f.flags & 0x500)) return false;
    }
    return true;
#else
    (void)p; return false;
#endif
}
inline bool blueprint_new_game_schema(const CallPacket& p) {
#if defined(E33_BLUEPRINT_TRACE_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 289
    return p.function_flags==0x0c000000 && p.entry_rva==0x13937a0 &&
        p.parameter_size==0 && p.return_offset==65535 && p.field_count==0;
#else
    (void)p;return false;
#endif
}
inline bool story_direction_schema(const CallPacket& p) {
#if defined(E33_BLUEPRINT_TRACE_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 318
    const auto& field=p.fields[0];
    return p.function_flags==263169U && p.entry_rva==0x5fc16c0 &&
        p.parameter_size==1 && p.return_offset==65535 && p.field_count==1 &&
        !std::strcmp(field.name,"UINavigation") && field.kind==CallByte &&
        !field.offset && field.width==1 && field.dimension==1 && field.flags==6755469234274944ULL;
#else
    (void)p;return false;
#endif
}
inline bool blueprint_observer_schema(const CallPacket& p) {
    return blueprint_damage_schema(p)||blueprint_new_game_schema(p);
}
