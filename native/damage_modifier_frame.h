#pragma once
#include <cstdint>
#include <cmath>
#include <cstring>

namespace e33_damage_evidence {
template<class Reader>
uint64_t parameter(Reader&& read,uint64_t frame,uint64_t function,uint64_t object,uint64_t script,uint64_t property,bool direct){
    if(!frame||frame>UINT64_MAX-0x98||!function||!object||!script||!property)return 0;
    uint64_t node{},context{},code{},current{},locals{},out{};
    if(!read(frame+0x10,&node,8)||!read(frame+0x18,&context,8)||!read(frame+0x20,&code,8)||
       !read(frame+0x28,&locals,8)||!read(frame+0x80,&out,8)||!read(frame+0x90,&current,8)||
       node!=function||context!=object||code!=script||current!=(direct?0:function))return 0;
    if(out){uint64_t field{},next{},address{};
        if(out>UINT64_MAX-24||!read(out,&field,8)||!read(out+8,&address,8)||!read(out+16,&next,8)||field!=property||next)return 0;
        locals=address;
    }
    return locals&&locals<=UINT64_MAX-40?locals:0;
}
inline bool values(const uint8_t* data,uint8_t& kind,double& value,uint8_t& affects){
    if(!data)return false;
    kind=data[0];std::memcpy(&value,data+8,8);affects=data[16];
    return kind<=16&&affects<=1&&std::isfinite(value);
}
}
