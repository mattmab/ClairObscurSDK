#pragma once
#include "text_call_protocol.h"

// Version 5 uses the copied UTF-16 envelope, never FText construction.
constexpr uint32_t kStringCallVersion=5, kStringCallKind=16;
// Exact engine save-slot signatures observed in the supported executable.
inline uint32_t validate_save_slot_string(const TextCallPacket& p) {
    const auto& c=p.retained.call;const bool save=c.entry_rva==0x3740310;
    const unsigned slot=save?1U:0U,user=save?2U:1U,result=save?3U:2U;
    if(p.version!=1||p.count!=1||!retained_call_empty(p.retained)||c.version!=5||
       c.function_flags!=0x4022403||c.field_count!=(save?4U:3U)||c.object_count!=(save?1U:0U)||
       c.parameter_size!=(save?29U:32U)||c.allocation_extent!=32||c.return_offset!=(save?28U:24U))return 760;
    const auto& f=c.fields[slot];const auto& u=c.fields[user];const auto& r=c.fields[result];
    if(f.kind!=16||f.offset!=(save?8U:0U)||f.width!=16||f.dimension!=1||
       f.flags!=0x18000000000280ULL||f.bool_encoding||f.constraint.index!=-1||f.constraint.serial||f.constraint.address||std::strcmp(f.name,"SlotName"))return 761;
    if(u.kind!=CallInt32||u.offset!=(save?24U:16U)||u.width!=4||u.dimension!=1||
       u.flags!=0x18001040000282ULL||u.bool_encoding||u.constraint.index!=-1||u.constraint.serial||u.constraint.address||std::strcmp(u.name,"UserIndex"))return 761;
    if(r.kind!=(save?CallBool:CallObject)||r.offset!=(save?28U:24U)||r.width!=(save?1U:8U)||r.dimension!=1||
       r.flags!=(save?0x18001040000780ULL:0x18001000000780ULL)||r.bool_encoding!=(save?0xff010001U:0U)||std::strcmp(r.name,"ReturnValue"))return 761;
    if(save){
        const auto& o=c.fields[0];
        if(o.kind!=CallObject||o.offset||o.width!=8||o.dimension!=1||o.flags!=0x18001000000280ULL||
           o.bool_encoding||o.constraint.index<0||o.constraint.serial<0||!o.constraint.address||std::strcmp(o.name,"SaveGameObject")||
           c.objects[0].offset||c.objects[0].identity.index<0||c.objects[0].identity.serial<0||!c.objects[0].identity.address||
           r.constraint.index!=-1||r.constraint.serial||r.constraint.address)return 761;
    }else if(r.constraint.index<0||r.constraint.serial<0||!r.constraint.address)return 761;
    if(p.texts[0].field_index!=slot||!valid_text_units(p.texts[0].units,p.texts[0].count))return 762;
    for(uint32_t i=p.texts[0].count;i<kOwnedTextUnits;++i)if(p.texts[0].units[i])return 762;
    for(unsigned i=1;i<kTextCallSlots;++i){
        if(p.texts[i].field_index||p.texts[i].count)return 762;
        for(auto unit:p.texts[i].units)if(unit)return 762;
    }
    for(unsigned i=0;i<kCallBytes;++i)if((i<u.offset||i>=u.offset+4)&&c.data[i])return 763;
    auto normalized=c;normalized.version=2;normalized.fields[slot].kind=CallUInt16;
    normalized.fields[slot].width=2;normalized.fields[slot].dimension=8;
    return validate_call_packet(normalized,true);
}
// Exact read-only SaveManager helper: one borrowed input and one owned return.
inline uint32_t validate_save_path_string(const TextCallPacket&p){
 const auto&c=p.retained.call;
 if(p.version!=1||p.count!=2||!retained_call_empty(p.retained)||c.version!=5||c.entry_rva!=0x13937a0||c.function_flags!=474218496U||c.field_count!=2||c.object_count||c.parameter_size!=32||c.allocation_extent!=56||c.return_offset!=16)return 760;
 for(unsigned i=0;i<2;++i){const auto&f=c.fields[i];
  if(f.kind!=16||f.offset!=i*16||f.width!=16||f.dimension!=1||f.flags!=(i?2251799813687168ULL:2251799813685908ULL)||f.bool_encoding||f.constraint.index!=-1||f.constraint.serial||f.constraint.address||std::strcmp(f.name,i?"ReturnValue":"SaveName"))return 761;
 }
 if(p.texts[0].field_index||!valid_text_units(p.texts[0].units,p.texts[0].count)||p.texts[1].field_index!=1||p.texts[1].count)return 762;
 for(unsigned i=0;i<kTextCallSlots;++i){const auto&t=p.texts[i];if(i>=2&&(t.count||t.field_index))return 762;for(unsigned j=i?0:t.count;j<kOwnedTextUnits;++j)if(t.units[j])return 762;}
 for(auto b:c.data)if(b)return 763;
 auto normalized=c;normalized.version=2;for(unsigned i=0;i<2;++i){normalized.fields[i].kind=CallUInt16;normalized.fields[i].width=2;normalized.fields[i].dimension=8;}
 normalized.fields[1].flags=(normalized.fields[1].flags&~uint64_t(0x400))|0x100;normalized.return_offset=65535;
 return validate_call_packet(normalized,true);
}
inline uint32_t validate_string_call(const TextCallPacket& p) {
    if(p.retained.call.entry_rva==0x13937a0)return validate_save_path_string(p);
    if(p.retained.call.entry_rva==0x3740310||p.retained.call.entry_rva==0x373c5c0)return validate_save_slot_string(p);
    const auto& c=p.retained.call;
    const bool texture=c.entry_rva==0x3854c30;
    const bool timer_clear=c.entry_rva==0x3858580;
    const bool timer_active=c.entry_rva==0x3858fc0;
    const bool timer=timer_clear||timer_active;
    const unsigned fields=timer?(timer_active?3U:2U):(texture?3U:1U);
    const unsigned size=timer?(timer_active?25U:24U):(texture?32U:16U);
    const unsigned extent=timer?(timer_active?32U:24U):size;
    if(p.version!=1 || p.count!=1 || !retained_call_empty(p.retained) ||
       c.version!=5 || c.field_count!=fields || c.object_count!=((texture||timer)?1U:0U) ||
       c.parameter_size!=size || c.allocation_extent!=extent ||
       c.return_offset!=((texture||timer_active)?24U:65535U) ||
       c.function_flags!=(timer_active?0x14022403U:((texture||timer_clear)?0x4022403U:0x4020403U)) ||
       (!texture&&!timer&&c.entry_rva!=0x320b2d0)) return 760;
    const unsigned string_index=(texture||timer)?1:0;
    const auto& f=c.fields[string_index];
    if(f.kind!=16 || f.offset!=((texture||timer)?8U:0U) || f.width!=16 || f.dimension!=1 ||
       f.flags!=0x18000000000280ULL || f.bool_encoding || f.constraint.index!=-1 ||
       f.constraint.serial || f.constraint.address || std::strcmp(f.name,timer?"FunctionName":texture?"Filename":"Path")) return 761;
    if(timer){
        const auto& object=c.fields[0];
        if(object.kind!=CallObject||object.offset||object.width!=8||object.dimension!=1||
           object.flags!=0x18001000000280ULL||object.bool_encoding||object.constraint.index<0||
           object.constraint.serial<0||!object.constraint.address||std::strcmp(object.name,"Object")||
           c.objects[0].offset||c.objects[0].identity.index<0||c.objects[0].identity.serial<0||!c.objects[0].identity.address)return 761;
        if(timer_active){
            const auto& result=c.fields[2];
            if(result.kind!=CallBool||result.offset!=24||result.width!=1||result.dimension!=1||
               result.flags!=0x18001040000780ULL||result.bool_encoding!=0xff010001U||
               result.constraint.index!=-1||result.constraint.serial||result.constraint.address||
               std::strcmp(result.name,"ReturnValue"))return 761;
        }
    }
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
    template<class Ops>bool returned_output(TextCallPacket&p,Ops&ops){
        if(!returned(p))return false;
        if(p.retained.call.entry_rva!=0x13937a0)return true;
        // Ownership is transferred by the qualified original FString return.
        // Quarantine before either read or allocator call; failures never retry.
        state=StringFrameState::Quarantined;
        TargetStringValue value{};std::memcpy(&value,arguments+16,16);
        if(value.count<0||value.count>int(kOwnedTextUnits)||value.capacity<value.count||value.capacity>65536||
           (value.count&&!value.data)||value.data==expected.data||(!value.data&&value.capacity))return false;
        uint16_t copied[kOwnedTextUnits]{};uint32_t n=value.count?uint32_t(value.count):1;
        if(value.count&&(!ops.read(value.data,copied,n)||!valid_text_units(copied,n)))return false;
        if(value.data&&!ops.release(value.data))return false;
        std::memset(arguments+16,0,16);std::memcpy(p.texts[1].units,copied,n*2);p.texts[1].count=n;
        state=StringFrameState::Returned;return true;
    }
    bool reset() {
        if(state==StringFrameState::DispatchUnknown || state==StringFrameState::Quarantined) return false;
        std::memset(arguments,0,sizeof(arguments)); std::memset(units,0,sizeof(units));
        expected={}; state=StringFrameState::Empty; return true;
    }
};
