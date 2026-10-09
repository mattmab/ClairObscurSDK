#pragma once
#include "trace_frame.h"
#include "trace_copy.h"

namespace e33_trace {
enum class StorageKind : uint32_t { locals, result, out };
struct CaptureField {
    StorageKind source;
    uint64_t property;
    uint32_t source_extent, source_offset, destination_offset, size;
};
enum class CaptureError { none, layout, storage, read };

// Fields must come from independently revalidated scalar reflection metadata.
// This function only proves bounds and copies; it cannot establish type safety,
// engine identity, game-thread ownership, or a stable GC/lifetime interval.
template<class Reader>
CaptureError capture_fields(Reader&& reader, const FrameStorage& storage,
                           const CaptureField* fields, uint32_t count,
                           uint32_t extent, Copy& output) {
    output = {};
    if (count > max_fields || extent > max_bytes || (count && !fields))
        return CaptureError::layout;
    uint8_t used[max_bytes]{};
    uint64_t addresses[max_fields]{};
    for (uint32_t i = 0; i < count; ++i) {
        const auto& field = fields[i];
        if (!field.size || field.source_extent > max_bytes ||
            uint64_t(field.source_offset) + field.size > field.source_extent ||
            uint64_t(field.destination_offset) + field.size > extent)
            return CaptureError::layout;
        for (uint32_t j = 0; j < field.size; ++j) {
            if (used[field.destination_offset + j]) return CaptureError::layout;
            used[field.destination_offset + j] = 1;
        }
        uint64_t base{};
        switch (field.source) {
        case StorageKind::locals: base = storage.locals; break;
        case StorageKind::result: base = storage.result; break;
        case StorageKind::out: base = find_out(storage, field.property); break;
        default: return CaptureError::layout;
        }
        if (!base || base > UINT64_MAX - field.source_offset ||
            base + field.source_offset > UINT64_MAX - (field.size - 1))
            return CaptureError::storage;
        addresses[i] = base + field.source_offset;
    }
    // Never publish a partial observation, including if the reader writes a
    // partial field and then reports failure. Scratch bytes remain local.
    Copy candidate{};
    for (uint32_t i = 0; i < count; ++i) {
        const auto& field = fields[i];
        if (!reader(addresses[i], candidate.bytes + field.destination_offset, field.size))
            return CaptureError::read;
    }
    candidate.size = extent;
    output = candidate;
    return CaptureError::none;
}
}
