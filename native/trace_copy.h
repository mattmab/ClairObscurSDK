#pragma once
#include <cstdint>
#include <cstring>

// Pure bounded copying, not an engine-memory reader. The game-thread collector
// must first validate reflected types, acquire readable views, and resolve out
// records/return storage. No view or pointer is retained in the copied event.
namespace e33_trace {
constexpr uint32_t max_bytes = 4096, max_fields = 128, max_sources = 130;
struct View { const uint8_t* data; uint32_t size; };
// Convention: source 0 = locals, 1 = separate result, 2+ = resolved out storage.
struct Field { uint32_t source, source_offset, destination_offset, size; };
struct Copy { uint32_t size; uint8_t bytes[max_bytes]; };
enum class CopyError { none, limits, source, range, overlap };

inline CopyError copy_fields(const View* sources, uint32_t source_count,
                             const Field* fields, uint32_t field_count,
                             uint32_t extent, Copy& output) {
    // Failure never publishes a prefix of an observation or stale prior bytes.
    output = {};
    if (extent > max_bytes || field_count > max_fields || source_count > max_sources ||
        (source_count && !sources) || (field_count && !fields)) return CopyError::limits;
    uint8_t used[max_bytes]{};
    for (uint32_t i = 0; i < field_count; ++i) {
        const auto& f = fields[i];
        if (f.source >= source_count || !sources[f.source].data) return CopyError::source;
        if (!f.size || uint64_t(f.source_offset) + f.size > sources[f.source].size ||
            uint64_t(f.destination_offset) + f.size > extent) return CopyError::range;
        for (uint32_t j = 0; j < f.size; ++j) {
            if (used[f.destination_offset + j]) return CopyError::overlap;
            used[f.destination_offset + j] = 1;
        }
    }
    // Only validated ranges are touched. Padding is zero, never copied from
    // engine stack storage. Callers must not alias sources with output.
    for (uint32_t i = 0; i < field_count; ++i) {
        const auto& f = fields[i];
        std::memcpy(output.bytes + f.destination_offset,
                    sources[f.source].data + f.source_offset, f.size);
    }
    output.size = extent;
    return CopyError::none;
}
}
