#pragma once
#include "invocation_protocol.h"
#include "trace_capture.h"
#include "blueprint_trace_profile.h"

namespace e33_trace {
struct CapturePlan {
    uint32_t count{}, extent{};
    CaptureField fields[max_fields]{};
    bool blueprint{};
    CallIdentity constraints[max_fields]{};
};

// Pure normalization, not engine validation. Properties must be provided by the
// target after checking the live linked list against the full reflected schema.
inline bool make_capture_plan(const CallPacket& schema, const uint64_t* properties,
                              uint32_t property_count, CapturePlan& output) {
    output = {};
    if (validate_call_packet(schema) || schema.object_count ||
        (!(schema.function_flags & 0x400) && !blueprint_damage_schema(schema)) || !schema.entry_rva || schema.entry_rva >= 166776832 ||
        property_count != schema.field_count || (property_count && !properties)) return false;
    for (auto byte : schema.data) if (byte) return false;
    CapturePlan candidate{};
    candidate.blueprint = blueprint_damage_schema(schema);
    for (uint32_t i = 0; i < property_count; ++i) {
        const auto& field = schema.fields[i];
        if ((field.kind > CallDouble && !candidate.blueprint) || !properties[i]) return false;
        for (uint32_t j = 0; j < i; ++j) if (properties[i] == properties[j]) return false;
        const auto source = field.flags & 0x400 ? StorageKind::result :
                            field.flags & 0x100 ? StorageKind::out : StorageKind::locals;
        const auto source_extent = source == StorageKind::locals ? schema.parameter_size :
                                   field.width * field.dimension;
        for (uint32_t element = 0; element < field.dimension; ++element) {
            if (candidate.count == max_fields) return false;
            auto offset = (source == StorageKind::locals ? field.offset : 0) + element * field.width;
            auto size = field.width;
            if (field.kind == CallBool) {
                offset += (field.bool_encoding >> 8) & 255;
                size = 1;
            }
            const auto copied_size = field.kind == CallObject ? uint32_t(sizeof(CallIdentity)) : size;
            if (uint64_t(candidate.extent) + copied_size > max_bytes) return false;
            if (field.kind == CallObject) candidate.constraints[candidate.count] = field.constraint;
            candidate.fields[candidate.count++] = {source, properties[i], source_extent,
                                                   offset, candidate.extent, size};
            candidate.extent += copied_size;
        }
    }
    output = candidate;
    return true;
}
}
