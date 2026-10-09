#pragma once
#include <cstdint>
#include <limits>

namespace e33_trace {
// Build-specific candidate layout derived from 141393330 / 141395250.
// Reader must safely copy exactly the requested bytes or return false. This
// resolver never dereferences engine addresses and grants no lifetime authority.
constexpr uint32_t max_out_records = 128;
struct FrameStorage {
    uint64_t locals{}, result{};
    uint32_t count{};
    struct Out { uint64_t property{}, address{}; } out[max_out_records]{};
};
enum class FrameError { none, read, function, bytecode, chain, limit };

template<class Reader>
FrameError resolve_frame(Reader&& reader, uint64_t frame, uint64_t function,
                         uint64_t result, FrameStorage& output) {
    output = {};
    FrameStorage candidate{};
    auto read = [&](uint64_t base, uint64_t offset, void* destination, uint32_t size) {
        if (!base || base > std::numeric_limits<uint64_t>::max() - offset) return false;
        const auto address = base + offset;
        if (address > std::numeric_limits<uint64_t>::max() - (size - 1)) return false;
        return reader(address, destination, size);
    };
    uint64_t current{}, code{}, head{};
    if (!read(frame, 0x90, &current, 8) || !read(frame, 0x20, &code, 8) ||
        !read(frame, 0x28, &candidate.locals, 8) || !read(frame, 0x80, &head, 8))
        return FrameError::read;
    if (!function || current != function) return FrameError::function;
    // Bytecode frames need a separate verified strategy; never guess locals.
    if (code) return FrameError::bytecode;
    candidate.result = result;
    uint64_t visited[max_out_records]{};
    while (head) {
        if (candidate.count == max_out_records) return FrameError::limit;
        for (uint32_t i = 0; i < candidate.count; ++i)
            if (visited[i] == head) return FrameError::chain;
        auto& out = candidate.out[candidate.count];
        uint64_t next{};
        if (!read(head, 0, &out.property, 8) || !read(head, 8, &out.address, 8) ||
            !read(head, 0x10, &next, 8)) return FrameError::read;
        if (!out.property || !out.address) return FrameError::chain;
        for (uint32_t i = 0; i < candidate.count; ++i)
            if (candidate.out[i].property == out.property) return FrameError::chain;
        visited[candidate.count++] = head;
        head = next;
    }
    output = candidate;
    return FrameError::none;
}

// A null return means unavailable storage, never a fallback to locals. The
// collector must validate property identity, offsets, sizes and readability.
inline uint64_t find_out(const FrameStorage& storage, uint64_t property) {
    if (!property || storage.count > max_out_records) return 0;
    for (uint32_t i = 0; i < storage.count; ++i)
        if (storage.out[i].property == property) return storage.out[i].address;
    return 0;
}
}
