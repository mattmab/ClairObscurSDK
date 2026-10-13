#pragma once
// Validate bounded Byte->Double map hash chains before engine removal.
inline bool picto_stat_hash_valid(uint64_t map,uint64_t descriptor) {
 if(local_read<int32_t>(descriptor+0x84)!=16 || local_read<int32_t>(descriptor+0x88)!=20 ||
    local_read<int32_t>(descriptor+0x8c)!=24)return false;
 const auto count=local_read<int32_t>(map+8),free=local_read<int32_t>(map+52),size=local_read<int32_t>(map+72);
 const auto heap=local_read<uint64_t>(map+64),buckets=heap?heap:map+56;
 if(count<0 || count>64 || free<0 || free>count || size<0 || size>128 ||
    (size && (size&(size-1))) || (!heap && size>2))return false;
 if(!size)return count==free;
 const auto data=local_read<uint64_t>(map),bits_heap=local_read<uint64_t>(map+32),bits=bits_heap?bits_heap:map+16;
 uint64_t seen=0;int visited=0;
 for(int bucket=0;bucket<size;++bucket) {
  auto index=local_read<int32_t>(buckets+uint64_t(bucket)*4);
  for(int links=0;index!=-1;++links) {
   if(index<0 || index>=count || links>=count || (seen&(uint64_t(1)<<index)) ||
      !(local_read<uint32_t>(bits+uint64_t(index/32)*4)&(uint32_t(1)<<(index%32))))return false;
   const auto at=data+uint64_t(index)*24;
   if((local_read<uint32_t>(at+20)&uint32_t(size-1))!=uint32_t(bucket))return false;
   seen|=uint64_t(1)<<index;++visited;index=local_read<int32_t>(at+16);
  }
 }
 return visited==count-free;
}
