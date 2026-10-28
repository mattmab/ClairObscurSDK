#pragma once
#include <cstdint>
#include <cstring>
namespace e33_battle_completion {
struct FrameInput {uint64_t private_name=0;uint8_t result=0;};
// Called only by the shared interpreter's exact POST route, after the original
// returned. A post cursor need not equal script start, but must remain in that
// exact verified function's bytecode. Input fields are copied, never written.
template<class Read> bool copy_post_frame(Read&& read,uint64_t frame,uint64_t function,
    uint64_t object,uint64_t script,uint32_t script_size,bool direct,FrameInput& out){
    out={};if(!frame||frame>UINT64_MAX-0x98||!function||!object||!script||!script_size||
        script_size>1048576||script>UINT64_MAX-script_size)return false;
    uint64_t initial=0,current=0,context=0,code=0,locals=0,chain=0;
    if(!read(frame+0x10,&initial,8)||!read(frame+0x90,&current,8)||!read(frame+0x18,&context,8)||
       !read(frame+0x20,&code,8)||!read(frame+0x28,&locals,8)||!read(frame+0x80,&chain,8)||
       initial!=function||current!=(direct?0:function)||context!=object||chain||!locals||
       locals>UINT64_MAX-8||code<script||code>script+script_size)return false;
    uint8_t bytes[9]{};if(!read(locals,bytes,9))return false;
    std::memcpy(&out.private_name,bytes,8);out.result=bytes[8];return out.private_name!=0;
}
}
