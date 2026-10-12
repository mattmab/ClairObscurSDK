#include "string_call_frame.h"
#include <memory>
#include <iostream>
#include <cstdlib>
static void check(bool b) { if(!b) std::abort(); }
int main() {
 auto p=std::make_unique<TextCallPacket>();
 auto& c=p->retained.call;
 c.version=5; c.parameter_size=c.allocation_extent=16; c.return_offset=65535;
 c.function_flags=0x4020403; c.entry_rva=0x320b2d0;
 c.target={1,2,0x1234}; c.function={3,4,0x5678}; c.field_count=1;
 c.fields[0]={16,0,16,1,0x18000000000280ULL,0,"Path",{-1,0,0}};
 p->count=1; p->texts[0].count=2; p->texts[0].units[0]='x';
 check(validate_string_call(*p)==0);
 auto frame=std::make_unique<StringCallFrame>();
 for(int i=0;i<10000;++i) {
  check(frame->prepare(*p)); check(!frame->prepare(*p)); check(frame->begin());
  check(!frame->reset()); check(frame->returned(*p));
  for(auto b:frame->arguments) check(!b);
  check(frame->reset() && frame->available());
 }
 check(frame->prepare(*p) && frame->begin());
 frame->arguments[0]^=1; check(!frame->returned(*p)); check(!frame->reset());
 check(!frame->prepare(*p));
 c.fields[0].flags|=0x100; check(validate_string_call(*p)!=0); c.fields[0].flags&=~0x100ULL;
 p->texts[0].units[0]=0xd800; check(validate_string_call(*p)!=0);
 p->texts[0].units[0]=0; check(validate_string_call(*p)!=0);
 p->texts[0].units[0]='x'; c.fields[0].dimension=2; check(validate_string_call(*p)!=0);
 std::cout << "FString bounded frame: 10000 cycles, rejection, scrub, unknown quarantine PASS\n";
}
