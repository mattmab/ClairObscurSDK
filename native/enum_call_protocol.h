#pragma once
#include "retained_call_protocol.h"

constexpr uint32_t kEnumCallVersion=4, kEnumCallKind=14;
inline uint32_t validate_enum_call(const RetainedCallPacket& packet) {
    if(!retained_call_empty(packet) || packet.call.version!=kEnumCallVersion ||
       packet.call.field_count>kCallFields) return 750;
    // A validation-only normalized copy. Never dispatch this copy: the actual
    // dispatcher must verify EnumProperty, underlying type and UEnum identity.
    auto normalized=packet.call;
    normalized.version=kPodCallVersion;
    unsigned enums=0;
    for(uint32_t i=0;i<normalized.field_count;++i) {
        auto& field=normalized.fields[i];
        if(field.kind!=kEnumCallKind) continue;
        ++enums;
        if(field.width!=1 || field.dimension!=1 || field.bool_encoding ||
           field.constraint.index<0 || field.constraint.serial<0 || !field.constraint.address) return 751;
        field.kind=CallByte;
    }
    return enums ? validate_call_packet(normalized,true) : 752;
}
