#pragma once
#include <cstdint>
namespace e33_npc_presentation {
struct DialogueLocalSchema {
    uint64_t table,owner,flags;
    uint32_t number,dimension,width,offset,boolean;
};
inline bool dialogue_local_schema(const DialogueLocalSchema& s,unsigned ordinal,uint64_t base,uint64_t function){
    static constexpr uint32_t numbers[]={0,0,0,0,0,2,3};
    return ordinal<7&&s.table==base+0x6e119b0&&s.owner==(function|1)&&
        s.number==numbers[ordinal]&&s.dimension==1&&s.width==1&&s.offset==ordinal&&
        s.flags==(ordinal?0x8001040000200ULL:0x8001040000380ULL)&&s.boolean==0xff010001;
}
}
