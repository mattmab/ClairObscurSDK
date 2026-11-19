#include "dialogue_slot_call.h"
#include <cassert>
#include <cstdio>
int main(){
 CallPacket p{};p.version=12;p.entry_rva=0x33a3bc0;p.function_flags=67240963;
 p.target={1,2,0x1234};p.function={3,4,0x5678};p.parameter_size=p.allocation_extent=48;p.return_offset=40;p.field_count=9;
 const char*names[]={"Asset","SlotNodeName","BlendInTime","BlendOutTime","InPlayRate","LoopCount","BlendOutTriggerTime","InTimeToStartMontageAt","ReturnValue"};
 const uint32_t kinds[]={CallObject,21,CallFloat,CallFloat,CallFloat,CallInt32,CallFloat,CallFloat,CallObject};
 const uint32_t offsets[]={0,8,16,20,24,28,32,36,40};
 for(unsigned i=0;i<9;++i){auto&f=p.fields[i];f.kind=kinds[i];f.offset=offsets[i];f.width=i<2||i==8?8:4;f.dimension=1;f.flags=i==8?0x480:0x80;strcpy_s(f.name,96,names[i]);f.constraint={-1,0,0};}
 p.fields[0].constraint=p.fields[8].constraint={5,6,0x9999};p.object_count=1;p.objects[0]={0,{7,8,0xaaaa}};
 strcpy_s(p.fields[1].name+13,83,"Mouth");float values[]={.35f,.35f,1.f,0.f,-1.f,0.f};std::memcpy(p.data+16,values,24);int loops=10000;std::memcpy(p.data+28,&loops,4);
 assert(validate_dialogue_slot_call(p)==0);
 auto bad=p;bad.entry_rva++;assert(validate_dialogue_slot_call(bad));
 bad=p;strcpy_s(bad.fields[1].name+13,83,"Other");assert(validate_dialogue_slot_call(bad));
 bad=p;std::memset(bad.fields[0].name,'X',96);assert(validate_dialogue_slot_call(bad));
 bad=p;loops=20000;std::memcpy(bad.data+28,&loops,4);assert(validate_dialogue_slot_call(bad));
 bad=p;bad.data[8]=1;assert(validate_dialogue_slot_call(bad));
 std::puts("Qualified mouth/default slot profile, bounds, loop limits and raw-name rejection passed");
}
