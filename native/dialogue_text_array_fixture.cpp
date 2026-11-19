#include "dialogue_text_packet.h"
#include <memory>
#include "owned_text_fixture_ops.h"
#include <iostream>
#include <stdexcept>
using namespace e33_dialogue_text;
static void check(bool value){if(!value)throw std::runtime_error("Dialogue text ownership check failed");}
int main(){
    const uint16_t a[]={'H','i',0},b[]={'B','y','e',0};Input input[]={{a,3},{b,4}};
    {FakeTextOps ops;Frame f;check(f.prepare(ops,input,2));check(ops.values.size()==2);check(f.array.count==2);
     check(!f.prepare(ops,input,2));check(f.begin(ops));check(!f.cleanup(ops));check(f.returned());
     check(f.cleanup(ops));check(ops.values.empty());check(ops.releases==2);check(f.cleanup(ops));check(ops.releases==2);}
    {FakeTextOps ops;Frame f;check(f.prepare(ops,input,2));check(f.begin(ops));f.array.count=1;
     check(!f.returned());check(f.state==State::Quarantined);check(!f.cleanup(ops));check(ops.releases==0);}
    {FakeTextOps ops;Frame f;check(f.prepare(ops,input,2));check(f.begin(ops));f.elements[0].data=999;
     check(!f.returned());check(!f.cleanup(ops));check(ops.releases==0);}
    {FakeTextOps ops;Frame f;ops.fail_construct_at=2;try{f.prepare(ops,input,2);}catch(const std::runtime_error&){}
     check(f.state==State::Preparing);check(!f.cleanup(ops));check(f.state==State::Quarantined);check(ops.releases==0);}
    {FakeTextOps ops;Frame f;check(f.prepare(ops,input,2));check(f.begin(ops));check(f.returned());ops.context=false;
     check(!f.cleanup(ops));check(ops.releases==0);ops.context=true;check(f.cleanup(ops));check(ops.releases==2);}
    {FakeTextOps ops;Frame f;const uint16_t bad[]={0xd800,0};Input invalid[]={{bad,2}};
     check(!f.prepare(ops,invalid,1));check(!f.prepare(ops,input,17));check(!f.prepare(ops,input,0));check(ops.constructions==0);}
    {auto p=std::make_unique<Packet>();p->owner=7;p->dialogue_lease=9;p->system={1,2,0x10000};p->dialogue={3,4,0x20000};p->function={5,6,0x30000};p->mode=1;p->count=2;p->used_units=7;
     p->starts[1]=3;p->lengths[0]=3;p->lengths[1]=4;std::memcpy(p->units,a,6);std::memcpy(p->units+3,b,8);
     check(valid_packet(*p));p->starts[1]=2;check(!valid_packet(*p));p->starts[1]=3;
     p->speaker={7,8,0x40000};check(!valid_packet(*p));p->mode=0;check(valid_packet(*p));
     p->units[7]=1;check(!valid_packet(*p));p->units[7]=0;p->tail[0]=1;check(!valid_packet(*p));}
    {auto p=std::make_unique<Packet>();p->owner=7;p->dialogue_lease=9;p->system={1,2,0x10000};p->dialogue={3,4,0x20000};p->function={5,6,0x30000};p->mode=2;
     check(valid_packet(*p));p->count=1;check(!valid_packet(*p));p->count=0;p->speaker={1,2,0x40000};check(!valid_packet(*p));}
    std::cout<<"Native dialogue text-array ownership checks passed\n";
}
