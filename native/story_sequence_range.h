#pragma once
// Selected-save, reversible endpoints for the two inspected reference movies.
namespace e33_story_sequence_range {
constexpr uint32_t operation=252,rejected=4220,uncertain=4221;
#pragma pack(push,1)
struct Packet {uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity scene{},gi{};uint64_t leases[2]{};uint32_t guid[4]{},mode=0,expected=0,replacement=0,readback=0;uint8_t tail[20880]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story sequence range packet");
struct Profile {uint32_t expected,replacement;int32_t lower;const char* name;const char* path;};
constexpr Profile profiles[]={
 {6493600U,7261600U,0,"MCS_TheGommageP2_PreRender","/Game/Cinematics/Lumiere/Act01/TheGommage/MCS_TheGommageP2_PreRender"},
 {5501600U,5885600U,-24000,"MCS_TheEndOfExpedition33","/Game/Cinematics/DarkShores/TheEndOfExpedition33/MCS_TheEndOfExpedition33"}
};
inline int profile_for(uint32_t expected,uint32_t replacement){for(int i=0;i<2;++i)if(profiles[i].expected==expected&&profiles[i].replacement==replacement)return i;return -1;}
enum class SaveContext { Pending,Selected,Changed };
#ifndef E33_STORY_SEQUENCE_RANGE_FIXTURE
inline SaveContext selected_context(uint64_t b,CallIdentity gi,const uint32_t*guid){
 if(!call_identity(b,gi))return SaveContext::Pending;
 const auto manager=zone_ref(b,gi.address,"SaveManager");uint64_t ld=0,bd=0,cd=0;
 const auto loaded=picto_field(b,gi.address,"SaveLoaded","BoolProperty",2680,1,&ld),
  loading=manager?picto_field(b,manager,"LoadIsInProgress","BoolProperty",169,1,&bd):0,
  changing=picto_field(b,gi.address,"IsChangingMap","BoolProperty",464,1,&cd);
 if(!manager||!picto_class(b,manager,"BP_SaveManager_C","/Game/Gameplay/Save/BP_SaveManager")||
    zone_ref(b,manager,"GameInstanceReference")!=gi.address||!loaded||!loading||!changing||
    local_read<uint32_t>(ld+0x70)!=0xff010001U||local_read<uint32_t>(bd+0x70)!=0xff010001U||
    local_read<uint32_t>(cd+0x70)!=0xff010001U)return SaveContext::Pending;
 const auto l=local_read<uint8_t>(loaded),busy=local_read<uint8_t>(loading),travel=local_read<uint8_t>(changing);
 // Native travel may temporarily reset save readiness. It is not evidence
 // that the user selected a different save; retain across this boundary.
 if(l>1||busy>1||travel>1||busy||travel)return SaveContext::Pending;
 if(!l){
  e33_retired_world::Snapshot now{};e33_retired_world::TargetOps proof{b};
  return proof.observe(now)&&exact_name(b,now.world.address+24,"Level_MainMenu")?
   SaveContext::Changed:SaveContext::Pending;
 }
 e33_story_action::Dispatcher proof;proof.base=b;proof.gi=gi;std::memcpy(proof.guid,guid,16);
 if(proof.bound())return SaveContext::Selected;
 // Distinguish an admitted vanilla/different save from a malformed or
 // incomplete map. Only a complete valid snapshot authorizes restoration.
 uint64_t descriptor=0;const auto map=picto_field(b,gi.address,"InteractedDialogues","MapProperty",3400,80,&descriptor);
 std::vector<e33_story_identity::Entry> entries;e33_story_identity::Entry found{};
 if(!map||!descriptor||!e33_story_identity::snapshot(map,descriptor,entries))return SaveContext::Pending;
 const auto n=e33_story_identity::marker(entries,found);
 if(n<0)return SaveContext::Pending;
 return n==1&&!std::memcmp(found.guid,guid,16)?SaveContext::Selected:SaveContext::Changed;
}
#else
SaveContext selected_context(uint64_t,CallIdentity,const uint32_t*);
#endif
inline bool tick_rate(uint64_t b,uint64_t scene,uint64_t cls){
 // Inspect the reflected offset instead of assuming another MovieScene build's
 // layout. Require the exact FrameRate schema and 24000/1 source tick unit.
 uint64_t found=0;
 for(auto f=local_read<uint64_t>(cls+0x50),n=uint64_t(0);f&&++n<256;f=local_read<uint64_t>(f+0x18)){
  if(!exact_name(b,f+0x20,"TickResolution"))continue;
  if(found)return false;found=f;
 }
 if(!found)return false;
 const auto offset=local_read<int32_t>(found+0x44),extent=local_read<int32_t>(cls+0x58);
 if(offset<0x28||offset>0x400||extent<offset+8||extent>0x10000||
    picto_struct_field(b,cls,"TickResolution","StructProperty",offset,8)!=found)return false;
 const auto st=local_read<uint64_t>(found+0x70);
 if(!e33_mesh::named(b,st,"FrameRate","/Script/CoreUObject")||
    !picto_struct_field(b,st,"Numerator","IntProperty",0,4)||!picto_struct_field(b,st,"Denominator","IntProperty",4,4))return false;
 return local_read<int32_t>(scene+offset)==24000&&local_read<int32_t>(scene+offset+4)==1;
}
struct Owner {
 uint64_t base=0,session=0,owner=0;CallIdentity scene{},gi{};uint64_t leases[2]{};uint32_t guid[4]{};uint8_t original[16]{},published[16]{};bool attached=false,unknown=false,restored=false;
 bool protects(uint64_t token)const{return attached&&(token==leases[0]||token==leases[1]);}
 bool current()const{return attached&&call_identity(base,scene)&&!std::memcmp(reinterpret_cast<void*>(scene.address+0x108),restored?original:published,16);}
 bool restore(){if(unknown)return false;if(!attached)return true;if(!current()){unknown=true;return false;}if(!restored){std::memcpy(reinterpret_cast<void*>(scene.address+0x108),original,16);restored=true;}return true;}
 bool close(){if(!restore())return false;attached=false;owner=0;return true;}
 void poll_context(SaveContext context){if(attached&&!unknown&&!restored&&context==SaveContext::Changed)restore();}
 void poll(){if(attached&&!unknown&&!restored)poll_context(selected_context(base,gi,guid));}
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p,const Profile&profile){
  if(unknown){p.error=uncertain;return;}
  if(p.mode){if(!attached||owner!=p.owner||session!=s||std::memcmp(&scene,&p.scene,16)||std::memcmp(&gi,&p.gi,16)||std::memcmp(leases,p.leases,16)||std::memcmp(guid,p.guid,16)){p.error=rejected;return;}
   if(p.mode==2){if(!close()){p.error=uncertain;return;}p.readback=p.expected;p.state=3;return;}
   if(!current()){unknown=true;p.error=uncertain;return;}p.readback=restored?p.expected:p.replacement;p.state=restored?4U:2U;return;}
  if(attached){p.error=rejected;return;}
  const CallIdentity ids[]={p.scene,p.gi};for(unsigned i=0;i<2;++i)if(!call_identity(b,ids[i])||!p.leases[i]||!pool.owns_object(s,p.leases[i],ids[i].address)){p.error=rejected;return;}
  e33_story_action::Dispatcher proof;proof.base=b;proof.gi=p.gi;std::memcpy(proof.guid,p.guid,16);
  if(p.guid[0]!=0xe33c5701U||!proof.bound()||!picto_class(b,p.scene.address,"MovieScene","/Script/MovieScene")||
     !e33_mesh::candidate_name(b,p.scene.address+24,"MovieScene_0")||
     !e33_mesh::named(b,local_read<uint64_t>(p.scene.address+32),profile.name,profile.path)){p.error=rejected;return;}
  const auto cls=local_read<uint64_t>(p.scene.address+16),field=picto_struct_field(b,cls,"PlaybackRange","StructProperty",0x108,16);
  if(!field||!e33_mesh::named(b,local_read<uint64_t>(field+0x70),"MovieSceneFrameRange","/Script/MovieScene")||!tick_rate(b,p.scene.address,cls)){p.error=rejected;return;}
  const auto range=p.scene.address+0x108;
  if(local_read<uint8_t>(range)!=1||local_read<int32_t>(range+4)!=profile.lower||local_read<uint8_t>(range+8)!=0||local_read<uint32_t>(range+12)!=p.expected){p.error=rejected;return;}
  base=b;session=s;owner=p.owner;scene=p.scene;gi=p.gi;restored=false;std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,sizeof(guid));std::memcpy(original,reinterpret_cast<void*>(range),16);std::memcpy(published,original,16);std::memcpy(published+12,&p.replacement,4);
  unknown=true;std::memcpy(reinterpret_cast<void*>(range+12),&p.replacement,4);attached=true;
  if(!current()){p.error=uncertain;return;}unknown=false;p.readback=p.replacement;p.state=1;
 }
};
struct Dispatcher {
 Owner owners[2]{};bool attached=false,unknown=false;uint64_t next_poll=0;
 void refresh(){attached=false;for(auto& row:owners){attached=attached||row.attached;unknown=unknown||row.unknown;}}
 bool active()const{for(const auto&row:owners)if(row.attached&&!row.restored&&!row.unknown)return true;return false;}
 void poll(){
  if(unknown||!active())return;
  const auto now=GetTickCount64();if(now<next_poll)return;next_poll=now+50;
  for(auto&row:owners)row.poll();refresh();
 }
 bool protects(uint64_t token)const{for(const auto&row:owners)if(row.protects(token))return true;return false;}
 bool close(){if(unknown)return false;bool done=true;for(auto&row:owners)if(!row.close())done=false;refresh();return done;}
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  const auto index=profile_for(p.expected,p.replacement);
  if(p.version!=3||p.op!=operation||!p.owner||p.error||p.state||p.mode>2||p.readback||index<0){p.error=rejected;return;}
  for(auto value:p.tail)if(value){p.error=rejected;return;}
  if(unknown){p.error=uncertain;return;}
  owners[index].run(b,s,pool,p,profiles[index]);refresh();
 }
};
}
