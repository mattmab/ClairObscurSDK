#pragma once
// Admission is published only by the typed selected-save trial-data owner.
namespace e33_story_trial_data {
struct Registration {
 uint64_t base=0;CallIdentity root{},source{},structure{},gi{};const uint8_t* published=nullptr;bool ready=false;
 uint32_t offset(uint64_t b,const CallIdentity&r,const CallIdentity&s,uint64_t type=0)const{
  if(!ready||b!=base||std::memcmp(&r,&root,16)||std::memcmp(&s,&source,16)||(type&&type!=structure.address)||
   !call_identity(b,r)||!call_identity(b,s)||!call_identity(b,structure)||!call_identity(b,gi)||
   local_read<uint64_t>(s.address+16)!=r.address||local_read<uint64_t>(s.address+32)!=gi.address||
   local_read<uint32_t>(s.address+8)&0x40018030U||!published||std::memcmp(reinterpret_cast<void*>(s.address+48),published,344))return 0;
  return 48;
 }
};
inline Registration registration{};
}
