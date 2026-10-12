#pragma once
#include "retained_call_protocol.h"

// Build-audited LoadAsset_Blocking only. No subobject strings, weak pointers,
// caller addresses, class loading, output soft references or arrays.
constexpr uint32_t kAssetCallVersion=6, kAssetCallKind=17;
inline uint32_t validate_asset_call(const RetainedCallPacket& p) {
    const auto& c=p.call;
    const bool class_load=c.entry_rva==0x3860250;
    if(!retained_call_empty(p) || c.version!=6 || c.field_count!=2 || c.object_count ||
       c.parameter_size!=48 || c.allocation_extent!=48 || c.return_offset!=40 ||
       c.function_flags!=67249155 || (c.entry_rva!=0x3860130 && !class_load)) return 1450;
    const auto& a=c.fields[0]; const auto& r=c.fields[1];
    if(a.kind!=17 || a.offset || a.width!=40 || a.dimension!=1 ||
       a.flags!=7881299347898496ULL || a.bool_encoding || std::strcmp(a.name,class_load?"AssetClass":"Asset") ||
       a.constraint.index<0 || !a.constraint.address ||
       r.kind!=(class_load?CallClass:CallObject) || r.offset!=40 || r.width!=8 || r.dimension!=1 ||
       r.flags!=6755468160534400ULL || std::strcmp(r.name,"ReturnValue") ||
       std::memcmp(&a.constraint,&r.constraint,sizeof(CallIdentity))) return 1451;
    for(unsigned i=0;i<40;++i)
        if((i<8 || (i>=12 && i<16) || i>=20) && c.data[i]) return 1452;
    uint32_t package=0,asset=0;
    std::memcpy(&package,c.data+8,4); std::memcpy(&asset,c.data+16,4);
    if(!package || !asset) return 1452;
    auto normalized=c; normalized.version=2;
    normalized.fields[0].kind=CallUInt16;
    normalized.fields[0].width=2; normalized.fields[0].dimension=20;
    return validate_call_packet(normalized,true);
}
