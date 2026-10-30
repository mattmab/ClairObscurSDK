#pragma once
#include "text_call_protocol.h"

// Version 5 uses the copied UTF-16 envelope, never FText construction.
constexpr uint32_t kStringCallVersion=5, kStringCallKind=16;
inline uint32_t validate_string_call(const TextCallPacket& p) {
    const auto& c=p.retained.call;
    const bool texture=c.entry_rva==0x3854c30;
    if(p.version!=1 || p.count!=1 || !retained_call_empty(p.retained) ||
       c.version!=5 || c.field_count!=(texture?3U:1U) || c.object_count!=(texture?1U:0U) ||
       c.parameter_size!=(texture?32U:16U) || c.allocation_extent!=(texture?32U:16U) ||
       c.return_offset!=(texture?24U:65535U) || c.function_flags!=(texture?0x4022403U:0x4020403U) ||
       (!texture&&c.entry_rva!=0x320b2d0)) return 760;
    const unsigned string_index=texture?1:0;
    const auto& f=c.fields[string_index];
    if(f.kind!=16 || f.offset!=(texture?8U:0U) || f.width!=16 || f.dimension!=1 ||
       f.flags!=0x18000000000280ULL || f.bool_encoding || f.constraint.index!=-1 ||
       f.constraint.serial || f.constraint.address || std::strcmp(f.name,texture?"Filename":"Path")) return 761;
    if(texture){
        for(unsigned i=0;i<=2;i+=2){
            const auto& object=c.fields[i];
            if(object.kind!=CallObject||object.offset!=(i?24U:0U)||object.width!=8||object.dimension!=1||
               object.flags!=(i?0x18001000000780ULL:0x18001000000280ULL)||object.bool_encoding||
               object.constraint.index<0||object.constraint.serial<0||!object.constraint.address||
               std::strcmp(object.name,i?"ReturnValue":"WorldContextObject"))return 761;
        }
        if(c.objects[0].offset||c.objects[0].identity.index<0||c.objects[0].identity.serial<0||!c.objects[0].identity.address)return 761;
    }
    if(p.texts[0].field_index!=string_index || !valid_text_units(p.texts[0].units,p.texts[0].count)) return 762;
    for(uint32_t i=p.texts[0].count;i<kOwnedTextUnits;++i) if(p.texts[0].units[i]) return 762;
    for(uint32_t i=1;i<kTextCallSlots;++i) {
        if(p.texts[i].field_index || p.texts[i].count) return 762;
        for(auto u:p.texts[i].units) if(u) return 762;
    }
    for(auto b:c.data) if(b) return 763;
    auto normalized=c; normalized.version=2;
    normalized.fields[string_index].kind=CallUInt16; normalized.fields[string_index].width=2;
    normalized.fields[string_index].dimension=8;
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
        const auto offset=p.retained.call.fields[p.texts[0].field_index].offset;
        // Reflection has already patched validated input object slots. Only
        // the string slot is ours; preserve those inputs and the return slot.
        std::memcpy(arguments+offset,&expected,16); state=StringFrameState::Ready; return true;
    }
    bool begin() {
        if(state!=StringFrameState::Ready) return false;
        state=StringFrameState::DispatchUnknown; return true;
    }
    bool returned(const TextCallPacket& p) {
        const auto offset=p.retained.call.fields[p.texts[0].field_index].offset;
        if(state!=StringFrameState::DispatchUnknown ||
           std::memcmp(arguments+offset,&expected,16) || std::memcmp(units,p.texts[0].units,sizeof(units))) {
            state=StringFrameState::Quarantined; return false;
        }
        // reflected_call captures/retains output objects after this callback.
        // Scrub the borrowed FString pointer now, leaving object slots intact.
        std::memset(arguments+offset,0,16); state=StringFrameState::Returned; return true;
    }
    bool reset() {
        if(state==StringFrameState::DispatchUnknown || state==StringFrameState::Quarantined) return false;
        std::memset(arguments,0,sizeof(arguments)); std::memset(units,0,sizeof(units));
        expected={}; state=StringFrameState::Empty; return true;
    }
};
