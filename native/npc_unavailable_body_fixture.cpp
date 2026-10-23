#include "npc_unavailable_body.h"
#include <cassert>
#include <iostream>
int main(){
    uint8_t code[15]={0x14,0x48};const uint64_t field=0x12345000;std::memcpy(code+2,&field,8);
    code[10]=0x28;code[11]=0x04;code[12]=0x0b;code[13]=0x53;
    assert(e33_npc_presentation::constant_unavailable_body(code,14,field));unsigned checks=1;
    for(size_t n:{0U,13U,15U}){assert(!e33_npc_presentation::constant_unavailable_body(code,n,field));++checks;}
    for(unsigned offset:{0U,1U,10U,11U,12U,13U}){code[offset]^=1;assert(!e33_npc_presentation::constant_unavailable_body(code,14,field));code[offset]^=1;++checks;}
    assert(!e33_npc_presentation::constant_unavailable_body(code,14,field+1));++checks;
    assert(!e33_npc_presentation::constant_unavailable_body(code,14,0));++checks;
    std::cout<<checks<<" complete NPC availability-body checks passed; no engine calls executed\n";
}
