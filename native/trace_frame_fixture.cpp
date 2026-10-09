#include "trace_frame.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
    using namespace e33_trace;
    std::array<uint8_t, 8192> memory{};
    constexpr uint64_t base = 0x1000, frame = base, function = 0xabc;
    auto put = [&](uint64_t offset, uint64_t value) {
        assert(offset + 8 <= memory.size());
        std::memcpy(memory.data() + offset, &value, 8);
    };
    auto reader = [&](uint64_t address, void* output, uint32_t size) {
        if (address < base || address - base > memory.size() ||
            size > memory.size() - (address - base)) return false;
        std::memcpy(output, memory.data() + (address - base), size);
        return true;
    };
    put(0x90, function); put(0x28, 0x5000); put(0x80, base + 0x100);
    put(0x100, 0xaaa); put(0x108, 0x6000); put(0x110, base + 0x120);
    put(0x120, 0xbbb); put(0x128, 0x7000);
    FrameStorage storage{};
    assert(resolve_frame(reader, frame, function, 0x8000, storage) == FrameError::none);
    assert(storage.locals == 0x5000 && storage.result == 0x8000 && storage.count == 2);
    assert(find_out(storage, 0xaaa) == 0x6000 && find_out(storage, 0xbbb) == 0x7000);
    assert(find_out(storage, 0xccc) == 0);
    auto reject = [&](FrameError expected, uint64_t address = 0x1000) {
        assert(resolve_frame(reader, address, function, 0x8000, storage) == expected);
        assert(storage.locals == 0 && storage.result == 0 && storage.count == 0);
        for (const auto& out : storage.out) assert(!out.property && !out.address);
    };
    put(0x130, base + 0x100); reject(FrameError::chain); put(0x130, 0);
    put(0x120, 0xaaa); reject(FrameError::chain); put(0x120, 0xbbb);
    put(0x128, 0); reject(FrameError::chain); put(0x128, 0x7000);
    put(0x90, function + 1); reject(FrameError::function); put(0x90, function);
    put(0x20, 1); reject(FrameError::bytecode); put(0x20, 0);
    reject(FrameError::read, UINT64_MAX - 0x20);
    put(0x130, 0xdeadbeef); reject(FrameError::read); put(0x130, 0);
    put(0x80, 0);
    assert(resolve_frame(reader, frame, function, 0, storage) == FrameError::none);
    assert(storage.result == 0 && storage.count == 0);
    put(0x80, base + 0x100);
    for (uint64_t i = 0; i <= max_out_records; ++i) {
        const auto offset = 0x100 + i * 24;
        put(offset, i + 1); put(offset + 8, 0x6000 + i);
        put(offset + 16, i == max_out_records ? 0 : base + offset + 24);
    }
    reject(FrameError::limit);
    std::puts("Frame resolver: separate sources, identity/code gates, bounded chains and cleared failures passed.");
}
