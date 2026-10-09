#pragma once
#include "retained_call_protocol.h"
#include "owned_text_value.h"

// Separate candidate envelope. v11 must continue rejecting inner version3.
constexpr uint32_t kTextCallVersion=3, kTextCallKind=13, kTextCallSlots=8;
#pragma pack(push,1)
struct TextCallSlot {
    uint32_t field_index=0, count=0;
    uint16_t units[kOwnedTextUnits]{};
};
struct TextCallPacket {
    RetainedCallPacket retained{};
    uint32_t version=1, count=0;
    TextCallSlot texts[kTextCallSlots]{};
};
#pragma pack(pop)
static_assert(sizeof(TextCallSlot)==8200 && sizeof(TextCallPacket)==91800);

inline uint32_t validate_text_call(const TextCallPacket& packet) {
    if(packet.version!=1 || !packet.count || packet.count>kTextCallSlots ||
       !retained_call_empty(packet.retained)) return 600;
    const auto& call=packet.retained.call;
    if(call.version!=kTextCallVersion || call.field_count>kCallFields) return 601;
    // Validate scalar/object/POD layout with the established pure validator.
    // Text is represented as eight zero uint16s for THIS CHECK ONLY. This copy
    // must never be dispatched; the real backend must check TextProperty itself.
    auto normalized=call;
    normalized.version=kPodCallVersion;
    uint32_t seen=0;
    for(uint32_t f=0;f<call.field_count;++f) {
        const auto& field=call.fields[f];
        if(field.kind!=kTextCallKind) continue;
        if(seen>=packet.count || field.width!=16 || field.dimension!=1 ||
           field.bool_encoding || field.constraint.index!=-1 || field.constraint.serial ||
           field.constraint.address || field.offset>kCallBytes-16) return 602;
        for(uint32_t b=0;b<16;++b) if(call.data[field.offset+b]) return 603;
        const auto& text=packet.texts[seen++];
        if(text.field_index!=f || text.count>kOwnedTextUnits) return 604;
        const bool input=!(field.flags&0x400) && (!(field.flags&0x100) || (field.flags&0x8000000));
        if(input ? !valid_text_units(text.units,text.count) : text.count!=0) return 605;
        for(uint32_t i=text.count;i<kOwnedTextUnits;++i) if(text.units[i]) return 606;
        auto& substitute=normalized.fields[f];
        substitute.kind=CallUInt16; substitute.width=2; substitute.dimension=8;
        // The old validator requires a scalar return dimension. A TextProperty
        // return is one16-byte value; clearing RETURN here preserves OUT zero
        // checks, with return count/offset checked separately below.
        if(substitute.flags&0x400) { substitute.flags=(substitute.flags&~uint64_t(0x400))|0x100; }
    }
    if(seen!=packet.count) return 607;
    unsigned returns=0;
    for(uint32_t f=0;f<call.field_count;++f) if(call.fields[f].flags&0x400) {
        ++returns;
        if(call.fields[f].offset!=call.return_offset || call.fields[f].dimension!=1) return 608;
        if(call.fields[f].kind==kTextCallKind) normalized.return_offset=65535;
    }
    if(returns>1 || ((call.return_offset==65535)!=(returns==0))) return 608;
    for(uint32_t i=packet.count;i<kTextCallSlots;++i) {
        const auto& text=packet.texts[i];
        if(text.field_index || text.count) return 609;
        for(auto unit:text.units) if(unit) return 609;
    }
    return validate_call_packet(normalized,true);
}
