#pragma once
#include "invocation_protocol.h"

// Explicit opt-in transport. Ordinary v1/v2 calls retain their Blueprint ban.
constexpr uint32_t kBlueprintCallVersion=8;
constexpr uint32_t kBlueprintThunkRva=0x13937a0;
constexpr uint32_t kBlueprintNameKind=21;
constexpr uint32_t kBlueprintForbiddenFlags=0x400|0x40|0x80|0x100|0x1000|0x2000|
    0x4000|0x8000|0x10000|0x100000|0x200000|0x1000000|0x80000000u;
inline bool blueprint_function_admitted(uint32_t flags,uint32_t entry,const char* name) {
    return !(flags&kBlueprintForbiddenFlags) && entry==kBlueprintThunkRva && name && name[0] &&
        std::strncmp(name,"ExecuteUbergraph",16)!=0;
}
inline uint32_t validate_blueprint_call(const CallPacket& p) {
    if(p.version!=kBlueprintCallVersion || !blueprint_function_admitted(p.function_flags,p.entry_rva,"Function"))return 1470;
    // Only the lifetime-free codecs used by ordinary v2 calls are admitted.
    // Frame-time/Timespan have separate narrow native-only contracts.
    auto normalized=p;normalized.version=kPodCallVersion;
    for(unsigned i=0;i<p.field_count && i<kCallFields;++i) {
        if(p.fields[i].kind==CallQualifiedFrameTime || p.fields[i].kind==CallTimespan)return 1471;
        const auto& f=p.fields[i];
        if(f.kind==kBlueprintNameKind) {
            const auto identifier=static_cast<const char*>(std::memchr(f.name,0,96));
            if(!identifier || identifier==f.name || identifier>=f.name+94 || f.width!=8 || f.dimension!=1 ||
               (f.flags&0x400) || ((f.flags&0x100) && !(f.flags&0x8000000)) || f.bool_encoding || f.constraint.index!=-1 ||
               f.constraint.serial || f.constraint.address || f.offset>kCallBytes-8)return 1473;
            const auto value=identifier+1;
            const auto end=static_cast<const char*>(std::memchr(value,0,size_t(f.name+96-value)));
            if(!end || end==value)return 1473;
            for(auto ch=value;ch<end;++ch)if(!((*ch>='A'&&*ch<='Z')||(*ch>='a'&&*ch<='z')||
                (*ch>='0'&&*ch<='9')||*ch=='_'||*ch=='.'||*ch=='/'||*ch=='-'))return 1473;
            for(auto ch=end+1;ch<f.name+96;++ch)if(*ch)return 1473;
            for(unsigned b=0;b<8;++b)if(p.data[f.offset+b])return 1473;
            normalized.fields[i].kind=CallDouble;
        }
    }
    return validate_call_packet(normalized,true);
}
