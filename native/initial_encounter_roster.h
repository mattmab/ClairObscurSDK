#pragma once
// Full roster is borrowed only across the original SpawnEnemies call. The
// engine creates every actor and initializes initiative in its normal order.
namespace e33_initial_roster {
constexpr uint32_t operation=257,rejected=4260,uncertain=4261;
#pragma pack(push,1)
struct Packet {uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[7]{};uint64_t leases[7]{};uint32_t mode=0,count=0;char names[10][96]{};uint32_t calls=0;uint8_t tail[19820]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"initial roster packet");
struct Dispatcher {
 uint64_t base=0,session=0,owner=0,instance=0;CallIdentity ids[7]{};uint64_t leases[7]{};uint32_t count=0,calls=0;char requested[10][96]{};DWORD thread=0;
 bool unknown=false,routing=false,attached=false,in_flight=false;uint64_t slot=0;uint8_t before[80]{},published[80]{};
 alignas(8)uint8_t maps[10][80]{};bool initialized[10]{};uint32_t stride=0;uint64_t map_field=0;
 inline static Dispatcher* live=nullptr;
 bool active()const{return owner||routing||attached||in_flight;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto t:leases)if(t==token)return true;return false;}
 bool context(uint64_t manager)const{
  return thread==GetCurrentThreadId()&&call_identity(base,ids[0])&&call_identity(base,ids[1])&&call_identity(base,ids[2])&&
   picto_class(base,manager,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")&&
   local_read<uint64_t>(manager+32)==ids[2].address&&zone_ref(base,ids[2].address,"AC_jRPG_BattleManager")==manager&&
   e33_dialogue_text::Dispatcher{}.world(base,ids[2].address)==ids[1].address&&local_read<uint64_t>(manager+1240)==instance;
 }
 uint64_t begin(uint64_t fn,void*object,void*){
  const auto m=reinterpret_cast<uint64_t>(object);
  if(unknown||in_flight||fn!=ids[4].address||!context(m)||local_read<uint8_t>(m+497))return 0;
  PictoSparseView cache{};if(!picto_sparse(reinterpret_cast<uint64_t>(maps[count-1]),stride,128,cache)||cache.count-cache.free!=int(count)){unknown=true;return 0;}
  slot=m+1880;std::memcpy(before,reinterpret_cast<void*>(slot),80);std::memcpy(published,maps[count-1],80);
  // The retained manager class proves the map descriptor. No engine call,
  // allocation, actor spawn or turn-order mutation occurs in this callback.
  in_flight=true;std::memcpy(reinterpret_cast<void*>(slot),published,80);return 1;
 }
 void end(uint64_t token){
  if(!token)return;
  if(!in_flight||!slot||std::memcmp(reinterpret_cast<void*>(slot),published,80)){unknown=true;return;}
  std::memcpy(reinterpret_cast<void*>(slot),before,80);slot=0;in_flight=false;++calls;
 }
 static e33_blueprint_transform::Decision pre(void*ctx,uint64_t fn,void*object,void*frame){
  auto*self=static_cast<Dispatcher*>(ctx);uint64_t token=0;
  __try{token=self->begin(fn,object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;}
  return {token,false};
 }
 static void post(void*ctx,uint64_t token){auto*self=static_cast<Dispatcher*>(ctx);__try{self->end(token);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;}}
 static void __fastcall wrapper(void*object,void*frame,void*result){
  auto*self=live;if(!self)return;const auto token=pre(self,self->ids[4].address,object,frame).token;
  reinterpret_cast<e33_trace::Entry>(self->base+0x13937a0)(object,frame,result);post(self,token);
 }
 bool close(){
  if(unknown||in_flight)return false;
  if(attached){auto*p=reinterpret_cast<void*volatile*>(ids[4].address+0xd8);
   if(InterlockedCompareExchangePointer(p,reinterpret_cast<void*>(base+0x13937a0),reinterpret_cast<void*>(wrapper))!=reinterpret_cast<void*>(wrapper)){unknown=true;return false;}
   attached=false;
  }
  if(routing){if(!e33_blueprint_transform::detach(this)||!BlueprintDirectTrace::release_narrative(ids[4].address))return false;routing=false;}
  owner=0;live=nullptr;return true;
 }
 template<class Pool,class EnemyOwner>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p,EnemyOwner&enemy){
  if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.count<1||p.count>10||p.calls){p.error=rejected;return;}
  for(auto v:p.tail)if(v){p.error=rejected;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||count!=p.count||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(requested,p.names,sizeof(requested))){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   if(unknown){p.error=uncertain;return;}p.calls=calls;p.state=2;return;
  }
  if(active()||live){p.error=rejected;return;}
  for(unsigned i=0;i<7;++i)if(!call_identity(b,p.ids[i])||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  base=b;session=s;std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));thread=GetCurrentThreadId();
  if(!enemy.has_work()||!enemy.token_matches(p.owner)||!enemy.owned_instance_name(b,s,pool,p.owner,ids[0],instance)||
     !e33_mesh::named(b,local_read<uint64_t>(ids[3].address+16),"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
     local_read<uint64_t>(ids[3].address+32)!=ids[2].address||zone_ref(b,ids[2].address,"AC_jRPG_BattleManager")!=ids[3].address||
     e33_dialogue_text::Dispatcher{}.world(b,ids[2].address)!=ids[1].address||
     local_read<uint8_t>(ids[3].address+168)||local_read<uint8_t>(ids[3].address+1961)||local_read<int32_t>(ids[3].address+208)) {p.error=4262;return;}
  const auto cls=local_read<uint64_t>(ids[3].address+16),fn=ids[4].address;
  if(local_read<uint64_t>(fn+32)!=cls||!exact_name(b,fn+24,"SpawnEnemies")||local_read<uint32_t>(fn+0xb0)!=0xc820000U||
     local_read<uint16_t>(fn+0xb6)||local_read<uint64_t>(fn+0xd8)!=b+0x13937a0||
     !e33_mesh::named(b,ids[5].address,"DT_jRPG_Enemies","/Game/jRPGTemplate/Datatables/DT_jRPG_Enemies")||
     !e33_mesh::named(b,ids[6].address,"Map_Add","BlueprintMapLibrary")||local_read<uint64_t>(ids[6].address+0xd8)!=b+0x34cba80||
     std::memcmp(reinterpret_cast<void*>(b+0x34a7a80),generic_map_add_code,sizeof(generic_map_add_code))){p.error=4263;return;}
  if(!picto_struct_field(b,cls,"IsBattleInitialized","BoolProperty",168,1)||!picto_struct_field(b,cls,"HasSpawnedEnemies","BoolProperty",497,1)||
     !picto_struct_field(b,cls,"CurrentBattleStartParams","StructProperty",1224,344)){p.error=4264;return;}
  map_field=picto_struct_field(b,cls,"CurrentBattleEnemies","MapProperty",1880,80);
  const auto key=map_field?local_read<uint64_t>(map_field+0x70):0,val=map_field?local_read<uint64_t>(map_field+0x78):0;
  if(!map_field||!key||!val||!exact_name(b,local_read<uint64_t>(key+8),"IntProperty")||!exact_name(b,local_read<uint64_t>(val+8),"NameProperty")||
     local_read<int32_t>(key+0x34)!=4||local_read<int32_t>(key+0x44)||local_read<int32_t>(val+0x34)!=8||local_read<int32_t>(val+0x44)!=4||
     local_read<int32_t>(map_field+0x80)!=4||local_read<int32_t>(map_field+0x8c)!=20||(local_read<uint8_t>(map_field+0x98)&1)){p.error=4265;return;}
  stride=20;PictoSparseView definitions{};if(!picto_sparse(ids[5].address+48,24,4096,definitions)){p.error=4266;return;}
  uint64_t names[10]{};
  for(unsigned i=0;i<10;++i){
   const auto end=std::memchr(p.names[i],0,96);if(!end){p.error=rejected;return;}
   const auto length=static_cast<const char*>(end)-p.names[i];
   for(size_t j=size_t(length)+1;j<96;++j)if(p.names[i][j]){p.error=rejected;return;}
   if(i>=p.count){if(length){p.error=rejected;return;}continue;}
   if(!length||!e33_blueprint_names::resolve(b,p.names[i],names[i])){p.error=4267;return;}
   unsigned found=0;for(int j=0;j<definitions.count;++j)if(definitions.active(j)&&local_read<uint64_t>(definitions.data+uint64_t(j)*24)==names[i])++found;
   if(found!=1){p.error=4268;return;}
  }
  auto*cache=maps[p.count-1];
  if(!initialized[p.count-1]){
   std::memset(cache,0,80);*reinterpret_cast<int32_t*>(cache+44)=128;*reinterpret_cast<int32_t*>(cache+48)=-1;
   // At most 55 POD entries across all ten group sizes for the process lifetime.
   unknown=true;for(int32_t i=0;i<int32_t(p.count);++i)reinterpret_cast<void(__fastcall*)(void*,void*,const void*,const void*)>(b+0x34a7a80)(cache,reinterpret_cast<void*>(map_field),&i,&names[i]);
   initialized[p.count-1]=true;unknown=false;
  }
  PictoSparseView view{};if(!picto_sparse(reinterpret_cast<uint64_t>(cache),20,128,view)||view.count!=int(p.count)||view.free){p.error=4269;return;}
  bool seen[10]{};for(int j=0;j<view.count;++j){const auto at=view.data+uint64_t(j)*20;const auto k=local_read<int32_t>(at);
   if(k<0||k>=int(p.count)||seen[k]){p.error=4269;return;}seen[k]=true;std::memcpy(reinterpret_cast<void*>(at+4),&names[k],8);
  }
  if(!BlueprintDirectTrace::retain_narrative(b,fn)){p.error=rejected;return;}
  if(!e33_blueprint_transform::attach(this,fn,pre,post)){BlueprintDirectTrace::release_narrative(fn);p.error=rejected;return;}routing=true;
  HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(wrapper),&pinned)){close();p.error=rejected;return;}
  live=this;if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(fn+0xd8),reinterpret_cast<void*>(wrapper),reinterpret_cast<void*>(b+0x13937a0))!=reinterpret_cast<void*>(b+0x13937a0)){close();p.error=rejected;return;}
  attached=true;owner=p.owner;count=p.count;calls=0;std::memcpy(requested,p.names,sizeof(requested));p.state=1;
 }
};
}
