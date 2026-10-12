#pragma once
#include <cstdint>
#include <cstddef>

namespace e33_cinematic {
// Build 23765773 only. Caller must validate/retain the player and track UObject
// identities and run on the game thread. This helper never invokes the engine.
// Evidence: track-input-impl-decompile, root-instance-accessors,
// player-context-accessor-bytes and root-evaluation-schema.
// Only direct root inputs are supported. Subsequence ownership is not inferred.
struct TrackRootMatch {
    uint64_t linker = 0;
    uint32_t handle = 0xffff;
    uint32_t inputs = 0;
};

template<class Reader>
bool match_root_track(Reader&& read, uint64_t player, uint64_t track,
                      TrackRootMatch& result) {
    result = {};
    auto field = [&](uint64_t base, uint64_t offset, auto& value) {
        return base && base <= UINT64_MAX - offset &&
            base + offset <= UINT64_MAX - sizeof(value) &&
            read(base + offset, &value, sizeof(value));
    };
    uint64_t linker{}, track_linker{}, shared{}, registry{}, inputs{}, slots{}, bitmap{};
    uint32_t handle{};
    int32_t count{}, capacity{}, bits{};
    if (!field(player, 0x2d8, linker) || !linker ||
        !field(track, 0x38, track_linker) || track_linker != linker ||
        !field(player, 0x2e0, shared) || !field(shared, 0x38, handle) ||
        (handle & 0xffff) == 0xffff ||
        !field(track, 0x40, inputs) || !inputs ||
        !field(track, 0x48, count) || !field(track, 0x4c, capacity) ||
        count <= 0 || count > 16 || capacity < count || capacity > 1024 ||
        !field(linker, 0x548, registry) ||
        !field(registry, 8, slots) || !slots ||
        !field(registry, 0x28, bitmap) || !field(registry, 0x30, bits) ||
        bits <= 0 || bits > 65536 || (handle & 0xffff) >= static_cast<uint32_t>(bits)) return false;
    if (!bitmap) {
        if (bits > 128 || registry > UINT64_MAX - 0x18) return false;
        bitmap = registry + 0x18;
    }
    uint32_t word{};
    uint16_t serial{};
    const auto index = handle & 0xffff;
    if (!field(bitmap, uint64_t(index >> 5) * 4, word) || !(word & (1u << (index & 31))) ||
        !field(slots, uint64_t(index) * 0x110 + 0x104, serial) || serial != uint16_t(handle >> 16)) return false;
    for (int32_t i = 0; i < count; ++i) {
        uint64_t section{};
        uint32_t input_handle{};
        if (!field(inputs, uint64_t(i) * 16, section) || !section ||
            !field(inputs, uint64_t(i) * 16 + 8, input_handle) || input_handle != handle) return false;
    }
    result = {linker, handle, static_cast<uint32_t>(count)};
    return true;
}
}
