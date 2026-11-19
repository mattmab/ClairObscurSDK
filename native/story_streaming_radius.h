#pragma once
#include <cstdint>
#include <cstring>
#include <cmath>

namespace e33_story_streaming {
constexpr uint32_t operation=263,rejected=4310,uncertain=4311;
struct Identity {int32_t index,serial;uint64_t address;};
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    Identity actor{},component{};float radius=0;uint8_t tail[20924]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984);
inline bool identity(Identity id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool radius_valid(float radius){return std::isfinite(radius)&&radius>=1000.f&&radius<=50000.f;}
inline bool valid(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!identity(p.actor)||!identity(p.component)||!radius_valid(p.radius))return false;
    for(auto byte:p.tail)if(byte)return false;
    return true;
}
struct Shape {uint8_t bytes[72]{};};
template<class T> T at(const Shape& shape,size_t offset){T value{};std::memcpy(&value,shape.bytes+offset,sizeof(value));return value;}
inline bool original_shape(const Shape& shape){
    if(at<uint8_t>(shape,0)||at<float>(shape,4)!=1.f||at<float>(shape,8)!=50000.f||
       at<uint8_t>(shape,12)||at<float>(shape,16)!=360.f)return false;
    for(size_t offset=24;offset<72;offset+=8)if(at<double>(shape,offset)!=0.)return false;
    return true;
}
struct Journal {bool attempted=false,acknowledged=false;};
template<class Ops> uint32_t configure(Journal& journal,float radius,Ops& ops){
    Shape before{},after{};uint64_t storage=0,fresh=0;
    if(journal.attempted||!radius_valid(radius)||!ops.observe(storage,before)||!original_shape(before))return rejected;
    Shape expected=before;std::memcpy(expected.bytes+8,&radius,4);
    journal.attempted=true; // Persist before the only scalar write; never replay unknown work.
    if(!ops.write(storage,radius)||!ops.observe(fresh,after)||fresh!=storage||
       std::memcmp(after.bytes,expected.bytes,sizeof(after.bytes)))return uncertain;
    journal.acknowledged=true;return 0;
}
}
