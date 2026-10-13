#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include "picto_progression_protocol.h"
template<class T>T local_read(uint64_t at){T value;std::memcpy(&value,reinterpret_cast<void*>(at),sizeof(value));return value;}
#include "picto_stat_hash.h"
template<class T>void put(void* at,T value){std::memcpy(at,&value,sizeof(value));}
int main(){
 alignas(8) uint8_t map[80]{},desc[160]{},data[48]{};
 auto m=reinterpret_cast<uint64_t>(map),d=reinterpret_cast<uint64_t>(desc);
 put(desc+0x84,16);put(desc+0x88,20);put(desc+0x8c,24);
 put(map,reinterpret_cast<uint64_t>(data));put(map+8,2);put(map+16,uint32_t(3));put(map+40,2);put(map+72,1);put(map+56,0);
 put(data+16,1);put(data+40,-1);
 assert(picto_stat_hash_valid(m,d));
 put(data+40,0);assert(!picto_stat_hash_valid(m,d)); // cycle
 put(data+40,-1);put(map+16,uint32_t(1));assert(!picto_stat_hash_valid(m,d)); // dead slot in chain
 put(map+16,uint32_t(3));put(map+56,2);assert(!picto_stat_hash_valid(m,d)); // out of bounds
 put(map+56,0);put(map+72,3);assert(!picto_stat_hash_valid(m,d)); // invalid bucket count
 put(map+72,1);put(desc+0x84,8);assert(!picto_stat_hash_valid(m,d));
 PictoProgressionPacket p{};p.operation=12;p.target=p.function={1,1,16};p.expected=1;p.value=6;
 assert(valid_picto_progression(p));p.expected=2;assert(valid_picto_progression(p));
 p.expected=3;assert(!valid_picto_progression(p));p.expected=1;p.value=7;assert(!valid_picto_progression(p));
 p.value=9;p.source.address=16;assert(!valid_picto_progression(p));
 puts("Picto stat removal guards passed");
}
