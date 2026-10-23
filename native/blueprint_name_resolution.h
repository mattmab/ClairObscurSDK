#pragma once
#include <cstring>
// Read-only target-build FNamePool lookup. Never calls an FName constructor.
// Names are copied from the pool, cached at most 64 entries, and revalidated.
namespace e33_blueprint_names {
struct Cached {uint64_t base=0;uint32_t id=0;char name[96]{};};
inline Cached cache[64]{};
inline unsigned next=0;
inline bool matches(uint64_t base,uint32_t id,const char* name) {
    const auto pool=base+0x92aadc0;
    const auto current=local_read<uint32_t>(pool+8),cursor=local_read<uint32_t>(pool+12);
    const auto block=id>>16,offset=(id&65535)*2;
    if(current>=8192 || block>current || cursor>0x20000)return false;
    const auto limit=block==current?cursor:0x20000u;
    if(offset+2>limit)return false;
    const auto data=local_read<uint64_t>(pool+16+uint64_t(block)*8);
    if(!data)return false;
    const auto header=local_read<uint16_t>(data+offset);
    const auto length=uint32_t(header>>6);
    return !(header&1) && length==std::strlen(name) && offset+2+length<=limit &&
        !std::memcmp(reinterpret_cast<void*>(data+offset+2),name,length);
}
inline bool resolve(uint64_t base,const char* name,uint64_t& value) {
    for(const auto& entry:cache)if(entry.base==base && !std::strcmp(entry.name,name) && matches(base,entry.id,name)) {
        value=entry.id;return true; // unnumbered FName only
    }
    const auto pool=base+0x92aadc0;
    const auto current=local_read<uint32_t>(pool+8),cursor=local_read<uint32_t>(pool+12);
    if(current>=8192 || cursor>0x20000)return false;
    const auto wanted=std::strlen(name);
    uint32_t budget=32*1024*1024;
    for(uint32_t block=0;block<=current;++block) {
        const auto limit=block==current?cursor:0x20000u;
        if(limit>budget)return false;
        budget-=limit;
        const auto data=local_read<uint64_t>(pool+16+uint64_t(block)*8);
        if(!data)return false;
        for(uint32_t offset=0;offset+2<=limit;) {
            const auto header=local_read<uint16_t>(data+offset);
            const auto length=uint32_t(header>>6);
            if(!length)break; // unused tail of a completed pool block
            const auto bytes=length*((header&1)?2u:1u);
            const auto size=(2+bytes+1)&~1u;
            if(offset+size>limit)return false;
            if(!(header&1) && length==wanted && !std::memcmp(reinterpret_cast<void*>(data+offset+2),name,wanted)) {
                const auto id=(block<<16)|(offset/2);
                if(!matches(base,id,name))return false;
                auto& entry=cache[next++%64];entry={};entry.base=base;entry.id=id;
                std::memcpy(entry.name,name,wanted+1);value=id;return true;
            }
            offset+=size;
        }
    }
    return false;
}
}
