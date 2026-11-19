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
 auto timer=std::make_unique<TextCallPacket>();auto& tc=timer->retained.call;
 tc.version=5;tc.parameter_size=tc.allocation_extent=24;tc.return_offset=65535;
 tc.function_flags=0x4022403;tc.entry_rva=0x3858580;
 tc.target={1,2,0x1234};tc.function={3,4,0x5678};tc.field_count=2;tc.object_count=1;
 tc.fields[0]={CallObject,0,8,1,0x18001000000280ULL,0,"Object",{5,6,0x1000}};
 tc.fields[1]={16,8,16,1,0x18000000000280ULL,0,"FunctionName",{-1,0,0}};
 tc.objects[0]={0,{9,10,0x3000}};
 timer->count=1;timer->texts[0].field_index=1;timer->texts[0].count=2;timer->texts[0].units[0]='x';
 check(validate_string_call(*timer)==0);
 tc.parameter_size=25;tc.allocation_extent=32;tc.return_offset=24;
 tc.function_flags=0x14022403;tc.entry_rva=0x3858fc0;tc.field_count=3;
 tc.fields[2]={CallBool,24,1,1,0x18001040000780ULL,0xff010001U,"ReturnValue",{-1,0,0}};
 check(validate_string_call(*timer)==0);
 tc.fields[2].bool_encoding=1;check(validate_string_call(*timer)!=0);tc.fields[2].bool_encoding=0xff010001U;
 tc.fields[0].offset=8;check(validate_string_call(*timer)!=0);tc.fields[0].offset=0;
 tc.entry_rva++;check(validate_string_call(*timer)!=0);
 auto slot=std::make_unique<TextCallPacket>();auto& sc=slot->retained.call;
 sc.version=5;sc.parameter_size=29;sc.allocation_extent=32;sc.return_offset=28;
 sc.function_flags=0x4022403;sc.entry_rva=0x3740310;sc.target={1,2,0x1234};sc.function={3,4,0x5678};
 sc.field_count=4;sc.object_count=1;
 sc.fields[0]={CallObject,0,8,1,0x18001000000280ULL,0,"SaveGameObject",{5,6,0x1000}};
 sc.fields[1]={16,8,16,1,0x18000000000280ULL,0,"SlotName",{-1,0,0}};
 sc.fields[2]={CallInt32,24,4,1,0x18001040000282ULL,0,"UserIndex",{-1,0,0}};
 sc.fields[3]={CallBool,28,1,1,0x18001040000780ULL,0xff010001U,"ReturnValue",{-1,0,0}};
 sc.objects[0]={0,{9,10,0x3000}};slot->count=1;slot->texts[0].field_index=1;
 slot->texts[0].count=2;slot->texts[0].units[0]='s';check(validate_string_call(*slot)==0);
 sc.data[24]=1;check(validate_string_call(*slot)==0);sc.data[28]=1;check(validate_string_call(*slot)!=0);sc.data[28]=0;
 sc.fields[2].offset=16;check(validate_string_call(*slot)!=0);sc.fields[2].offset=24;
 sc.object_count=0;check(validate_string_call(*slot)!=0);sc.object_count=1;
 sc.fields[0]=sc.fields[1];sc.fields[0].offset=0;sc.fields[1]=sc.fields[2];sc.fields[1].offset=16;
 sc.fields[2]={CallObject,24,8,1,0x18001000000780ULL,0,"ReturnValue",{5,6,0x1000}};sc.fields[3]={};
 sc.objects[0]={};sc.object_count=0;sc.field_count=3;sc.parameter_size=32;sc.return_offset=24;
 sc.entry_rva=0x373c5c0;slot->texts[0].field_index=0;std::memset(sc.data,0,sizeof(sc.data));
 check(validate_string_call(*slot)==0);sc.fields[2].constraint.address=0;check(validate_string_call(*slot)!=0);
 auto path=std::make_unique<TextCallPacket>();auto&pc=path->retained.call;
 pc.version=5;pc.parameter_size=32;pc.allocation_extent=56;pc.return_offset=16;pc.function_flags=474218496U;pc.entry_rva=0x13937a0;
 pc.target={1,2,0x1234};pc.function={3,4,0x5678};pc.field_count=2;
 pc.fields[0]={16,0,16,1,2251799813685908ULL,0,"SaveName",{-1,0,0}};
 pc.fields[1]={16,16,16,1,2251799813687168ULL,0,"ReturnValue",{-1,0,0}};
 path->count=2;path->texts[0].count=2;path->texts[0].units[0]='s';path->texts[1].field_index=1;
 check(validate_string_call(*path)==0);
 struct OutputOps{int frees=0;bool fail=false;bool read(uint64_t at,uint16_t*out,uint32_t n){std::memcpy(out,reinterpret_cast<void*>(at),n*2);return true;}bool release(uint64_t){++frees;return !fail;}};
 uint16_t output[]={'d','i','r','/','s',0};TargetStringValue output_value{reinterpret_cast<uint64_t>(output),6,6};
 for(bool fail:{false,true}){auto owned=std::make_unique<StringCallFrame>();OutputOps ops;ops.fail=fail;
  path->texts[1].count=0;std::memset(path->texts[1].units,0,sizeof(path->texts[1].units));
  check(owned->prepare(*path)&&owned->begin());std::memcpy(owned->arguments+16,&output_value,16);
  check(owned->returned_output(*path,ops)==!fail);check(ops.frees==1);
  if(fail){check(!owned->reset());check(!owned->returned_output(*path,ops));check(ops.frees==1);}
  else {check(path->texts[1].count==6);check(!std::memcmp(path->texts[1].units,output,sizeof(output)));for(auto b:owned->arguments)check(!b);check(owned->reset());}
 }
 path->texts[1].count=0;std::memset(path->texts[1].units,0,sizeof(path->texts[1].units));
 pc.fields[1].flags^=0x400;check(validate_string_call(*path)!=0);pc.fields[1].flags^=0x400;
 pc.allocation_extent=32;check(validate_string_call(*path)!=0);pc.allocation_extent=56;
 pc.fields[0].name[0]='X';check(validate_string_call(*path)!=0);pc.fields[0].name[0]='S';
 std::cout << "FString bounded frame: 10000 cycles, exact timer profiles, rejection, scrub, unknown quarantine PASS\n";
}
