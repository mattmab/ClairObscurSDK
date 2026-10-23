#pragma once
#include <cstdint>
#include <cstring>
namespace e33_enemy_spawn {
inline bool empty_battle_arena_soft_value(const void* soft){
    if(!soft)return false;
    // Supported 40-byte soft reference: first8 bytes are weak/cache state;
    // its value path occupies offsets8..39. The shipping soft-copy routine
    // corroborates this layout. This only recognizes an exact empty path.
    const uint8_t empty_path[32]{};
    return !std::memcmp(static_cast<const uint8_t*>(soft)+8,empty_path,sizeof(empty_path));
}
}
