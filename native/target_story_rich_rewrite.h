#pragma once
#include "story_rich_rewrite_packet.h"
#include "target_story_action.h"
#include "target_native_dialogue.h"
namespace e33_story_rewrite {
struct Profile {
 CallIdentity source{};uint64_t lease=0;unsigned count=0;
 OwnedTextStorage text[capacity];TargetTextValue replacement[capacity]{};
 uint16_t before[capacity][kOwnedTextUnits]{};uint32_t lengths[capacity]{};uint64_t hits[capacity]{};
 CallIdentity sound{};uint64_t sound_lease=0;uint32_t sound_mask=0;
};
struct Dispatcher {
 uint64_t base=0,session=0,owner=0,function_lease=0,gi_lease=0;
 CallIdentity function{},gi{},text_cdo{},text_query{};uint64_t text_cdo_lease=0,text_query_lease=0;
 // One engine-owned FString output cache per pinned runtime. It is reused by
 // the engine's FString assignment and intentionally survives SDK reconnects.
 // It contains no UObject references and is never freed by the CRT allocator.
 TargetStringValue key_cache{};
 uint32_t guid[4]{};Profile profiles[profiles_capacity];
 bool routing=false,unknown=false;DWORD thread=0;unsigned in_flight=0;
 struct Swap {TargetTextValue*slot=nullptr;unsigned profile=0,line=0;};Swap swaps[capacity]{};
 struct CameraSwap {uint8_t*slot=nullptr;uint8_t before=0;};CameraSwap cameras[capacity]{};unsigned camera_count=0;
 struct SoundSwap {uint64_t*slot=nullptr;uint64_t before=0;};SoundSwap sounds[capacity]{};unsigned sound_count=0;
 bool active()const{return owner||routing;}
 bool protects(uint64_t token)const{
  if(!active())return false;
  if(token==function_lease||token==gi_lease||token==text_cdo_lease||token==text_query_lease)return true;
  for(const auto&p:profiles)if(p.count&&(token==p.lease||(p.sound_mask&&token==p.sound_lease)))return true;
  return false;
 }
 bool bound()const{
  e33_story_action::Dispatcher proof;proof.base=base;proof.gi=gi;std::memcpy(proof.guid,guid,16);
  return proof.bound();
 }
 static const MeshFunction& key_profile(){
  static const MeshField fields[]={
   {"Text","TextProperty",0,16,0x10000000000080ULL,0x6e1ba00ULL,"","",0,"",0U,""},
   {"OutTableId","NameProperty",16,8,0x18001040000380ULL,0x6e13040ULL,"","",0,"",0U,""},
   {"OutKey","StrProperty",24,16,0x18000000000380ULL,0x6e131d8ULL,"","",0,"",0U,""},
   {"ReturnValue","BoolProperty",40,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
  };
  static const MeshFunction function={"KismetTextLibrary","StringTableIdAndKeyFromText",0x14422403,41,48,40,0x328c560ULL,fields,4};
  return function;
 }
 bool source_key(TargetTextValue text,TargetStringValue&key,uint64_t&table){
  alignas(8)uint8_t args[48]{};std::memcpy(args,&text,16);std::memcpy(args+24,&key_cache,16);
  e33_engine_profile_call::TargetOps call{base,call_identity(base,text_query),call_identity(base,text_cdo),key_profile(),args};
  if(!call.identities()||!call.context()||!call.exact_profile()||!call.recipient_derives()||!call.dispatch_entry()){unknown=true;return false;}
  call.dispatch_once();key_cache=local_read<TargetStringValue>(reinterpret_cast<uint64_t>(args)+24);
  if(args[40]>1||key_cache.count<0||key_cache.count>int(kOwnedTextUnits)||key_cache.capacity<key_cache.count||(!key_cache.data&&key_cache.count)){unknown=true;return false;}
  if(!args[40])return false;
  key=key_cache;table=local_read<uint64_t>(reinterpret_cast<uint64_t>(args)+16);return true;
 }
 bool schema(uint64_t b,uint64_t f)const{
  if(!call_capture(b,f).address||!e33_mesh::named(b,local_read<uint64_t>(f+32),"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||
     !exact_name(b,f+24,"StartRichDialogueLines")||local_read<uint32_t>(f+0xb0)!=214040576U||local_read<uint16_t>(f+0xb6)!=32||
     local_read<uint16_t>(f+0xb8)!=65535||local_read<uint64_t>(f+0xd8)!=b+0x13937a0)return false;
  const auto d=picto_struct_field(b,f,"Dialogue","ObjectProperty",0,8),c=picto_struct_field(b,f,"CharacterAsset","ObjectProperty",8,8),
   a=picto_struct_field(b,f,"RichDialogueLines","ArrayProperty",16,16);
  if(!d||!c||!a||local_read<uint64_t>(d+0x38)!=2251868533162644ULL||local_read<uint64_t>(c+0x38)!=2251868533162644ULL||
     local_read<uint64_t>(a+0x38)!=549890032020ULL||(local_read<uint8_t>(a+0x70)&1))return false;
  const auto inner=local_read<uint64_t>(a+0x78),st=inner?local_read<uint64_t>(inner+0x70):0;
  return inner&&local_read<uint64_t>(inner+16)==a&&exact_name(b,local_read<uint64_t>(inner+8),"StructProperty")&&
   local_read<int32_t>(inner+0x34)==304&&call_capture(b,st).address&&exact_name(b,st+24,"FRichDialogueLine")&&
   local_read<int32_t>(st+0x58)==304&&picto_struct_field(b,st,"LineText_59_150163D04423FC32BC8332BB249FEC44","TextProperty",0,16)&&
   picto_struct_field(b,st,"CameraType_17_1035B24C408190BDC2E6C8A2BD27644D","ByteProperty",24,1)&&
   picto_struct_field(b,st,"Sound_67_713F82BC4689C46AA512BC9A9C4EC3F5","ObjectProperty",16,8);
 }
 uint64_t begin(uint64_t f,void*object,void*frame){
  if(unknown||in_flight||camera_count||sound_count||thread!=GetCurrentThreadId()||f!=function.address||!call_identity(base,function)||!bound())return 0;
  const auto sys=reinterpret_cast<uint64_t>(object),stack=reinterpret_cast<uint64_t>(frame);
  if(!call_capture(base,sys).address||!picto_class(base,sys,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||!stack||
     local_read<uint64_t>(stack+0x10)!=f||local_read<uint64_t>(stack+0x90)||local_read<uint64_t>(stack+0x18)!=sys||
     local_read<uint64_t>(stack+0x20)!=local_read<uint64_t>(f+0x60))return 0;
  const auto locals=local_read<uint64_t>(stack+0x28);if(!locals)return 0;
  const auto dialogue=local_read<uint64_t>(locals);if(!call_capture(base,dialogue).address)return 0;
  unsigned profile=profiles_capacity;
  for(unsigned i=0;i<profiles_capacity;++i)if(profiles[i].count&&call_identity(base,profiles[i].source)&&local_read<uint64_t>(dialogue+16)==profiles[i].source.address){profile=i;break;}
  if(profile==profiles_capacity)return 0;
  e33_dialogue_text::Dispatcher helper;
  const auto controller=local_read<uint64_t>(sys+32),player=helper.object_field(base,controller,"Player"),world=helper.world(base,controller);
  if(!player||!e33_mesh::named(base,local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine")||
     helper.object_field(base,player,"PlayerController")!=controller||helper.object_field(base,sys,"ActiveDialogue")!=dialogue||
     !world||helper.world(base,dialogue)!=world||zone_ref(base,world,"OwningGameInstance")!=gi.address)return 0;
  // RichDialogueLines is an out/reference parameter. The interpreter reads
  // its FOutParmRec destination; the temporary locals slot is not its array.
  const auto array_property=picto_struct_field(base,f,"RichDialogueLines","ArrayProperty",16,16),
   out=local_read<uint64_t>(stack+0x80);
  if(!array_property||!out||(out&7)||local_read<uint64_t>(out)!=array_property||local_read<uint64_t>(out+16))return 0;
  const auto array=local_read<uint64_t>(out+8);
  if(array<0x10000||(array&7))return 0;
  const auto header=local_read<TargetStringValue>(array);
  if(header.count<1||header.count>8||header.capacity<header.count||header.capacity>64||!header.data||(header.data&7))return 0;
  auto&p=profiles[profile];bool used[capacity]{};Swap selected_swaps[capacity]{};unsigned n=0;
  const bool flower=e33_mesh::named(base,p.source.address,"BP_Dialogue_Gardens_GustaveFlower_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Gardens_GustaveFlower");
  for(int i=0;i<header.count;++i){
   auto*slot=reinterpret_cast<TargetTextValue*>(header.data+uint64_t(i)*304);
   // Borrowed FText remains engine-owned. The accessor supports localized
   // histories; only newly constructed SDK text is released by this owner.
   auto text=*slot;if(!text.data)continue;
   TargetStringValue key{};uint64_t table=0;if(!source_key(text,key,table)){if(unknown)return 0;continue;}
   const char*expected=flower?"/Game/StringTables/Dialogs/StandardDialogue/ST_D_Lumiere.ST_D_Lumiere":"/Game/StringTables/Dialogs/DialogueSequence/ST_DS_Lumiere.ST_DS_Lumiere";
   if(!exact_name(base,reinterpret_cast<uint64_t>(&table),expected))continue;
   for(unsigned j=0;j<p.count;++j)if(key.count==int(p.lengths[j])&&key.data&&
      !std::memcmp(reinterpret_cast<void*>(key.data),p.before[j],size_t(key.count)*2)){
    if(used[j]||n==capacity){unknown=true;return 0;}used[j]=true;selected_swaps[n++]={slot,profile,j};break;
   }
  }
  // All discovery and engine calls finish before the first borrowed slot is
  // moved. Swap ownership tokens; never memcpy an extra FText reference.
  if(p.sound_mask&&!call_identity(base,p.sound)){unknown=true;return 0;}
  for(unsigned i=0;i<n;++i){swaps[i]=selected_swaps[i];auto&v=p.text[swaps[i].line].value;const auto prior=*swaps[i].slot;*swaps[i].slot=v;v=prior;}
  for(unsigned i=0;i<n;++i)if(p.sound_mask&(1U<<swaps[i].line)){
   auto*slot=reinterpret_cast<uint64_t*>(reinterpret_cast<uint8_t*>(swaps[i].slot)+16);
   sounds[sound_count++]={slot,*slot};*slot=p.sound.address;
  }
  // The reference gives every flower line camera type 4. StartDialogLines
  // builds default rich structs, so its appended branch otherwise uses 0.
  // The original callee copies the queue; restore our borrowed input after it.
  if(flower)for(int i=0;i<header.count;++i){
   auto*slot=reinterpret_cast<uint8_t*>(header.data+uint64_t(i)*304+24);
   if(*slot!=4){cameras[camera_count++]={slot,*slot};*slot=4;}
  }
  in_flight=n;return (n||camera_count)?owner:0;
 }
 void end(uint64_t token){
  if(token!=owner||(!in_flight&&!camera_count)||thread!=GetCurrentThreadId()){unknown=true;return;}
  for(unsigned i=0;i<camera_count;++i)if(*cameras[i].slot!=4){unknown=true;return;}
  for(unsigned i=0;i<sound_count;++i)if(*sounds[i].slot!=profiles[swaps[0].profile].sound.address){unknown=true;return;}
  for(unsigned i=0;i<in_flight;++i){auto&s=swaps[i];auto&p=profiles[s.profile];
   if(std::memcmp(s.slot,&p.replacement[s.line],sizeof(TargetTextValue))){unknown=true;return;}}
  for(unsigned i=in_flight;i>0;--i){auto&s=swaps[i-1];auto&p=profiles[s.profile];auto&v=p.text[s.line].value;
   const auto prior=*s.slot;*s.slot=v;v=prior;++p.hits[s.line];s={};}
  in_flight=0;
  for(unsigned i=0;i<camera_count;++i){*cameras[i].slot=cameras[i].before;cameras[i]={};}camera_count=0;
  for(unsigned i=0;i<sound_count;++i){*sounds[i].slot=sounds[i].before;sounds[i]={};}sound_count=0;
 }
 static e33_blueprint_transform::Decision pre(void*context,uint64_t f,void*object,void*frame){
  __try{return {static_cast<Dispatcher*>(context)->begin(f,object,frame),false};}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->unknown=true;return {};}
 }
 static void post(void*context,uint64_t token){
  __try{static_cast<Dispatcher*>(context)->end(token);}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->unknown=true;}
 }
 bool close(){
  if(unknown||in_flight||camera_count||sound_count)return false;
  if(routing){if(!e33_blueprint_transform::detach(this)||!BlueprintDirectTrace::release_narrative(function.address))return false;routing=false;}
  TargetOwnedTextOps ops{base};
  for(auto&p:profiles){for(unsigned i=0;i<p.count;++i)if(release_owned_text(ops,p.text[i])!=OwnedTextResult::Ok)return false;p.count=0;p.lease=0;}
  owner=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(!valid(p)||unknown||in_flight||camera_count||sound_count){p.error=unknown?uncertain:rejected;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||std::memcmp(&gi,&p.gi,16)||std::memcmp(&function,&p.function,16)||std::memcmp(guid,p.guid,16)||
      !profiles[p.profile].count||std::memcmp(&profiles[p.profile].source,&p.source,16)||std::memcmp(&profiles[p.profile].sound,&p.sound,16)||profiles[p.profile].sound_mask!=p.sound_mask||profiles[p.profile].sound_lease!=p.sound_lease){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   for(unsigned i=0;i<profiles[p.profile].count;++i)p.hits[i]=profiles[p.profile].hits[i];p.state=2;return;
  }
  if(profiles[p.profile].count||!pool.owns_object(s,p.function_lease,p.function.address)||!pool.owns_object(s,p.gi_lease,p.gi.address)||!pool.owns_object(s,p.source_lease,p.source.address)||
     !pool.owns_object(s,p.text_cdo_lease,p.text_cdo.address)||!pool.owns_object(s,p.text_query_lease,p.text_query.address)||
     !call_identity(b,p.function)||!call_identity(b,p.gi)||!call_identity(b,p.source)||!call_is_class(b,p.source.address)||!schema(b,p.function.address)){
   p.error=rejected;return;}
  const auto source=p.source.address;
  if(p.sound_mask&&(!pool.owns_object(s,p.sound_lease,p.sound.address)||!call_identity(b,p.sound)||
     !e33_mesh::named(b,source,"BP_Dialogue_Jules_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Jules")||
     !e33_mesh::named(b,p.sound.address,"VO_CHAR_Noah_Breath_Out_Low_07","/Game/Audio/WAV/VO/Characters/Gustave/Breath/VO_CHAR_Noah_Breath_Out_Low_07")||
     !e33_mesh::named(b,local_read<uint64_t>(p.sound.address+16),"SoundWave","/Script/Engine"))){p.error=rejected;return;}
  if(!e33_mesh::named(b,source,"BP_Dialogue_Gardens_GustaveFlower_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Gardens_GustaveFlower")&&
     !e33_mesh::named(b,source,"BP_Dialogue_Jules_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Jules")){p.error=rejected;return;}
  e33_engine_profile_call::TargetOps query_check{b,call_identity(b,p.text_query),call_identity(b,p.text_cdo),key_profile(),nullptr};
  if(!query_check.identities()||!query_check.exact_profile()||!query_check.recipient_derives()||!e33_mesh::named(b,p.text_cdo.address,"Default__KismetTextLibrary","/Script/Engine")){p.error=rejected;return;}
  if(owner&&(owner!=p.owner||session!=s||std::memcmp(&function,&p.function,16)||std::memcmp(&gi,&p.gi,16)||std::memcmp(&text_cdo,&p.text_cdo,16)||std::memcmp(&text_query,&p.text_query,16)||std::memcmp(guid,p.guid,16))){p.error=rejected;return;}
  base=b;session=s;owner=p.owner;function=p.function;gi=p.gi;function_lease=p.function_lease;gi_lease=p.gi_lease;std::memcpy(guid,p.guid,16);thread=GetCurrentThreadId();
  text_cdo=p.text_cdo;text_query=p.text_query;text_cdo_lease=p.text_cdo_lease;text_query_lease=p.text_query_lease;
  if(!bound()){p.error=rejected;return;}
  auto&out=profiles[p.profile];out.source=p.source;out.lease=p.source_lease;out.count=p.count;
  out.sound=p.sound;out.sound_lease=p.sound_lease;out.sound_mask=p.sound_mask;
  TargetOwnedTextOps ops{b};
  for(unsigned i=0;i<p.count;++i){const auto&t=p.texts[i];
   for(unsigned j=0;j<i;++j)if(out.lengths[j]==t.before_count&&!std::memcmp(out.before[j],p.units+t.before_start,t.before_count*2)){p.error=rejected;return;}
   out.lengths[i]=t.before_count;std::memcpy(out.before[i],p.units+t.before_start,t.before_count*2);out.hits[i]=0;
   if(create_owned_text(ops,out.text[i],p.units+t.after_start,t.after_count)!=OwnedTextResult::Ok){unknown=true;p.error=uncertain;return;}
   out.replacement[i]=out.text[i].value;
  }
  if(!routing){
   if(!e33_blueprint_transform::attach(this,function.address,pre,post)){p.error=rejected;return;}
   if(!BlueprintDirectTrace::retain_narrative(b,function.address)){e33_blueprint_transform::detach(this);p.error=rejected;return;}routing=true;
  }
  p.state=1;
 }
};
}
