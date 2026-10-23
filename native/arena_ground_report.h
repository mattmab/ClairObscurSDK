#pragma once
#include <cstdint>
#include "arena_approach_policy.h"
namespace e33_enemy_spawn {
struct ArenaGroundReport {
    double before[3]{},destination[3]{},after[3]{},heights[7]{},positions[7][3]{},minimum=0,maximum=0;
    uint32_t candidates=0,samples=0,supported=0,clearance=0,attempted=0,acknowledged=0,engine_accepted=0,readback=0,verified=0;
    uint32_t approach_samples=0; // Zero for legacy arena-only placement.
};
static_assert(sizeof(ArenaGroundReport)==352,"owned arena copied ground report");
// Optional receipt extension. Legacy requests keep their exact352-byte reply.
struct ArenaCandidateDiagnostic {
    uint32_t stage=0,samples=0,approach_samples=0,last_surface=0;
    double distance=0,minimum=0,maximum=0;
    e33_arena_approach::Diagnostic approach{};
};
struct ArenaGroundDiagnostics {
    uint32_t version=1,count=0;
    ArenaCandidateDiagnostic candidates[3]{};
};
static_assert(sizeof(ArenaCandidateDiagnostic)==96,"candidate copied diagnostic");
static_assert(sizeof(ArenaGroundDiagnostics)==296,"arena diagnostics extension");
}
