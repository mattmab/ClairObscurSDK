#pragma once
#include "text_call_protocol.h"

// Version 5 uses the copied UTF-16 envelope, never FText construction.
constexpr uint32_t kStringCallVersion=5, kStringCallKind=16;
inline uint32_t validate_string_call(const TextCallPacket& p) {
    const auto& c=p.retained.call;
    if(p.version!=1 || p.count!=1 || !retained_call_empty(p.retained) ||
       c.version!=5 || c.field_count!=1 || c.object_count || c.parameter_size!=16 ||
       c.allocation_extent!=16 || c.return_offset!=65535 || c.function_flags!=0x4020403 ||
       c.entry_rva!=0x320b2d0) return 760;
    const auto& f=c.fields[0];
    if(f.kind!=16 || f.offset || f.width!=16 || f.dimension!=1 ||
       f.flags!=0x18000000000280ULL || f.bool_encoding || f.constraint.index!=-1 ||
       f.constraint.serial || f.constraint.address || std::strcmp(f.name,"Path")) return 761;
    if(p.texts[0].field_index || !valid_text_units(p.texts[0].units,p.texts[0].count)) return 762;
    for(uint32_t i=p.texts[0].count;i<kOwnedTextUnits;++i) if(p.texts[0].units[i]) return 762;
    for(uint32_t i=1;i<kTextCallSlots;++i) {
        if(p.texts[i].field_index || p.texts[i].count) return 762;
        for(auto u:p.texts[i].units) if(u) return 762;
    }
    for(auto b:c.data) if(b) return 763;
    auto normalized=c; normalized.version=2;
    normalized.fields[0].kind=CallUInt16; normalized.fields[0].width=2;
    normalized.fields[0].dimension=8;
    return validate_call_packet(normalized,true);
}

enum class StringFrameState { Empty, Ready, DispatchUnknown, Returned, Quarantined };
struct StringCallFrame {
    alignas(16) uint8_t arguments[kCallBytes]{};
    uint16_t units[kOwnedTextUnits]{};
    TargetStringValue expected{};
    StringFrameState state=StringFrameState::Empty;
    StringCallFrame()=default;
    StringCallFrame(const StringCallFrame&)=delete;
    StringCallFrame& operator=(const StringCallFrame&)=delete;
    bool available() const { return state==StringFrameState::Empty; }
    bool prepare(const TextCallPacket& p) {
        if(!available() || validate_string_call(p)) return false;
        std::memcpy(units,p.texts[0].units,sizeof(units));
        expected={reinterpret_cast<uint64_t>(units),static_cast<int32_t>(p.texts[0].count),
                  static_cast<int32_t>(p.texts[0].count)};
        std::memcpy(arguments,&expected,16); state=StringFrameState::Ready; return true;
    }
    bool begin() {
        if(state!=StringFrameState::Ready) return false;
        state=StringFrameState::DispatchUnknown; return true;
    }
    bool returned(const TextCallPacket& p) {
        if(state!=StringFrameState::DispatchUnknown ||
           std::memcmp(arguments,&expected,16) || std::memcmp(units,p.texts[0].units,sizeof(units))) {
            state=StringFrameState::Quarantined; return false;
        }
        std::memset(arguments,0,sizeof(arguments)); state=StringFrameState::Returned; return true;
    }
    bool reset() {
        if(state==StringFrameState::DispatchUnknown || state==StringFrameState::Quarantined) return false;
        std::memset(arguments,0,sizeof(arguments)); std::memset(units,0,sizeof(units));
        expected={}; state=StringFrameState::Empty; return true;
    }
};
