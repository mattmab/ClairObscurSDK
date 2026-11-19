#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include "encounter_action_profile.h"
template<class T>T local_read(uint64_t a){T out{};std::memcpy(&out,reinterpret_cast<void*>(a),sizeof(out));return out;}
bool call_identity(uint64_t,const CallIdentity&i){return i.address!=0;}
#include "story_trial_data_registry.h"
#define E33_RUNTIME_CINEMATIC_VERSION 318
#include "story_trial_parameter_source.h"
int main(){
 using namespace e33_story_trial_data;
 alignas(8)std::array<uint8_t,344> original{},frame{};
 for(size_t i=0;i<original.size();++i)original[i]=static_cast<uint8_t>(i);frame=original;
 alignas(8)uint8_t party[16]{},music[40]{};std::memset(music,0x55,40);uint64_t role=8;std::memcpy(party,&role,8);
 e33_encounter_action::Profile profile;profile.flags=5;profile.level_offset=-3;profile.party_count=1;
 e33_encounter_action::authored_values(frame.data(),0x2000,0x3000,party,music,profile);
 for(size_t i=0;i<frame.size();++i){const bool changed=i<16||(i>=104&&i<144)||i==97||i==98||i==192||(i>=196&&i<217);
  if(!changed)assert(frame[i]==original[i]);}
 assert(frame[97]==1&&frame[98]==0&&frame[192]==1&&frame[216]==0);
 assert(local_read<int32_t>(reinterpret_cast<uint64_t>(frame.data()+196))==-3);
 assert(local_read<uint64_t>(reinterpret_cast<uint64_t>(frame.data()+200))==reinterpret_cast<uint64_t>(party));
 assert(local_read<int32_t>(reinterpret_cast<uint64_t>(frame.data()+208))==1);
 alignas(8)std::array<uint8_t,392> object{};
 CallIdentity root{1,2,0x1000},source{3,4,reinterpret_cast<uint64_t>(object.data())},type{5,6,0x4000},game{7,8,0x5000};
 std::memcpy(object.data()+16,&root.address,8);std::memcpy(object.data()+32,&game.address,8);std::memcpy(object.data()+48,frame.data(),344);
 Registration r{1,root,source,type,game,frame.data(),true};assert(r.offset(1,root,source,type.address)==48);
 auto other=source;++other.serial;assert(!r.offset(1,root,other,type.address));assert(!r.offset(2,root,source,type.address));assert(!r.offset(1,root,source,0x6000));
 object[8]=0x10;assert(!r.offset(1,root,source,type.address));object[8]=0;
 object[48]^=1;assert(!r.offset(1,root,source,type.address));object[48]^=1;
 registration=r;assert(e33_enemy_spawn::story_trial_parameter_offset(1,root,source,type.address)==48);
 registration.ready=false;assert(!e33_enemy_spawn::story_trial_parameter_offset(1,root,source,type.address));
 r.ready=false;assert(!r.offset(1,root,source,type.address));
}
