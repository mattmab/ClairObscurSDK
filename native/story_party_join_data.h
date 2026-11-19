#pragma once
// Only a newly constructed vanilla join action may borrow one explicitly requested character row name.
// No campaign action is dispatched here; the normal executor owns recruitment.
namespace e33_story_party_join_data {
constexpr uint32_t operation=258,rejected=4270,uncertain=4271,busy=4272;
#pragma pack(push,1)
struct Packet {uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[3]{};uint64_t leases[3]{};uint32_t guid[4]{},mode=0,reserved=0;char character[96]{};uint8_t tail[20768]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Party join data packet");
inline bool valid_character(const char (&name)[96]) {
 bool ended=false;unsigned count=0;
 for(char c:name){if(!c){ended=true;continue;}
  if(ended||!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'))return false;
  ++count;
 }return count>0&&count<96&&ended;
}
struct Dispatcher {
 uint64_t base=0,session=0,owner=0;CallIdentity ids[3]{};uint64_t leases[3]{},role=0;uint32_t guid[4]{};
 uint8_t original[16]{},published[16]{};bool attached=false,unknown=false;char character[96]{};
 bool active()const{return attached||unknown;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto t:leases)if(t==token)return true;return false;}
 bool inner(uint64_t descriptor,const char*kind)const{
  const auto p=local_read<uint64_t>(descriptor+0x78);
  return !(local_read<uint8_t>(descriptor+0x70)&1)&&p&&local_read<uint64_t>(p+0x10)==descriptor&&exact_name(base,local_read<uint64_t>(p+8),kind)&&
   local_read<int32_t>(p+0x30)==1&&local_read<int32_t>(p+0x34)==8&&local_read<int32_t>(p+0x44)==0;
 }
 int executing()const{
  if(!call_identity(base,ids[2]))return -1;
  uint64_t descriptor=0;const auto a=picto_field(base,ids[2].address,"GameActionInstancesInExecution","ArrayProperty",168,16,&descriptor);
  if(!a||!inner(descriptor,"ObjectProperty")||
   !e33_mesh::named(base,local_read<uint64_t>(local_read<uint64_t>(descriptor+0x78)+0x70),"GameActionInstance","/Script/SandFall"))return -1;
  const auto data=local_read<uint64_t>(a);const auto count=local_read<int32_t>(a+8),capacity=local_read<int32_t>(a+12);
  if(count<0||capacity<count||capacity>128||(count&&(!data||(data&7))))return -1;
  for(int i=0;i<count;++i){
   const auto instance=local_read<uint64_t>(data+uint64_t(i)*8);
   if(!call_capture(base,instance).address)return -1;
   const auto action=picto_field(base,instance,"GameAction","ObjectProperty",40,8);
   if(!action)return -1;if(local_read<uint64_t>(action)==ids[0].address)return 1;
  }return 0;
 }
 bool current()const{return attached&&call_identity(base,ids[0])&&
  !std::memcmp(reinterpret_cast<void*>(ids[0].address+48),published,16)&&local_read<uint8_t>(ids[0].address+64)==1;}
 bool close(){
  if(unknown)return false;if(!attached)return true;
  if(!current()){unknown=true;return false;}const auto running=executing();
  if(running<0){unknown=true;return false;}if(running)return false;
  std::memcpy(reinterpret_cast<void*>(ids[0].address+48),original,16);attached=false;owner=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.reserved||p.guid[0]!=0xe33c5701U){p.error=rejected;return;}
  for(auto v:p.tail)if(v){p.error=rejected;return;}
  if(!valid_character(p.character)){p.error=rejected;return;}
  if(unknown){p.error=uncertain;return;}
  if(p.mode){
   if(!attached||owner!=p.owner||session!=s||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(guid,p.guid,sizeof(guid))||std::memcmp(character,p.character,sizeof(character))){p.error=rejected;return;}
   if(p.mode==2){if(!close()){p.error=unknown?uncertain:busy;return;}p.state=3;return;}
   if(!current()){unknown=true;p.error=uncertain;return;}p.state=2;return;
  }
  if(attached){p.error=rejected;return;}
  for(unsigned i=0;i<3;++i)if(!call_identity(b,p.ids[i])||!p.leases[i]||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  const auto action=p.ids[0].address,gi=p.ids[1].address,executor=p.ids[2].address;
  if(!picto_class(b,action,"BP_GameAction_CharacterJoinGroup_C","/Game/Gameplay/GameActionsSystem/SetCurrentParty/BP_GameAction_CharacterJoinGroup")||
   local_read<uint64_t>(action+32)!=gi||(local_read<uint32_t>(action+8)&0x40018030U)||
   !picto_class(b,executor,"BP_GameActionExecutorComponent_C","/Game/Gameplay/GameActionsSystem/BP_GameActionExecutorComponent")){p.error=rejected;return;}
  e33_story_action::Dispatcher selected;selected.base=b;selected.gi=p.ids[1];std::memcpy(selected.guid,p.guid,16);
  e33_retired_world::Snapshot now{};e33_retired_world::TargetOps world{b};
  if(!selected.bound()||!world.observe(now)||zone_ref(b,now.world.address,"OwningGameInstance")!=gi){p.error=rejected;return;}
  bool current_world=false;for(auto o=executor,n=uint64_t(0);o&&++n<32;o=local_read<uint64_t>(o+32))if(o==now.world.address){current_world=true;break;}
  if(!current_world){p.error=rejected;return;}
  base=b;uint64_t ad=0,bd=0;
  const auto array=picto_field(b,action,"CharacterSaveStateRowName","ArrayProperty",48,16,&ad),automatic=picto_field(b,action,"AutoAddToParty","BoolProperty",64,1,&bd);
  if(!array||!automatic||!inner(ad,"NameProperty")||local_read<uint32_t>(bd+0x70)!=0xff010001U||local_read<uint8_t>(automatic)!=1||
   local_read<uint64_t>(array)||local_read<uint64_t>(array+8)||!e33_blueprint_names::resolve(b,p.character,role)){p.error=rejected;return;}
  session=s;std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,sizeof(guid));
  const auto running=executing();if(running){p.error=running>0?busy:rejected;return;}
  std::memcpy(original,reinterpret_cast<void*>(array),16);const auto pointer=reinterpret_cast<uint64_t>(&role);const uint32_t count=1;
  std::memcpy(published,&pointer,8);std::memcpy(published+8,&count,4);std::memcpy(published+12,&count,4);
  std::memcpy(character,p.character,sizeof(character));owner=p.owner;unknown=true;attached=true;std::memcpy(reinterpret_cast<void*>(array),published,16);
  if(!current()){p.error=uncertain;return;}unknown=false;p.state=1;
 }
};
}
