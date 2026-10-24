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
 // Exact texture import profile: object inputs survive string construction,
 // and its output survives until reflected_call can retain and scrub it.
 auto image=std::make_unique<TextCallPacket>();auto& ic=image->retained.call;
 ic.version=5;ic.parameter_size=ic.allocation_extent=32;ic.return_offset=24;
 ic.function_flags=0x4022403;ic.entry_rva=0x3854c30;
 ic.target={1,2,0x1234};ic.function={3,4,0x5678};ic.field_count=3;ic.object_count=1;
 ic.fields[0]={CallObject,0,8,1,0x18001000000280ULL,0,"WorldContextObject",{5,6,0x1000}};
 ic.fields[1]={16,8,16,1,0x18000000000280ULL,0,"Filename",{-1,0,0}};
 ic.fields[2]={CallObject,24,8,1,0x18001000000780ULL,0,"ReturnValue",{7,8,0x2000}};
 ic.objects[0]={0,{9,10,0x3000}};
 image->count=1;image->texts[0].field_index=1;image->texts[0].count=2;image->texts[0].units[0]='x';
 check(validate_string_call(*image)==0);
 auto texture=std::make_unique<StringCallFrame>();
 const uint64_t world=0x12345678000,returned_texture=0x98765432000;
 std::memcpy(texture->arguments,&world,8);
 check(texture->prepare(*image));check(!std::memcmp(texture->arguments,&world,8));check(texture->begin());
 std::memcpy(texture->arguments+24,&returned_texture,8);check(texture->returned(*image));
 check(!std::memcmp(texture->arguments,&world,8));check(!std::memcmp(texture->arguments+24,&returned_texture,8));
 for(unsigned i=8;i<24;++i)check(!texture->arguments[i]);
 check(texture->reset());for(auto b:texture->arguments)check(!b);
 image->texts[0].field_index=0;check(validate_string_call(*image)!=0);image->texts[0].field_index=1;
 ic.objects[0].offset=24;check(validate_string_call(*image)!=0);ic.objects[0].offset=0;
 ic.fields[2].flags^=0x400;check(validate_string_call(*image)!=0);ic.fields[2].flags^=0x400;
 ic.fields[1].offset=0;check(validate_string_call(*image)!=0);ic.fields[1].offset=8;
 ic.entry_rva++;check(validate_string_call(*image)!=0);
 std::cout << "FString bounded frame: 10000 cycles, rejection, scrub, unknown quarantine PASS\n";
}
