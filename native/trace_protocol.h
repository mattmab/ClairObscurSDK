#pragma once
#include <cstddef>
#include "invocation_protocol.h"

namespace e33_trace {
enum class Operation : uint32_t { start = 1, stop, drain, status, forget };
constexpr uint32_t wire_version = 1, drain_capacity = 8;
#pragma pack(push, 1)
struct WireEvent {
    uint64_t sequence, monotonic_ms;
    uint32_t thread, pid;
    int32_t index, serial;
    uint32_t size;
    uint8_t bytes[kCallBytes];
};
struct Packet {
    uint32_t version, operation;
    uint64_t owner, registration;
    uint32_t duration_ms, limit, filtered, reserved;
    CallIdentity filter;
    CallPacket schema;
    uint32_t error, state, cleanup, count, observed, dropped;
    uint64_t rejected;
    WireEvent events[drain_capacity];
};
#pragma pack(pop)
static_assert(sizeof(WireEvent) == 4132 && sizeof(Packet) == 57792);
static_assert(offsetof(Packet, schema) == 56 && offsetof(Packet, error) == 24704 &&
              offsetof(Packet, events) == 24736);

inline bool wire_zero(const void* memory, size_t size) {
    const auto* bytes = static_cast<const uint8_t*>(memory);
    for (size_t i = 0; i < size; ++i) if (bytes[i]) return false;
    return true;
}
inline bool valid_request(const Packet& p) {
    if (p.version != wire_version || p.operation < 1 || p.operation > 5 || !p.owner ||
        p.filtered > 1 || p.reserved || p.error || p.state || p.cleanup || p.count ||
        p.observed || p.dropped || p.rejected || !wire_zero(p.events, sizeof(p.events))) return false;
    if (p.operation != static_cast<uint32_t>(Operation::start)) {
        return p.registration && !p.duration_ms && !p.limit && !p.filtered &&
            p.filter.index == -1 && !p.filter.serial && !p.filter.address &&
            wire_zero(&p.schema, sizeof(p.schema));
    }
    if (p.registration || !p.duration_ms || p.duration_ms > 300000 || !p.limit || p.limit > 1000 ||
        validate_call_packet(p.schema) || p.schema.object_count ||
        !(p.schema.function_flags & 0x400) || !p.schema.entry_rva || p.schema.entry_rva >= 166776832 ||
        !wire_zero(p.schema.data, sizeof(p.schema.data))) return false;
    if (p.filtered) {
        if (p.filter.index < 0 || p.filter.serial < 0 || p.filter.address < 0x10000 || (p.filter.address & 7)) return false;
    } else if (p.filter.index != -1 || p.filter.serial || p.filter.address) return false;
    for (uint32_t i = 0; i < p.schema.field_count; ++i)
        if (p.schema.fields[i].kind > CallDouble) return false;
    return true;
}
}
