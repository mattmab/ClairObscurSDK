#pragma once
#include "story_trial_data_registry.h"
#include "encounter_action_profile.h"
namespace e33_story_trial_data {
constexpr uint32_t operation=260,rejected=4290,uncertain=4291,busy=4292;
#pragma pack(push,1)
struct Packet {uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[8]{};uint64_t leases[8]{};uint32_t guid[4]{},mode=0,reserved=0;e33_encounter_action::Profile profile{};uint8_t tail[19332]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Owned trial data packet");
// ids: owned action, vanilla class, FBattleStartParams, private encounter table,
// GI, vanilla music asset, KismetSystemLibrary CDO, ObjectToSoft conversion.
struct Dispatcher {
 uint64_t base=0,session=0,owner=0;CallIdentity ids[8]{};uint64_t leases[8]{};uint32_t guid[4]{};e33_encounter_action::Profile profile{};uint32_t profile_padding=0;
 // Six PartySlots occupy 72 bytes; all engine-value buffers keep natural
 // 8-byte boundaries without compiler-inserted alignment padding.
 alignas(8)uint8_t original[344]{},published[344]{},party[72]{},conversion[48]{};
 bool attached=false,unknown=false,converted=false;uint8_t padding[5]{};uint64_t music_field=0;
 bool active()const{return attached||converted||unknown;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto held:leases)if(held==token)return true;return false;}
 bool conversion_ready()const{
  using namespace e33_mesh;
  const auto library=call_identity(base,ids[6]),function=call_identity(base,ids[7]);
  static const MeshField fields_expected[]={
   {"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0,"Object"},
   {"ReturnValue","SoftObjectProperty",8,40,7881299347899776ULL,0x6e128d8ULL,"","",0,"",0,""}};
  if(!library||!function||!named(base,library,"Default__KismetSystemLibrary","/Script/Engine")||
   !named(base,local_read<uint64_t>(function+32),"KismetSystemLibrary","/Script/Engine")||
   !exact_name(base,function+24,"Conv_ObjectToSoftObjectReference")||local_read<uint32_t>(function+0xb0)!=335684611U||
   local_read<uint16_t>(function+0xb6)!=48||local_read<uint16_t>(function+0xb8)!=8||local_read<int32_t>(function+0x58)!=48||
   local_read<uint64_t>(function+0xd8)!=base+0x383a400||!fields(base,function,fields_expected,2)||
   local_read<uint64_t>(base+0x6e128d8+0xf0)!=base+0x1368190||local_read<uint8_t>(base+0x1368190)!=0x45||
   local_read<uint8_t>(base+0x1368191)!=0x85||local_read<uint8_t>(base+0x1368192)!=0xc9)return false;
  const auto pe=local_read<uint64_t>(local_read<uint64_t>(library)+0x268);
  return pe==base+0x1393330||pe==base+0x332bb90;
 }
 bool current()const{return attached&&registration.offset(base,ids[1],ids[0],ids[2].address)==48;}
 bool close(){
  if(unknown)return false;
  if(attached){if(!current()){unknown=true;return false;}
   registration.ready=false;std::memcpy(reinterpret_cast<void*>(ids[0].address+48),original,344);attached=false;registration={};}
  if(converted){
   if(!conversion_ready()){unknown=true;return false;}
   const uint8_t empty[40]{};unknown=true;
   reinterpret_cast<void(__fastcall*)(void*,void*,const void*,int)>(base+0x1368190)(reinterpret_cast<void*>(music_field),conversion+8,empty,1);
   converted=false;unknown=false;
  }owner=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.reserved||p.guid[0]!=0xe33c5701U||!e33_encounter_action::valid(p.profile)){p.error=rejected;return;}
  for(auto v:p.tail)if(v){p.error=rejected;return;}if(unknown){p.error=uncertain;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(guid,p.guid,16)||std::memcmp(&profile,&p.profile,sizeof(profile))){p.error=rejected;return;}
   if(p.mode==2){if(!close()){p.error=uncertain;return;}p.state=3;return;}
   if(!current()){unknown=true;p.error=uncertain;return;}p.state=2;return;
  }
  if(active()||registration.ready){p.error=rejected;return;}
  for(unsigned i=0;i<8;++i)if(!call_identity(b,p.ids[i])||!p.leases[i]||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  base=b;session=s;profile=p.profile;std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,16);
  const auto action=ids[0].address,cls=ids[1].address,structure=ids[2].address;
  if(!e33_mesh::named(b,cls,"BP_GameAction_TriggerBattle_C","/Game/Gameplay/GameActionsSystem/TriggerBattle/BP_GameAction_TriggerBattle")||
   local_read<uint64_t>(action+16)!=cls||local_read<uint64_t>(action+32)!=ids[4].address||local_read<uint32_t>(action+8)&0x40018030U||
   !e33_mesh::named(b,ids[3].address,profile.table_asset,profile.table_package)||
   !e33_mesh::named(b,ids[5].address,profile.music_asset,profile.music_package)){p.error=rejected;return;}
  e33_story_action::Dispatcher save;save.base=b;save.gi=ids[4];std::memcpy(save.guid,guid,16);
  const auto value=picto_struct_field(b,cls,"Battle Start Params","StructProperty",48,344);
  if(!save.bound()||!value||local_read<uint64_t>(value+0x70)!=structure){p.error=rejected;return;}
  e33_enemy_spawn::TargetBattleParameterOps<Pool> engine{b,s,pool,ids[2],ids[0],ids[1],p.leases[2],p.leases[0],p.leases[1],nullptr,nullptr};
  if(!engine.engine_ready()){p.error=rejected;return;}
  const auto encounter=engine.field(structure,"EncounterRow_25_76E166214BC95AA2A6A68DAD97A47C62",0,16,0x6e136a0,0x1000000005ULL),
   music=engine.field(structure,"MusicParameters_58_3EF84D0A4944D7C4EF7BFCB46E28D32F",104,48,0x6e136a0,0x8000000000005ULL),
   team=engine.field(structure,"OverrideParty_63_56C3E35647CCE3DAC58BE292F8A3FFC0",200,16,0x6e0de80,5);
  if(!encounter||!music||!team){p.error=rejected;return;}
  const auto row=local_read<uint64_t>(encounter+0x70),music_type=local_read<uint64_t>(music+0x70),inner=local_read<uint64_t>(team+0x78),slot=inner?local_read<uint64_t>(inner+0x70):0;
  if(!engine.named(row,"DataTableRowHandle","/Script/Engine")||!picto_struct_field(b,row,"DataTable","ObjectProperty",0,8)||!picto_struct_field(b,row,"RowName","NameProperty",8,8)||
   !engine.named(music_type,"S_MusicParameters","/Game/Gameplay/Audio/S_MusicParameters")||
   local_read<uint8_t>(team+0x70)&1||!inner||local_read<uint64_t>(inner+0x10)!=team||local_read<int32_t>(inner+0x34)!=12||
   !engine.named(slot,"S_jRPG_PartySlot","/Game/jRPGTemplate/Structures/S_jRPG_PartySlot")||
   !picto_struct_field(b,slot,"CharacterHardcodedName_2_2A63D4C5433428900D69748563F50580","NameProperty",0,8)||
   !picto_struct_field(b,slot,"Formation_5_710E67F044BACE578CEE51AF24DC58B0","ByteProperty",8,1)){p.error=rejected;return;}
  music_field=picto_struct_field(b,music_type,"Music_16_0332400D492AAEF7CE88BEBEA72A3D9B","SoftObjectProperty",0,40);
  const struct {const char*name;const char*kind;int offset;} fields[]={
   {"PlayCameraIntro_21_FE94DAD74E9218AB0C1D48A3DC163272","BoolProperty",97},
   {"ForceFleeImpossible_28_67F4412A4BF319F3EFFE8C8110E1CBC5","BoolProperty",98},
   {"BackToExplorationOnLost_38_6E7B04094D32F81767771FA52BAE96D1","BoolProperty",192},
   {"EncounterLevelOffset_53_1CBE091C40F1DC0A4C5A0EAC44E28B8E","IntProperty",196},
   {"AllowReserveTeam_67_D9994E8845C61EC655889197EAE92383","BoolProperty",216}};
  for(const auto&f:fields){const auto field=picto_struct_field(b,structure,f.name,f.kind,f.offset,f.offset==196?4:1);
   if(!field||(f.offset!=196&&local_read<uint32_t>(field+0x70)!=0xff010001U)){p.error=rejected;return;}}
  const auto frame=action+48;
  if(!music_field||!conversion_ready()||local_read<uint64_t>(frame+200)||local_read<uint64_t>(frame+208)||
   !e33_enemy_spawn::empty_battle_arena_soft_value(reinterpret_cast<void*>(frame+104))){p.error=rejected;return;}
  uint64_t encounter_name=0;if(!e33_blueprint_names::resolve(b,profile.encounter,encounter_name)){p.error=rejected;return;}
  std::memset(party,0,sizeof(party));
  for(unsigned i=0;i<profile.party_count;++i){uint64_t role=0;if(!e33_blueprint_names::resolve(b,profile.characters[i],role)){p.error=rejected;return;}std::memcpy(party+i*12,&role,8);party[i*12+8]=uint8_t(profile.formations[i]);}
  std::memcpy(original,reinterpret_cast<void*>(frame),344);std::memcpy(published,original,344);
  std::memcpy(conversion,&ids[5].address,8);owner=p.owner;unknown=true;converted=true;
  const auto pe=local_read<uint64_t>(local_read<uint64_t>(ids[6].address)+0x268);
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(ids[6].address),reinterpret_cast<void*>(ids[7].address),conversion);
  // This exact top-level asset has no sub-object FString allocation.
  const auto converted_at=reinterpret_cast<uint64_t>(conversion);
  if(!exact_name(b,converted_at+16,profile.music_package)||
   !exact_name(b,converted_at+24,profile.music_asset)||local_read<uint64_t>(converted_at+32)||local_read<uint64_t>(converted_at+40)){p.error=uncertain;return;}
  e33_encounter_action::authored_values(published,ids[3].address,encounter_name,party,conversion+8,profile);
  attached=true;std::memcpy(reinterpret_cast<void*>(frame),published,344);
  registration={b,ids[1],ids[0],ids[2],ids[4],published,true};
  if(!current()){p.error=uncertain;return;}unknown=false;p.state=1;
 }
};
}
