#include <cstdint>
#include <cstring>
template<class T> T local_read(uint64_t at){T value;std::memcpy(&value,reinterpret_cast<void*>(at),sizeof(value));return value;}
inline bool target_trace_read(uint64_t at,void* out,uint32_t size){std::memcpy(out,reinterpret_cast<void*>(at),size);return true;}
#include "blueprint_direct_trace.h"
#include <cassert>
int main(){
    auto* memory=static_cast<uint64_t*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));assert(memory);
    const auto base=reinterpret_cast<uint64_t>(memory)-0x9360600;
    memory[0x46]=base+0x13986b0;memory[0x1c]=base+0x1398850;
    uint64_t spawn[4]={0,0,0,101},difficulty[4]={0,0,0,102},trace[4]={0,0,0,103};
    assert(BlueprintDirectTrace::retain_encounter(base,reinterpret_cast<uint64_t>(spawn),reinterpret_cast<uint64_t>(difficulty)));
    assert(BlueprintDirectTrace::matches_name(101)&&BlueprintDirectTrace::matches_name(102)&&!BlueprintDirectTrace::matches_name(103));
    assert(BlueprintDirectTrace::original_direct_or_owned(base,memory[0x46]));
    assert(BlueprintDirectTrace::close()); // unrelated trace maintenance must preserve encounter routes
    assert(BlueprintDirectTrace::matches_name(101)&&memory[0x46]!=base+0x13986b0);
    assert(BlueprintDirectTrace::install(base,reinterpret_cast<uint64_t>(trace)));
    assert(BlueprintDirectTrace::matches_name(103));
    assert(BlueprintDirectTrace::release_encounter()); // a still-active trace keeps its route
    assert(!BlueprintDirectTrace::matches_name(101)&&BlueprintDirectTrace::matches_name(103));
    assert(BlueprintDirectTrace::close());
    assert(memory[0x46]==base+0x13986b0&&memory[0x1c]==base+0x1398850);
    VirtualFree(memory,0,MEM_RELEASE);return 0;
}
