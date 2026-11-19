// Save-scoped replacement of one enemy row with one guaranteed reward.
#pragma once
#include "story_enemy_loot_packet.h"
#include "story_identity_engine_bytes.h"
namespace e33_story_enemy_loot {
struct Row {uint64_t name=0,data=0;int hash=0;};
struct Dispatcher {
 e33_story_items::Dispatcher* definitions_owner=nullptr;
 CallIdentity gi{};uint64_t gi_lease=0;uint32_t guid[4]{};
 bool bound()const{e33_story_action::Dispatcher proof;proof.base=base;proof.gi=gi;std::memcpy(proof.guid,guid,16);return proof.bound();}
 uint64_t base=0,session=0,owner=0;CallIdentity target{},source{},map_class{},map_add{};uint64_t leases[4]{};
 // GenericMap_Add allocates this bounded cache through the engine allocator.
 // It intentionally survives SDK reconnects until process exit, just like the
 // permanent opcode slots. On detach every borrowed row pointer is zeroed.
 // No UObject or World is retained by the idle cache, and no engine allocation
 // is ever passed to the CRT allocator or an unverified map destructor.
 alignas(8)uint8_t cache[80]{},original_header[80]{},published[80]{};
 bool initialized=false,attached=false,unknown=false;uint32_t old_count=0,count=0,consumers=0;uint64_t definitions[16]{};Packet request{};
 bool active()const{return owner||attached;}
 bool protects(uint64_t token)const{if(!active())return false;if(token==gi_lease)return true;for(auto lease:leases)if(lease==token)return true;return false;}
 bool rows(uint64_t map,std::vector<Row>&output)const{
  PictoSparseView view{};if(!picto_sparse(map,24,4096,view))return false;
  const auto size=local_read<int32_t>(map+72);const auto heap=local_read<uint64_t>(map+64),buckets=heap?heap:map+56;
  if(size<1||size>4096||(size&(size-1))||(!heap&&size>2))return false;
  std::vector<uint8_t>seen(size_t(view.count),0);int total=0;
  for(int bucket=0;bucket<size;++bucket){int index=local_read<int32_t>(buckets+uint64_t(bucket)*4);
   for(int steps=0;index!=-1;++steps){
    if(index<0||index>=view.count||steps>=view.count||!view.active(index)||seen[size_t(index)])return false;
    seen[size_t(index)]=1;++total;const auto at=view.data+uint64_t(index)*24;
    if(local_read<int32_t>(at+20)!=bucket)return false;
    output.push_back({local_read<uint64_t>(at),local_read<uint64_t>(at+8),bucket});index=local_read<int32_t>(at+16);
   }
  }return total==view.count-view.free;
 }
 bool enemy_schema(uint64_t b,uint64_t schema)const{
  return call_capture(b,schema).address&&e33_mesh::named(b,schema,"S_jRPG_Enemy","/Game/jRPGTemplate/Structures/S_jRPG_Enemy")&&
   local_read<int32_t>(schema+0x58)==505&&
   picto_struct_field(b,schema,"EnemyHardcodedName_4_0FAACC934CB2957BA37E888624E5835F","NameProperty",0,8)&&
   picto_struct_field(b,schema,"PossibleLoot_49_4083979C4864530BB4DB9EB51A43C8AA","ArrayProperty",264,16);
 }
 bool table(uint64_t b,uint64_t object)const{
  const uint8_t accessor[]={0x48,0x8d,0x41,0x30,0xc3};
  const auto cls=local_read<uint64_t>(object+16),fn=local_read<uint64_t>(local_read<uint64_t>(object)+0x2d8);
  return (e33_mesh::named(b,cls,"DataTable","/Script/Engine")||e33_mesh::named(b,cls,"CompositeDataTable","/Script/Engine"))&&
   enemy_schema(b,local_read<uint64_t>(object+40))&&fn&&!std::memcmp(reinterpret_cast<void*>(fn),accessor,sizeof(accessor));
 }
 bool current()const{return attached&&call_identity(base,target)&&!std::memcmp(reinterpret_cast<void*>(target.address+48),published,80);}
 bool definition(uint64_t name)const{if(!current())return false;for(unsigned i=0;i<count;++i)if(definitions[i]==name)return true;return false;}
 bool close(){
  if(unknown||consumers)return false;
  if(attached){if(!current()){unknown=true;return false;}std::memcpy(reinterpret_cast<void*>(target.address+48),original_header,80);attached=false;}
  if(initialized){PictoSparseView view{};if(!picto_sparse(reinterpret_cast<uint64_t>(cache),24,4096,view)){unknown=true;return false;}
   for(int i=0;i<view.count;++i)if(view.active(i))*reinterpret_cast<uint64_t*>(view.data+uint64_t(i)*24+8)=0;}
  if(definitions_owner){if(!definitions_owner->consumers)return false;--definitions_owner->consumers;definitions_owner=nullptr;}
  owner=0;count=0;gi_lease=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p,e33_story_items::Dispatcher&items){
  if(!e33_story_enemy_loot::valid(p)||unknown){p.error=unknown?uncertain:rejected;return;}
  if(p.mode){
   auto normalized=p;normalized.mode=request.mode;if(std::memcmp(&normalized,&request,sizeof(request))){p.error=rejected;return;}
   if(owner!=p.owner||session!=s||std::memcmp(&target,&p.target,16)||std::memcmp(&source,&p.source,16)||count!=p.count){p.error=4100;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   if(!current()){p.error=uncertain;unknown=true;return;}p.old_rows=old_count;p.new_rows=old_count;p.state=2;return;
  }
  if(active()){p.error=4101;return;}
  const auto bytes=reinterpret_cast<const uint8_t*>(&p);
  std::memcpy(&gi,bytes+2024,16);std::memcpy(&gi_lease,bytes+2040,8);std::memcpy(guid,bytes+2048,16);base=b;
  const auto reward_id=reinterpret_cast<const char*>(&p)+2064;uint64_t reward_name=0;
  if(!call_identity(b,gi)||!pool.owns_object(s,gi_lease,gi.address)||!bound()||!items.current()||
     !e33_blueprint_names::resolve(b,reward_id,reward_name)||!items.definition(reward_name)){p.error=rejected;return;}
  const CallIdentity ids[]={p.target,p.source,p.map_class,p.map_add};
  for(unsigned i=0;i<4;++i)if(!call_identity(b,ids[i])||!pool.owns_object(s,p.leases[i],ids[i].address)){p.error=4102;return;}
  if(!e33_mesh::named(b,p.target.address,"DT_jRPG_Enemies","/Game/jRPGTemplate/Datatables/DT_jRPG_Enemies")||
     !e33_mesh::named(b,p.source.address,p.source_asset,p.source_package)||!table(b,p.target.address)||!table(b,p.source.address)||
     !e33_mesh::named(b,p.map_class.address,"BP_ItemUpgradeSystem_C","/Game/Gameplay/Pictos/BP_ItemUpgradeSystem")||!call_is_class(b,p.map_class.address)||
     !e33_mesh::named(b,p.map_add.address,"Map_Add","BlueprintMapLibrary")||local_read<uint64_t>(p.map_add.address+0xd8)!=b+0x34cba80||
     std::memcmp(reinterpret_cast<void*>(b+0x34a7a80),generic_map_add_code,sizeof(generic_map_add_code))){p.error=4103;return;}
  const auto field=picto_struct_field(b,p.map_class.address,"ItemInstances","MapProperty",576,80);
  const auto key=field?local_read<uint64_t>(field+0x70):0,value=field?local_read<uint64_t>(field+0x78):0;
  if(!field||!key||!value||(local_read<uint8_t>(field+0x98)&1)||
     !exact_name(b,local_read<uint64_t>(key+8),"NameProperty")||!exact_name(b,local_read<uint64_t>(value+8),"ObjectProperty")||
     local_read<int32_t>(key+0x34)!=8||local_read<int32_t>(value+0x34)!=8||local_read<int32_t>(key+0x44)!=0||local_read<int32_t>(value+0x44)!=8||
     local_read<int32_t>(field+0x80)!=8||local_read<int32_t>(field+0x8c)!=24){p.error=4104;return;}
  base=b;std::vector<Row>before,added;
  if(!rows(p.target.address+48,before)||!rows(p.source.address+48,added)||added.empty()||before.empty()||before.size()>4096){p.error=4105;return;}
  uint64_t wanted[16]{};
  for(unsigned i=0;i<p.count;++i){
   if(!e33_blueprint_names::resolve(b,p.names[i],wanted[i])){p.error=4106;return;}
   for(unsigned j=0;j<i;++j)if(wanted[i]==wanted[j]){p.error=4107;return;}
   unsigned found=0;
   unsigned originals=0;for(const auto&row:before)if(row.name==wanted[i])++originals;
   if(originals!=1){p.error=4108;return;} // This API replaces only the named existing enemy row.
   for(const auto&row:added)if(row.name==wanted[i]){
    const auto loot=local_read<uint64_t>(row.data+264);
    uint64_t reward=0;if(!e33_blueprint_names::resolve(b,reward_id,reward)){p.error=4109;return;}
    if(!row.data||(row.data&7)||local_read<uint64_t>(row.data)!=row.name||
       local_read<uint64_t>(p.target.address+40)!=local_read<uint64_t>(p.source.address+40)||
       !loot||(loot&7)||local_read<int32_t>(row.data+272)!=1||local_read<int32_t>(row.data+276)<1||
       local_read<int32_t>(row.data+276)>16||local_read<uint64_t>(loot+8)!=reward||
       local_read<int32_t>(loot+16)!=1||local_read<double>(loot+24)!=100.0||local_read<int32_t>(loot+32)!=0){p.error=4109;return;}
    ++found;
   }
   if(found!=1){p.error=4110;return;}
  }
  std::vector<Row>union_rows=before;
  for(auto&row:union_rows)if(row.name==wanted[0])for(const auto&replacement:added)if(replacement.name==row.name)row.data=replacement.data;
  if(initialized){
   std::vector<Row>cached;if(!rows(reinterpret_cast<uint64_t>(cache),cached)||cached.size()!=union_rows.size()){p.error=4111;return;}
   for(const auto&row:cached){unsigned found=0;for(const auto&desired:union_rows)if(desired.name==row.name)++found;if(found!=1){p.error=4112;return;}}
  }else{
   std::memset(cache,0,80);*reinterpret_cast<int32_t*>(cache+44)=128;*reinterpret_cast<int32_t*>(cache+48)=-1;
   const uint64_t null_object=0;
   unknown=true; // A partial engine allocation is never rebuilt on an uncertain retry.
   for(const auto&row:union_rows)reinterpret_cast<void(__fastcall*)(void*,void*,const void*,const void*)>(b+0x34a7a80)(cache,reinterpret_cast<void*>(field),&row.name,&null_object);
   initialized=true;unknown=false;
  }
  std::vector<Row>built;
  if(!rows(reinterpret_cast<uint64_t>(cache),built)||built.size()!=union_rows.size()){p.error=4113;return;}
  // Prove that the reflected FName map uses the same buckets as each native
  // DataTable map. No guessed FName hashing or hand-constructed hash chains.
  const auto built_size=local_read<int32_t>(reinterpret_cast<uint64_t>(cache)+72),
   original_size=local_read<int32_t>(p.target.address+48+72),source_size=local_read<int32_t>(p.source.address+48+72);
  for(const auto&row:built){unsigned found=0;for(const auto&desired:union_rows)if(desired.name==row.name){
    const int mask=(std::find_if(before.begin(),before.end(),[&](const Row&r){return r.name==row.name;})!=before.end()?original_size:source_size)-1;
    if((row.hash&mask)!=(desired.hash&mask)||row.data){p.error=4114;return;}++found;
   }if(found!=1){p.error=4115;return;}}
  (void)built_size;
  PictoSparseView storage{};if(!picto_sparse(reinterpret_cast<uint64_t>(cache),24,4096,storage)){p.error=4116;return;}
  for(int i=0;i<storage.count;++i)if(storage.active(i)){
   const auto at=storage.data+uint64_t(i)*24,name=local_read<uint64_t>(at);
   for(const auto&row:union_rows)if(row.name==name){*reinterpret_cast<uint64_t*>(at+8)=row.data;break;}
  }
  request=p;session=s;owner=p.owner;target=p.target;source=p.source;map_class=p.map_class;map_add=p.map_add;std::memcpy(leases,p.leases,sizeof(leases));old_count=uint32_t(before.size());count=p.count;std::memcpy(definitions,wanted,sizeof(wanted));
  std::memcpy(original_header,reinterpret_cast<void*>(target.address+48),80);std::memcpy(published,cache,80);
  std::memcpy(reinterpret_cast<void*>(target.address+48),published,80);attached=true;definitions_owner=&items;++items.consumers;
  p.old_rows=old_count;p.new_rows=old_count;p.state=1;
 }
};
}
