#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionMesh=133;
struct MeshPacket {
    uint32_t version=3,operation=0,error=0,state=0;
    uint64_t owner=0;
    CallIdentity actor{},component{};
    double position[3]{};
    uint32_t step=0,sections=0;
    CallIdentity inputs[16]{}; // pawn, libraries/classes, 12 verified functions
    uint32_t vertex_count=0,index_count=0;
    double vertices[256][8]{}; // position, normal, UV; copied before dispatch
    int32_t indices[768]{};
    CallIdentity material_inputs[9]{}; // parent, reserved, string CDO, four functions, rendering CDO/import
    wchar_t texture_path[512]{};
    uint32_t section_id=0,reserved=0; // op5 only: optional Widget tint gain 1..64; zero keeps default
};
static_assert(sizeof(MeshPacket)==20984,"mesh packet layout");
