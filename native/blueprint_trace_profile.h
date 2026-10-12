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
