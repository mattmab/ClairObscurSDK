#pragma once
#include <cstdint>
#include <cstring>

namespace e33_enemy_spawn {
// Exactly the observed supported-build custom-event stub. This is not a
// general Kismet decoder. Pointer operands must be validated as live metadata.
struct BattleEntryCopyStub {uint64_t destination=0,source=0,graph=0;};
inline bool decode_battle_entry_copy_stub(const void* data,uint32_t size,BattleEntryCopyStub& out){
    out={};
    if(!data||size!=36)return false;
    const auto* code=static_cast<const uint8_t*>(data);
    if(code[0]!=0x64||code[9]!=0x00||code[18]!=0x46||code[27]!=0x1d||
       code[32]!=0x16||code[33]!=0x04||code[34]!=0x0b||code[35]!=0x53)return false;
    int32_t entry=0;std::memcpy(&entry,code+28,4);
    if(entry!=41580)return false;
    BattleEntryCopyStub candidate;
    std::memcpy(&candidate.destination,code+1,8);
    std::memcpy(&candidate.source,code+10,8);
    std::memcpy(&candidate.graph,code+19,8);
    if(candidate.destination<0x10000||candidate.source<0x10000||candidate.graph<0x10000||
       (candidate.destination&7)||(candidate.source&7)||(candidate.graph&7)||
       candidate.destination==candidate.source||candidate.destination==candidate.graph||
       candidate.source==candidate.graph)return false;
    out=candidate;return true;
}
}
