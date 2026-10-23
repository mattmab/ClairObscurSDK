#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace e33_npc_presentation {
// One complete original 14-byte Blueprint body; not a general VM decoder.
inline bool constant_unavailable_body(const uint8_t* bytes,size_t count,uint64_t own_output_field){
    if(!bytes||count!=14||!own_output_field)return false;
    uint64_t referenced=0;std::memcpy(&referenced,bytes+2,8);
    return bytes[0]==0x14&&bytes[1]==0x48&&referenced==own_output_field&&
        bytes[10]==0x28&&bytes[11]==0x04&&bytes[12]==0x0b&&bytes[13]==0x53;
}
}
