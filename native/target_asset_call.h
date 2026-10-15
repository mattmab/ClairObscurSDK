#pragma once
#include "asset_call_protocol.h"

// Entry walk and allocator bounds independently verified at 1411a5a70.
// Walk one immutable block to establish an entry boundary, not arbitrary reads.
inline bool asset_name(uint64_t base,uint32_t id,char* out,size_t capacity) {
    const auto pool=base+0x92aadc0;
    const auto current=local_read<uint32_t>(pool+8), cursor=local_read<uint32_t>(pool+12);
    const uint32_t block=id>>16, offset=(id&65535)*2;
    if(current>=8192 || block>current || cursor>0x20000) return false;
    const auto limit=block==current ? cursor : 0x20000U;
    const auto data=local_read<uint64_t>(pool+16+uint64_t(block)*8);
    if(!data || offset+2>limit) return false;
    uint32_t at=0;
    while(at<offset) {
        const auto h=local_read<uint16_t>(data+at);
        const uint32_t length=h>>6;
        if(!length) return false;
        const auto extent=(length*((h&1)+1)+3)&~1U;
        if(at+extent>limit) return false;
        at+=extent;
    }
    if(at!=offset) return false;
    const auto h=local_read<uint16_t>(data+at);
    const uint32_t length=h>>6;
    if((h&1) || !length || length>=capacity || at+2+length>limit) return false;
    for(uint32_t i=0;i<length;++i) {
        const char c=local_read<char>(data+at+2+i);
        if(!((c>='a'&&c<='z') || (c>='A'&&c<='Z') || (c>='0'&&c<='9') || c=='_' || c=='/')) return false;
        out[i]=c;
    }
    out[length]=0; return true;
}
inline bool validate_target_asset(uint64_t base,uint64_t property,const CallIdentity& constraint,const uint8_t* value) {
    const bool class_load=local_read<uint64_t>(property)==base+0x6e12cb8;
    if((local_read<uint64_t>(property)!=base+0x6e128d8 && !class_load) ||
       local_read<uint64_t>(property+(class_load?0x78:0x70))!=constraint.address ||
       call_identity(base,constraint)!=constraint.address || !call_is_class(base,constraint.address) ||
       !exact_name(base,constraint.address+0x18,"Object") ||
       !exact_name(base,local_read<uint64_t>(constraint.address+0x20)+0x18,"/Script/CoreUObject")) return false;
    char package[1024]{},asset[1024]{};
    uint32_t p=0,a=0; std::memcpy(&p,value+8,4); std::memcpy(&a,value+16,4);
    if(!asset_name(base,p,package,sizeof(package)) || !asset_name(base,a,asset,sizeof(asset)) ||
       std::strncmp(package,"/Game/",6) || std::strstr(package,"//") || std::strchr(asset,'/')) return false;
    const auto tail=std::strrchr(package,'/');
    return tail && (class_load ? (std::strlen(asset)==std::strlen(tail+1)+2 && !std::strncmp(tail+1,asset,std::strlen(tail+1)) && !std::strcmp(asset+std::strlen(tail+1),"_C")) : !_stricmp(tail+1,asset));
}
