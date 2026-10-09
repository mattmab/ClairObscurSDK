#include "trace_capture.h"
#include "trace_events.h"
#include <array>
#include <cassert>
#include <cstdio>

int main() {
    using namespace e33_trace;
    std::array<uint8_t, 1024> memory{};
    auto put = [&](size_t at, uint64_t value) { std::memcpy(memory.data() + at, &value, 8); };
    auto reader = [&](uint64_t address, void* output, uint32_t size) {
        if (address < 0x1000 || address - 0x1000 > memory.size() ||
            size > memory.size() - (address - 0x1000)) return false;
        std::memcpy(output, memory.data() + (address - 0x1000), size); return true;
    };
    put(0x90, 0xabc); put(0x28, 0x1200); put(0x80, 0x1100);
    put(0x100, 0xdef); put(0x108, 0x1300);
    put(0x200, 11); put(0x300, 22); put(0x310, 33);
    FrameStorage storage{};
    assert(resolve_frame(reader, 0x1000, 0xabc, 0x1310, storage) == FrameError::none);
    CaptureField fields[] = {{StorageKind::locals, 0, 4, 0, 0, 4},
        {StorageKind::out, 0xdef, 4, 0, 4, 4}, {StorageKind::result, 0, 4, 0, 8, 4}};
    Copy copied{};
    assert(capture_fields(reader, storage, fields, 3, 16, copied) == CaptureError::none);
    assert(copied.bytes[0] == 11 && copied.bytes[4] == 22 && copied.bytes[8] == 33);
    for (uint32_t i = 12; i < max_bytes; ++i) assert(!copied.bytes[i]);
    Events<2> events;
    Ticket ticket{1, 2};
    assert(events.open(ticket, 7, 100, 1000, 10));
    assert(events.offer(ticket, 7, 101, {99, 3, 4}, copied));
    memory.fill(0);
    Event event{};
    assert(events.pop(ticket, event));
    assert(event.value.bytes[0] == 11 && event.value.bytes[4] == 22 && event.value.bytes[8] == 33);
    auto reject = [&](CaptureError expected) {
        assert(capture_fields(reader, storage, fields, 3, 16, copied) == expected);
        assert(copied.size == 0);
        for (auto byte : copied.bytes) assert(!byte);
    };
    fields[1].property = 0xeee; reject(CaptureError::storage); fields[1].property = 0xdef;
    storage.result = 0; reject(CaptureError::storage);
    storage.result = UINT64_MAX - 1; reject(CaptureError::storage);
    storage.result = 0xdead; reject(CaptureError::read); storage.result = 0x1310;
    fields[1].destination_offset = 3; reject(CaptureError::layout); fields[1].destination_offset = 4;
    fields[1].source_offset = 1; reject(CaptureError::layout); fields[1].source_offset = 0;
    fields[1].source = static_cast<StorageKind>(99); reject(CaptureError::layout);
    fields[1].source = StorageKind::out;
    int reads = 0;
    auto partial = [&](uint64_t, void* destination, uint32_t size) {
        std::memset(destination, 255, size); return ++reads < 2;
    };
    assert(capture_fields(partial, storage, fields, 3, 16, copied) == CaptureError::read);
    for (auto byte : copied.bytes) assert(!byte);
    assert(copied.size == 0 && reads == 2);
    std::puts("Trace capture: frame-to-owned-event, bounds, no partial publication, and unavailable storage passed.");
}
