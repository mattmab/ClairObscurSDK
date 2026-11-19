#pragma once
#include "story_ambient_overlay_packet.h"
#include "target_story_inworld.h"
#include "target_story_action.h"
namespace e33_story_ambient_overlay {
struct Entry {
 uint64_t owner=0,session=0,base=0,asset_lease=0,gi_lease=0,world_lease=0;
 CallIdentity asset{},gi{},world{},system{},query{};uint32_t guid[4]{};TargetStringValue original{};
 e33_story_inworld::Frame frame;bool attached=false;
 bool active()const{return owner!=0;}
 bool bound()const{e33_story_action::Dispatcher p;p.base=base;p.gi=gi;std::memcpy(p.guid,guid,16);return p.bound();}
 bool detach(){
  if(!attached)return true;
  e33_story_inworld::Dispatcher helper;const auto slot=call_identity(base,asset)?helper.lines_slot(base,asset.address):0;
  if(!slot||!frame.matches(local_read<TargetStringValue>(slot))){frame.unknown=true;return false;}
  *reinterpret_cast<TargetStringValue*>(slot)=original;attached=false;frame.attached=false;return true;
 }
 bool close(){
  if(frame.unknown||!detach())return false;
  // A world retirement is required before freeing a frame that an original
  // widget may still be reading. Explicit close in the same world defers.
  e33_retired_world::TargetOps proof{base};
  const auto retired=e33_retired_world::double_observe(proof,world);
  if(retired!=e33_retired_world::Result::Retired){
   if(retired!=e33_retired_world::Result::SameWorld||!call_identity(base,system)||!call_identity(base,query))return false;
   e33_story_inworld::Dispatcher player;player.asset=asset;player.system=system;player.world=world;
   e33_dialogue_text::Dispatcher helper;bool playing=false;
   if(!player.query_playing(base,query.address,helper,playing)||playing)return false;
  }
  TargetOwnedTextOps ops{base};if(!frame.cleanup(ops))return false;owner=0;return true;
 }
};
struct Dispatcher {
 Entry entries[16];bool unknown=false;
 bool active()const{for(const auto&e:entries)if(e.active())return true;return false;}
 bool protects(uint64_t token)const{for(const auto&e:entries)if(e.active()&&(token==e.asset_lease||token==e.gi_lease))return true;return false;}
 void poll(){for(auto&e:entries)if(e.active()&&e.attached&&!e.bound()&&!e.detach())unknown=true;}
 bool close(){bool ok=true;for(auto&e:entries)if(e.active()&&!e.close())ok=false;return ok;}
 bool source(uint64_t b,uint64_t object)const{
  static const char*const names[]={"DA_IWD_LuMaelleA","DA_IWD_LuMaelleB","DA_IWD_LuMaelleC","DA_IWD_LuMaelleD","DA_IWD_LuMaelleE","DA_IWD_LuMaelleG","DA_IWD_SophieA","DA_IWD_SophieB","DA_IWD_Corpses_1"};
  for(unsigned i=0;i<9;++i){char package[256]{};
   std::snprintf(package,sizeof(package),"/Game/Narrative/InWorldDialogue/Data/%s/%s",i==8?"SpringMeadows":"Lumiere",names[i]);
   if(i==8){
    // UE serializes DA_IWD_Corpses_1 as base DA_IWD_Corpses + Number=2.
    // Match the complete numbered display name and exact package; never
    // admit a prefix, a different suffix or an arbitrary dialogue asset.
    if(call_capture(b,object).address && e33_mesh::candidate_name(b,object+24,names[i]) &&
       e33_mesh::candidate_name(b,local_read<uint64_t>(object+32)+24,package))return true;
   }else if(e33_mesh::named(b,object,names[i],package))return true;
  }return false;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(!valid(p)||unknown){p.error=unknown?uncertain:rejected;return;}
  Entry*entry=nullptr;for(auto&e:entries)if(e.owner==p.owner){entry=&e;break;}
  if(p.mode){
   if(!entry||entry->session!=s||std::memcmp(&entry->asset,&p.asset,16)||std::memcmp(&entry->gi,&p.gi,16)||std::memcmp(&entry->world,&p.world,16)||
      std::memcmp(&entry->system,&p.system,16)||std::memcmp(&entry->query,&p.query,16)||std::memcmp(entry->guid,p.guid,16)){p.error=rejected;return;}
   if(p.mode==2){p.state=entry->close()?3U:0U;if(!p.state)p.error=entry->frame.unknown?uncertain:pending;return;}
   p.state=entry->attached?1U:2U;return;
  }
  if(entry){p.error=rejected;return;}
  for(auto&e:entries)if(!e.active()){entry=&e;break;}
  e33_story_inworld::Dispatcher helper;
  const auto a=call_identity(b,p.asset),g=call_identity(b,p.gi),w=call_identity(b,p.world);
  e33_dialogue_text::Dispatcher dialogue_helper;
  if(!entry||!a||!g||!w){p.state=101;p.error=rejected;return;}
  if(!source(b,a)){p.state=102;p.error=rejected;return;}
  if(!pool.owns_object(s,p.asset_lease,a)||!pool.owns_object(s,p.gi_lease,g)){p.state=103;p.error=rejected;return;}
  if(!call_identity(b,p.system)||!call_identity(b,p.query)){p.state=104;p.error=rejected;return;}
  if(dialogue_helper.world(b,p.system.address)!=w){p.state=105;p.error=rejected;return;}
  if(!helper.function(b,p.query.address,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent","IsPlayingSpecificInWorldDialogue",0x1c420000,9)||
     !helper.parameters(b,p.query.address,"InWorldDialogue","IsPlaying")){p.state=106;p.error=rejected;return;}
  if(zone_ref(b,w,"OwningGameInstance")!=g){p.state=107;p.error=rejected;return;}
  e33_retired_world::Snapshot now{};e33_retired_world::TargetOps proof{b};
  if(!proof.observe(now)||!e33_retired_world::same(now.world,p.world)){p.state=108;p.error=rejected;return;}
  for(const auto&e:entries)if(e.active()&&e.asset.address==a){p.state=109;p.error=rejected;return;}
  const auto slot=helper.lines_slot(b,a);const auto original_header=slot?local_read<TargetStringValue>(slot):TargetStringValue{};
  if(!slot||original_header.count!=int(p.expected_count)||original_header.count<0||original_header.capacity<original_header.count||original_header.capacity>128||(original_header.count&&(!original_header.data||(original_header.data&7)))){p.state=110;p.error=rejected;return;}
  entry->base=b;entry->session=s;entry->owner=p.owner;entry->asset=p.asset;entry->gi=p.gi;entry->world=p.world;
  entry->system=p.system;entry->query=p.query;
  entry->asset_lease=p.asset_lease;entry->gi_lease=p.gi_lease;entry->world_lease=p.world_lease;std::memcpy(entry->guid,p.guid,16);entry->original=original_header;
  if(!entry->bound()){entry->owner=0;p.error=rejected;return;}
  uint64_t names[16]{};
  for(unsigned i=0;i<p.count;++i){const auto&line=p.lines[i];
   if(!helper.object_kind(b,line.wave,"DialogueWave","/Script/Engine")||!helper.object_kind(b,line.sound,"SoundBase","/Script/Engine")||!helper.object_kind(b,line.table,"DataTable","/Script/Engine")||
      (line.row[0]&&std::strcmp(line.row,"None")&&!e33_blueprint_names::resolve(b,line.row,names[i]))){entry->owner=0;p.error=rejected;return;}
  }
  // This frame has the same 88-byte source ABI, but is not a private playback
  // request and must not call PlayInWorldDialogue or change any trigger state.
  auto&frame=entry->frame;frame.count=p.count;frame.prepared=true;TargetOwnedTextOps ops{b};
  for(unsigned i=0;i<p.count;++i){const auto&in=p.lines[i];auto&out=frame.lines[i];
   if(create_owned_text(ops,frame.owners[i],p.units+in.text_start,in.text_count)!=OwnedTextResult::Ok){frame.unknown=true;unknown=true;p.error=uncertain;return;}
   out.character=uint8_t(in.character);out.emotion=uint8_t(in.emotion);out.delete_delay=in.delete_delay;out.answer_delay=in.answer_delay;
   out.use_sound_duration=uint8_t(in.flags&1);out.portrait_right=uint8_t((in.flags>>1)&1);out.wave=in.wave.address;out.sound=in.sound.address;out.table=in.table.address;out.row=names[i];out.text=frame.owners[i].value;
  }
  frame.array={reinterpret_cast<uint64_t>(frame.lines),int(p.count),int(p.count)};
  *reinterpret_cast<TargetStringValue*>(slot)=frame.array;frame.attached=true;entry->attached=true;p.state=1;
 }
};
}
