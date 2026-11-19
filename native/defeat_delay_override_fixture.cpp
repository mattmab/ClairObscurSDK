#include "defeat_delay_override.h"
#include <cassert>
#include <iostream>
struct Ops {
    uint32_t value=0x41000000U;bool valid=true;unsigned writes=0;
    bool resolve(const e33_defeat_delay::Packet&,uint64_t& out){out=100;return valid;}
    uint32_t bits(uint64_t){return value;}
    void write(uint64_t,uint32_t next){value=next;++writes;}
};
int main(){
    using namespace e33_defeat_delay;
    Packet p{};p.owner=1;p.token=2;p.function={3,4,0x10000};p.mode=1;
    Ops ops;Frame frame;frame.run(p,ops);assert(!p.error&&p.state==1&&ops.value==0&&frame.protects(2));
    p.state=0;frame.run(p,ops);assert(!p.error&&ops.writes==1); // Duplicate acquire is not a second write.
    p.state=0;p.owner=9;frame.run(p,ops);assert(p.error==conflict&&ops.writes==1);
    assert(!frame.close(ops)&&ops.value==0x41000000U&&!frame.active);
    p={};p.owner=1;p.token=2;p.function={3,4,0x10000};p.mode=1;
    ops.valid=false;frame.run(p,ops);assert(p.error==rejected&&!frame.active&&ops.writes==2);
    ops.valid=true;p.error=0;frame.run(p,ops);assert(frame.active);
    ops.value=0x3f800000U;assert(frame.close(ops)==conflict&&frame.active&&ops.writes==3);
    ops.value=0;assert(!frame.close(ops)&&ops.writes==4);
    p.error=0;p.state=0;p.tail[10]=1;frame.run(p,ops);assert(p.error==rejected&&ops.writes==4);
    std::cout<<"Defeat delay override fixture passed\n";
}
