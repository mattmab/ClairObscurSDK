#include "trace_plan.h"
#include <cassert>
#include "blueprint_trace_frame.h"
#include <cstring>
int main(){
    CallPacket p{};p.version=1;p.target={1,1,0x10000};p.function={2,2,0x20000};
    p.function_flags=0x0c000000;p.entry_rva=0x13937a0;p.return_offset=65535;
    p.parameter_size=0;p.allocation_extent=32;p.field_count=0;
    e33_trace::CapturePlan out{};
    assert(blueprint_new_game_schema(p));assert(e33_trace::make_capture_plan(p,nullptr,0,out));
    assert(out.blueprint&&out.count==0&&out.extent==0);
    p.parameter_size=1;assert(!blueprint_new_game_schema(p));
    assert(!e33_trace::make_capture_plan(p,nullptr,0,out));
    p.parameter_size=0;p.function_flags|=0x400;assert(!blueprint_new_game_schema(p));
    p.function_flags=263169U;p.entry_rva=0x5fc16c0;p.parameter_size=1;p.field_count=1;
    p.fields[0]={CallByte,0,1,1,6755469234274944ULL,0,"UINavigation",{-1,0,0}};
    uint64_t property=0x50000;
    assert(story_direction_schema(p));
    assert(e33_trace::make_capture_plan(p,&property,1,out));
    assert(!out.blueprint&&out.story_direction&&out.count==1&&out.extent==1);
    p.fields[0].width=2;assert(!story_direction_schema(p));
    uint8_t frame[0x98]{};uint64_t function=0x20000,object=0x30000,script=0x40000;
    std::memcpy(frame+0x10,&function,8);std::memcpy(frame+0x90,&function,8);
    std::memcpy(frame+0x18,&object,8);std::memcpy(frame+0x20,&script,8);
    auto read=[](uint64_t at,void* to,uint32_t size){std::memcpy(to,reinterpret_cast<void*>(at),size);return true;};
    e33_trace::FrameStorage storage{};auto address=reinterpret_cast<uint64_t>(frame);
    assert(e33_trace::resolve_blueprint_entry(read,address,function,object,script,storage)==e33_trace::FrameError::chain);
    assert(e33_trace::resolve_blueprint_entry(read,address,function,object,script,storage,false,true)==e33_trace::FrameError::none);
    uint64_t wrong_script=script+1;std::memcpy(frame+0x20,&wrong_script,8);
    assert(e33_trace::resolve_blueprint_entry(read,address,function,object,script,storage,false,true)==e33_trace::FrameError::bytecode);
}
