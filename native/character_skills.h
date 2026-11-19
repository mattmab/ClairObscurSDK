#pragma once
#include "character_skill_schema.h"
#include "narrative_route_inputs.h"
#include "character_skill_rules.h"
#include "story_skill_target_array.h"
#include "story_skill_install.h"
#include "character_meter_init.h"
#include "retired_world_target.h"
#include "target_owned_text.h"
#include <cwchar>
namespace e33_character_skills {
constexpr uint32_t operation=259,rejected=4280,uncertain=4281;
 constexpr unsigned diagnostics_size=124;
#pragma pack(push,1)
struct Packet{uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[input_count]{};uint64_t leases[input_count]{};uint32_t guid[4]{},mode=0;uint8_t diagnostics[124]{};e33_character_skill_config::Profile profile{};uint8_t tail[20984-24-input_count*24-20-124-16276]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Character skill owner packet");
struct Dispatcher {
 uint64_t base=0,session=0,owner=0;DWORD thread=0;CallIdentity ids[input_count]{};uint64_t leases[input_count]{};uint32_t guid[4]{};
 bool unknown=false;unsigned hook_count=0,routing_count=0,depth=0;uint64_t hooks[22]{};unsigned route_inputs[22]{};
 e33_character_skill_config::Profile profile{};Rule rules[9]{};
 OwnedTextStorage empty_text;inline static Dispatcher*live=nullptr;
 struct Temporary{CallIdentity id{};uint64_t token=0;};Temporary temporaries[288]{};
 e33_skill_targets::Frame target_frames[8]{};
 void*pool_pointer=nullptr;bool(*retain)(Dispatcher*,Temporary&,uint64_t)=nullptr;bool(*release)(Dispatcher*,Temporary&)=nullptr;
 struct Cast{CallIdentity script{};bool healed=false;};Cast casts[64]{};unsigned cast_next=0;
 uint32_t executed[9]{},effects[9]{},damages=0,buffs=0,heals=0,meter_hits=0,meter_procs=0,stage=0;double last_factor=0.,last_bonus=0.;
 uint32_t meter_starts=0,meter_initialized=0,meter_forwarded=0;
 struct MeterCall{CallIdentity component{};e33_character_meter_init::Journal journal;};MeterCall meter_calls[8]{};
 e33_retired_world::Snapshot meter_world{};
 bool active()const{return owner||hook_count||routing_count||empty_text.state!=OwnedTextState::Empty;}
 bool protects(uint64_t t)const{for(auto lease:leases)if(active()&&lease==t)return true;for(const auto&v:temporaries)if(v.token==t&&t)return true;return false;}
 bool bound()const{e33_story_action::Dispatcher p;p.base=base;p.gi=ids[gi];std::memcpy(p.guid,guid,16);return thread==GetCurrentThreadId()&&p.bound();}
 bool is(uint64_t object,unsigned cls)const{return object&&call_capture(base,object).address&&call_derives(base,local_read<uint64_t>(object+16),ids[cls].address);}
 bool owned_character(uint64_t object)const{return is(object,character_class)&&zone_ref(base,local_read<uint64_t>(local_read<uint64_t>(object+32)+32),"OwningGameInstance")==ids[gi].address;}
 void dispatch(uint64_t receiver,unsigned fn,void*args){
  if(!receiver||!call_capture(base,receiver).address)throw uint32_t(4282);
  const auto pe=local_read<uint64_t>(local_read<uint64_t>(receiver)+0x268);
  if(pe!=base+0x1393330&&pe!=base+0x332bb90)throw uint32_t(4282);
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(receiver),reinterpret_cast<void*>(ids[fn].address),args);
 }
 template<class T>static void put(uint8_t*buffer,unsigned offset,const T&value){std::memcpy(buffer+offset,&value,sizeof(value));}
 template<class T>T output(uint64_t object,unsigned fn){alignas(16)uint8_t args[4096]{};dispatch(object,fn,args);T result{};std::memcpy(&result,args,sizeof(result));return result;}
 Temporary&hold(uint64_t value){for(auto&v:temporaries)if(!v.token&&!v.id.address){if(!retain(this,v,value))throw uint32_t(4283);return v;}throw uint32_t(4283);}
 void drop(Temporary&v){if(!release(this,v))throw uint32_t(4283);}
 Cast&cast(uint64_t script,bool begin){
  const auto id=call_capture(base,script);if(!id.address)throw uint32_t(4282);
  for(auto&c:casts)if(c.script.address==id.address&&c.script.index==id.index&&c.script.serial==id.serial){if(begin)c.healed=false;return c;}
  auto&c=casts[cast_next++%64];c={id,false};return c;
 }
 TargetStringValue reason(unsigned index)const{const auto*value=rules[index].debug_reason;const auto count=static_cast<int32_t>(std::wcslen(value)+1);return {reinterpret_cast<uint64_t>(value),count,count};}
 void recover_hp(uint64_t target_stats,uint64_t source,double fraction,unsigned skill){
  const double hp=output<double>(target_stats,maxhp);if(!std::isfinite(hp)||hp<0.||hp>1e12)throw uint32_t(4284);
  alignas(16)uint8_t args[4096]{};put(args,0,hp*fraction);put(args,8,source);args[16]=1;args[17]=1;
  put(args,24,reason(skill));
  dispatch(target_stats,recover,args);++heals;
 }
 void execute_skill(unsigned index,uint64_t script){
  const auto&r=rules[index];cast(script,true);alignas(16)uint8_t args[4096]{};
  put(args,0,ids[r.sequence].address);args[8]=r.look;args[9]=r.snap;args[10]=r.dash_in;args[11]=r.dash_back;
  put(args,16,r.distance);std::memcpy(args+40,&empty_text.value,16);put(args,56,r.initiative);args[64]=r.camera;
  stage=100+index;dispatch(script,standard,args);
  if(std::memcmp(args+40,&empty_text.value,16))throw uint32_t(4284);
  ++executed[index];stage=0;
 }
 void action_effect(unsigned index,uint64_t script,uint64_t character){
  const auto stats=zone_ref(base,character,"AC_jRPG_CharacterStats");if(!is(stats,stats_class))throw uint32_t(4282);
  // Retain the source-selected stats before callbacks can replace the roster.
  // A configured target query includes the skill's authored target overrides.
  Temporary*selected[32]{};uint32_t selected_count=0;
  struct TargetOps {
   Dispatcher*self;uint64_t script;Temporary**selected;uint32_t&selected_count;
   bool context()const{return !self->unknown&&self->bound();}
   void dispatch(void*args){self->dispatch(script,targets,args);}
   void count(uint32_t n){selected_count=n;}
   bool retain(uint64_t at,unsigned i){const auto actor=local_read<uint64_t>(at);const auto stats_value=zone_ref(self->base,actor,"AC_jRPG_CharacterStats");if(!self->is(stats_value,stats_class))return false;selected[i]=&self->hold(stats_value);return true;}
   void free_array(uint64_t data)const{reinterpret_cast<void(__fastcall*)(void*)>(self->base+0x107c7d0)(reinterpret_cast<void*>(data));}
  }target_ops{this,script,selected,selected_count};
  if(profile.skills[index].flags&32){if(!depth||depth>8||!target_frames[depth-1].query(target_ops))throw uint32_t(4284);}
  else{const auto list=local_read<e33_skill_targets::Array>(stats+432);if(list.count<0||list.count>32||list.capacity<list.count||list.capacity>4096||(!list.data&&list.count))throw uint32_t(4284);selected_count=uint32_t(list.count);for(uint32_t i=0;i<selected_count;++i)if(!target_ops.retain(list.data+uint64_t(i)*8,i))throw uint32_t(4282);}
  alignas(16)uint8_t combo_args[4096]{};dispatch(character,combo,combo_args);
  const int success=local_read<int32_t>(reinterpret_cast<uint64_t>(combo_args+4)),fail=local_read<int32_t>(reinterpret_cast<uint64_t>(combo_args+8)),perfect=local_read<int32_t>(reinterpret_cast<uint64_t>(combo_args+12));
  if(!e33_character_skill_rules::qte_counts(success,fail,perfect))throw uint32_t(4284);
  const bool final=output<uint8_t>(character,last)!=0;const uint8_t weapon=output<uint8_t>(stats,element);
  bool charged=false;if(profile.skills[index].flags&64){const auto state=zone_ref(base,script,"SkillState");if(!is(state,state_class))throw uint32_t(4282);charged=local_read<uint8_t>(state+48)!=0;}
  const auto effect=e33_character_skill_rules::effect(profile.skills[index],success,perfect,final,charged,weapon);auto&current_cast=cast(script,false);
  for(uint32_t i=0;i<selected_count;++i){
   if(!selected[i]||!call_identity(base,selected[i]->id))throw uint32_t(4282);const auto target_stats=selected[i]->id.address;stage=200+index;
   if(profile.skills[index].flags&256){recover_hp(target_stats,target_stats,profile.skills[index].recovery_fraction,index);if(!(profile.skills[index].flags&1024))continue;const auto component=zone_ref(base,stats,"BattleBuffComponent");if(!is(component,buff_component_class))throw uint32_t(4282);alignas(16)uint8_t args[4096]{};args[0]=uint8_t(profile.skills[index].cleanse_kind);dispatch(component,cleanse,args);continue;}
   alignas(16)uint8_t build[4096]{};put(build,0,target_stats);build[8]=effect.element;put(build,16,effect.damage);put(build,24,effect.breaking);
   // IBattleDamageSource is Blueprint-only on CharacterBattleStats: its object
   // half carries the interface; there is no native interface subobject.
   put(build,32,stats);build[48]=uint8_t(profile.skills[index].damage_reason);put(build,56,reason(index));put(build,72,character);
   dispatch(ids[helpers].address,make,build);const auto builder=local_read<uint64_t>(reinterpret_cast<uint64_t>(build+80));auto&temporary=hold(builder);
   alignas(16)uint8_t dealt[4096]{};dispatch(builder,deal,dealt);const bool hit=dealt[0]!=0;drop(temporary);++damages;last_factor=effect.damage;last_bonus=1.+profile.skills[index].qte_bonus*double(success+perfect);
   if(!hit)continue;
   if(effect.buff>=0){alignas(16)uint8_t args[4096]{};put(args,0,ids[buff_burn+unsigned(effect.buff)].address);put(args,8,target_stats);put(args,16,effect.duration);args[32]=uint8_t(profile.skills[index].buff_reason);dispatch(script,buff,args);++buffs;}
   if(effect.heal&&!current_cast.healed){const double hp=output<double>(target_stats,percent);if(!std::isfinite(hp)||hp<0.||hp>1.)throw uint32_t(4284);if(hp<profile.skills[index].heal_threshold){recover_hp(stats,stats,profile.skills[index].heal_fraction,index);current_cast.healed=true;}}
  }
  for(uint32_t i=0;i<selected_count;++i)drop(*selected[i]);
  ++effects[index];stage=0;
 }
 void update_meter(uint64_t object,int value){
  put(reinterpret_cast<uint8_t*>(object),352,value);alignas(16)uint8_t args[4096]{};put(args,0,value);dispatch(object,stack,args);
  const auto component=zone_ref(base,object,"MomentumUIComponent");if(component){if(!is(component,ui_class))throw uint32_t(4282);dispatch(component,ui,args);}
 }
 void reset_meter(uint64_t object){const int64_t previous=-1,zero=0;put(reinterpret_cast<uint8_t*>(object),360,previous);put(reinterpret_cast<uint8_t*>(object),368,zero);update_meter(object,int(profile.reset));}
 int random_value(int low,int high){alignas(16)uint8_t args[4096]{};put(args,0,low);put(args,4,high);dispatch(ids[math].address,random,args);const auto v=local_read<int32_t>(reinterpret_cast<uint64_t>(args+8));if(v<low||v>high)throw uint32_t(4284);return v;}
 void meter_damage(uint64_t object,uint64_t damage){
  if(!is(damage,damages_class))throw uint32_t(4282);const auto own=zone_ref(base,object,"TargetCharacterStats"),source=zone_ref(base,damage,"SourceCharacter");
  const double amount=local_read<double>(damage+736);if(!std::isfinite(amount))throw uint32_t(4284);
  const auto frame=local_read<uint64_t>(base+0x9272d10);const auto previous=local_read<int64_t>(object+360);
  if(!e33_character_skill_rules::qualifies_meter(profile,source==own,local_read<uint8_t>(damage+773),amount,frame,previous))return;
  const int old=local_read<int32_t>(object+352);if(old<0||old>int(profile.cap))throw uint32_t(4284);
  put(reinterpret_cast<uint8_t*>(object),360,frame);const int count=e33_character_skill_rules::next_meter(profile,old);update_meter(object,count);++meter_hits;
  if(random_value(1,int(profile.cap))>count)return;const auto target_stats=zone_ref(base,damage,"TargetCharacter");if(!target_stats)return;if(!is(target_stats,stats_class))throw uint32_t(4282);
  unsigned options[7]{},option_count=0;for(unsigned i=0;i<7;++i)if(profile.buff_mask&(1U<<i))options[option_count++]=i;const unsigned selected=options[random_value(0,int(option_count)-1)];alignas(16)uint8_t create[4096]{};put(create,0,ids[buff_burn+unsigned(selected)].address);put(create,8,target_stats);dispatch(ids[gameplay].address,spawn,create);
  const auto instance=local_read<uint64_t>(reinterpret_cast<uint64_t>(create+16));if(!instance)return;auto&temporary=hold(instance);
  alignas(16)uint8_t args[4096]{};put(args,0,instance);args[8]=4;put(args,16,source);dispatch(target_stats,activate,args);const bool activated=args[24]!=0;drop(temporary);
  if(activated){update_meter(object,int(profile.reset));++meter_procs;}
 }
 void set_meter_reference(uint64_t object,const char*name,unsigned offset,uint64_t value,uint64_t expected){
  if(local_read<uint64_t>(object+offset)!=expected)throw uint32_t(4288);
  uint64_t property_name=0;if(!e33_blueprint_names::resolve(base,name,property_name))throw uint32_t(4288);
  alignas(16)uint8_t args[4096]{};put(args,0,object);put(args,8,property_name);put(args,16,value);
  dispatch(ids[system].address,set_object,args);
  if(local_read<uint64_t>(object+offset)!=value)throw uint32_t(4288);
 }
 void meter_initialize(uint64_t object,uint64_t damage,bool battle){
  const auto character=battle?object:local_read<uint64_t>(object+32);
  const auto component=battle?zone_ref(base,character,"MomentumComponent"):object;
  const auto stats=zone_ref(base,character,"AC_jRPG_CharacterStats");
  if(!depth||depth>8||!owned_character(character)||!is(component,ui_class)||!is(stats,stats_class)||
     local_read<uint64_t>(component+32)!=character||local_read<uint64_t>(stats+32)!=character||
     zone_ref(base,character,"MomentumComponent")!=component)throw uint32_t(4288);
  e33_retired_world::TargetOps proof{base};
  if(!proof.current_binding(meter_world.engine,meter_world.viewport,meter_world.world)&&!proof.observe(meter_world))throw uint32_t(4288);
  auto outer=character;unsigned walked=0;for(;outer&&outer!=meter_world.world.address&&walked<32;++walked)outer=local_read<uint64_t>(outer+32);
  if(outer!=meter_world.world.address)throw uint32_t(4288);
  // Activation may invoke callbacks. A second initialization for this same
  // component cannot race publication or create another unjournaled state.
  for(const auto&pending:meter_calls)if(pending.component.address==component)throw uint32_t(4288);
  auto&pending=meter_calls[depth-1];if(pending.component.address)throw uint32_t(4288);
  pending.component=call_capture(base,component);
  auto&actor_hold=hold(character);auto&component_hold=hold(component);auto&stats_hold=hold(stats);
  Temporary*damage_hold=nullptr;if(!battle){if(!is(damage,damages_class))throw uint32_t(4288);damage_hold=&hold(damage);}
  struct Ops {
   Dispatcher*self;Temporary&actor,&component,&stats;Temporary*damage;e33_retired_world::Snapshot world;Temporary*state=nullptr,*previous_state=nullptr;uint64_t previous=0;
   bool context()const{return !self->unknown&&self->bound()&&call_identity(self->base,actor.id)&&
    call_identity(self->base,component.id)&&call_identity(self->base,stats.id)&&
    (!state||(call_identity(self->base,state->id)&&!(local_read<uint32_t>(state->id.address+8)&0x40018030U)))&&
    (!previous_state||call_identity(self->base,previous_state->id))&&
    (!damage||(call_identity(self->base,damage->id)&&!(local_read<uint32_t>(damage->id.address+8)&0x40018030U)))&&
    !(local_read<uint32_t>(actor.id.address+8)&0x40018030U)&&!(local_read<uint32_t>(component.id.address+8)&0x40018030U)&&
    !(local_read<uint32_t>(stats.id.address+8)&0x40018030U)&&
    e33_retired_world::TargetOps{self->base}.current_binding(world.engine,world.viewport,world.world)&&
    self->owned_character(actor.id.address)&&local_read<uint64_t>(component.id.address+32)==actor.id.address&&
    local_read<uint64_t>(stats.id.address+32)==actor.id.address&&
    zone_ref(self->base,actor.id.address,"MomentumComponent")==component.id.address&&
    zone_ref(self->base,actor.id.address,"AC_jRPG_CharacterStats")==stats.id.address;}
   void parent(){alignas(16)uint8_t args[4096]{};self->stage=300;self->dispatch(actor.id.address,parent_battle_start,args);++self->meter_starts;}
   bool existing(){
    const auto value=zone_ref(self->base,component.id.address,"MomentumState");
    if(!value||!call_capture(self->base,value).address||(local_read<uint32_t>(value+8)&0x30))return false;
    if(!self->is(value,momentum_class)||zone_ref(self->base,value,"TargetCharacterStats")!=stats.id.address||
       zone_ref(self->base,value,"MomentumUIComponent")!=component.id.address)throw uint32_t(4288);
    state=&self->hold(value);return true;
   }
   bool spawn(){
    previous=zone_ref(self->base,component.id.address,"MomentumState");
    // Retain a valid old state across ActivateBuff callbacks. Its expected
    // pointer cannot be recycled before the checked replacement is published.
    if(previous&&call_capture(self->base,previous).address&&!(local_read<uint32_t>(previous+8)&0x40018030U))previous_state=&self->hold(previous);
    self->stage=301;
    alignas(16)uint8_t args[4096]{};self->put(args,0,self->ids[momentum_class].address);self->put(args,8,stats.id.address);
    self->dispatch(self->ids[gameplay].address,e33_character_skills::spawn,args);
    const auto value=local_read<uint64_t>(reinterpret_cast<uint64_t>(args+16));if(!value)return false;
    state=&self->hold(value);
    if(local_read<uint64_t>(value+16)!=self->ids[momentum_class].address||local_read<uint64_t>(value+32)!=stats.id.address)throw uint32_t(4288);
    return true;
   }
   void link_ui(){self->stage=302;self->set_meter_reference(state->id.address,"MomentumUIComponent",376,component.id.address,0);}
   bool activate(){
    self->stage=303;alignas(16)uint8_t args[4096]{};self->put(args,0,state->id.address);args[8]=4;self->put(args,16,stats.id.address);
    self->dispatch(stats.id.address,e33_character_skills::activate,args);
    if(args[24]>1)throw uint32_t(4288);
    if(args[24]&&zone_ref(self->base,state->id.address,"TargetCharacterStats")!=stats.id.address)throw uint32_t(4288);
    return args[24]!=0;
   }
   void link_state(){self->stage=304;self->set_meter_reference(component.id.address,"MomentumState",208,state->id.address,previous);++self->meter_initialized;}
   void reset_ui(){self->stage=305;alignas(16)uint8_t args[4096]{};self->dispatch(component.id.address,ui,args);}
   void forward(){self->stage=306;self->meter_damage(state->id.address,damage->id.address);++self->meter_forwarded;}
  }ops{this,actor_hold,component_hold,stats_hold,damage_hold,meter_world};
  e33_character_meter_init::run(pending.journal,ops,battle?e33_character_meter_init::Origin::BattleStart:e33_character_meter_init::Origin::Damage);
  if(ops.state)drop(*ops.state);if(ops.previous_state)drop(*ops.previous_state);if(damage_hold)drop(*damage_hold);drop(stats_hold);drop(component_hold);drop(actor_hold);
  pending={};stage=0;
 }
 e33_blueprint_transform::Decision begin(uint64_t fn,void*object,void*frame){
  const auto obj=reinterpret_cast<uint64_t>(object),f=reinterpret_cast<uint64_t>(frame);if(!owner||!f||local_read<uint64_t>(f+0x10)!=fn||local_read<uint64_t>(f+0x18)!=obj||!bound())return {};
  bool selected=false;unsigned index=9;bool execution=false;
  for(unsigned i=0;i<profile.count;++i)if(fn==ids[rules[i].effect].address||fn==ids[rules[i].execute].address){if(local_read<uint64_t>(obj+16)!=ids[rules[i].script].address)return {};index=i;execution=fn==ids[rules[i].execute].address;selected=true;break;}
  if(index<profile.count){const auto character=zone_ref(base,obj,"CurrentCharacter");if(!owned_character(character))return {};if(unknown)return {0,true};if(depth>=8){unknown=true;return {0,true};}++depth;
   try{if(execution)execute_skill(index,obj);else action_effect(index,obj,character);}catch(...){unknown=true;}--depth;return {0,true};}
  if(profile.meter_enabled&&(fn==ids[meter].address||fn==ids[reset].address)){
   if(local_read<uint64_t>(obj+16)!=ids[momentum_class].address)return {};const auto stats=zone_ref(base,obj,"TargetCharacterStats");if(!is(stats,stats_class)||!owned_character(local_read<uint64_t>(stats+32)))return {};
   if(unknown)return {0,true};if(depth>=8){unknown=true;return {0,true};}++depth;
   try{if(fn==ids[reset].address)reset_meter(obj);else{const auto locals=local_read<uint64_t>(f+0x28);if(!locals)throw uint32_t(4282);meter_damage(obj,local_read<uint64_t>(locals));}}catch(...){unknown=true;}--depth;return {0,true};
  }
  if(fn==ids[battle_start].address||fn==ids[component_damage].address){
   const bool battle=fn==ids[battle_start].address;
   if(battle?!owned_character(obj):(!is(obj,ui_class)||!owned_character(local_read<uint64_t>(obj+32))))return {};
   if(unknown)return {0,true};if(depth>=8){unknown=true;return {0,true};}++depth;
   try{const auto locals=battle?0:local_read<uint64_t>(f+0x28);if(!battle&&!locals)throw uint32_t(4288);
    meter_initialize(obj,battle?0:local_read<uint64_t>(locals),battle);}catch(...){unknown=true;}--depth;return {0,true};
  }
  (void)selected;return {};
 }
 static e33_blueprint_transform::Decision pre(void*ctx,uint64_t fn,void*object,void*frame){auto*self=static_cast<Dispatcher*>(ctx);__try{return self->begin(fn,object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;self->depth=0;return {0,true};}}
 static void post(void*,uint64_t){}
 static void __fastcall wrapper(void*object,void*frame,void*result){auto*self=live;if(!self)return;const auto fn=local_read<uint64_t>(reinterpret_cast<uint64_t>(frame)+0x10);const auto d=pre(self,fn,object,frame);if(!d.skip)reinterpret_cast<e33_trace::Entry>(self->base+0x13937a0)(object,frame,result);}
 bool path(unsigned i)const{
  if(i==gi)return true;std::string value(e33_character_skill_config::path(profile,i,input_specs[i].path));const auto dot=value.find('.');if(dot==std::string::npos)return false;const auto colon=value.find(':',dot);
  const auto package=value.substr(0,dot),name=value.substr(dot+1,colon==std::string::npos?std::string::npos:colon-dot-1);
  if(colon==std::string::npos)return e33_mesh::named(base,ids[i].address,name.c_str(),package.c_str());
  return exact_name(base,ids[i].address+24,value.substr(colon+1).c_str())&&e33_mesh::named(base,local_read<uint64_t>(ids[i].address+32),name.c_str(),package.c_str());
 }
 bool property(const PropertySpec&prop)const{
  for(auto cls=ids[prop.index].address,n=uint64_t(0);cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40))
   if(picto_struct_field(base,cls,prop.name,prop.type,prop.offset,prop.size))return true;
  return false;
 }
 uint64_t object_property(unsigned owner_index,const char*name,unsigned offset,uint64_t flags)const{
  for(auto cls=ids[owner_index].address,n=uint64_t(0);cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40)){
   const auto field=picto_struct_field(base,cls,name,"ObjectProperty",offset,8);
   if(field)return local_read<int32_t>(field+0x30)==1&&local_read<uint64_t>(field+0x38)==flags?local_read<uint64_t>(field+0x70):0;
  }
  return 0;
 }
 bool meter_properties()const{
  return object_property(character_class,"MomentumComponent",5656,2251885713555972ULL)==ids[ui_class].address&&
   object_property(character_class,"AC_jRPG_CharacterStats",2288,2251885713555972ULL)==ids[stats_class].address&&
   object_property(ui_class,"MomentumState",208,2251868533162496ULL)==ids[buff_class].address&&
   e33_mesh::named(base,object_property(momentum_class,"MomentumUIComponent",376,2251868533162496ULL),"ActorComponent","/Script/Engine")&&
   object_property(component_damage,"BattleDamage",0,2251868533686932ULL)==ids[damages_class].address;
 }
 bool close(){
  if(unknown||depth)return false;
  for(const auto&frame:target_frames)if(!frame.available())return false;
  for(const auto&pending:meter_calls)if(pending.component.address)return false;
  while(hook_count){const auto fn=hooks[hook_count-1];if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(fn+0xd8),reinterpret_cast<void*>(base+0x13937a0),reinterpret_cast<void*>(wrapper))!=reinterpret_cast<void*>(wrapper)){unknown=true;return false;}--hook_count;}
  e33_blueprint_transform::detach(this);
  while(routing_count){if(!BlueprintDirectTrace::release_narrative(ids[route_inputs[routing_count-1]].address))return false;--routing_count;}
  for(auto&temporary:temporaries)if(temporary.token&&!release(this,temporary))return false;
  TargetOwnedTextOps ops{base};if(release_owned_text(ops,empty_text)!=OwnedTextResult::Ok)return false;
  owner=0;meter_world={};live=nullptr;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  auto reject=[&](uint32_t error,uint32_t diagnostic){p.error=error;put(p.diagnostics,92,diagnostic);};
  if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.guid[0]!=0xe33c5701U||!e33_character_skill_config::valid(p.profile)){reject(rejected,1000);return;}for(auto byte:p.diagnostics)if(byte){reject(rejected,1001);return;}for(auto byte:p.tail)if(byte){reject(rejected,1002);return;}
  if(p.mode){if(owner!=p.owner||session!=s||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(guid,p.guid,16)||std::memcmp(&profile,&p.profile,sizeof(profile))){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   std::memcpy(p.diagnostics,executed,36);std::memcpy(p.diagnostics+36,effects,36);put(p.diagnostics,72,damages);put(p.diagnostics,76,buffs);put(p.diagnostics,80,heals);put(p.diagnostics,84,meter_hits);put(p.diagnostics,88,meter_procs);put(p.diagnostics,92,stage);put(p.diagnostics,96,last_factor);put(p.diagnostics,104,last_bonus);
   put(p.diagnostics,112,meter_starts);put(p.diagnostics,116,meter_initialized);put(p.diagnostics,120,meter_forwarded);
   if(unknown){p.error=uncertain;return;}p.state=2;return;
  }
  if(active()){reject(rejected,1003);return;}for(unsigned i=0;i<input_count;++i){if(e33_character_skill_config::active(i,p.profile.count,p.profile.meter_enabled)){if(!call_identity(b,p.ids[i])||!p.leases[i]||!pool.owns_object(s,p.leases[i],p.ids[i].address)){reject(rejected,1100+i);return;}}else{const CallIdentity empty{};if(std::memcmp(&p.ids[i],&empty,sizeof(empty))||p.leases[i]){reject(rejected,1200+i);return;}}}
  base=b;session=s;profile=p.profile;thread=GetCurrentThreadId();std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,16);
  for(unsigned i=0;i<profile.count;++i){const auto&r=profile.skills[i];rules[i]={38+4*i,39+4*i,40+4*i,41+4*i,bool(r.flags&1),bool(r.flags&2),bool(r.flags&4),bool(r.flags&8),r.distance,r.initiative,bool(r.flags&16),reinterpret_cast<const wchar_t*>(r.debug_reason)};}
  if(!bound()){reject(rejected,1300);return;}if(!picto_frame_source(base)){reject(rejected,1301);return;}for(unsigned i=1;i<input_count;++i)if(e33_character_skill_config::active(i,profile.count,profile.meter_enabled)&&!path(i)){reject(4285,1400+i);return;}
  for(const auto&fn:functions){if(!e33_character_skill_config::active(fn.index,profile.count,profile.meter_enabled))continue;const auto f=ids[fn.index].address;if(local_read<uint32_t>(f+0xb0)!=fn.flags||local_read<uint16_t>(f+0xb6)!=fn.size||local_read<uint64_t>(f+0xd8)!=base+fn.entry){reject(4286,1500+fn.index);return;}}
  for(const auto&prop:properties)if(e33_character_skill_config::active(prop.index,profile.count,profile.meter_enabled)&&!property(prop)){reject(4287,1600+prop.index);return;}if(profile.meter_enabled&&!meter_properties()){reject(4287,1700);return;}
  const auto array=picto_struct_field(base,ids[targets].address,"TargetedCharacters","ArrayProperty",0,16);
  const auto inner=array?local_read<uint64_t>(array+0x78):0;
  if(!array||local_read<uint64_t>(array)!=base+0x6e0de80||local_read<uint64_t>(array+0x38)!=384||(local_read<uint8_t>(array+0x70)&1)||
   !inner||local_read<uint64_t>(inner)!=base+0x6e11d38||local_read<uint64_t>(inner+16)!=array||
   local_read<int32_t>(inner+0x34)!=8||local_read<uint64_t>(inner+0x70)!=local_read<uint64_t>(ids[combo].address+32)){reject(4287,1701);return;}
  pool_pointer=&pool;
  retain=[](Dispatcher*self,Temporary&tmp,uint64_t object){tmp.id=call_capture(self->base,object);if(!tmp.id.address)return false;TargetStrongReferenceOps ops{self->base,tmp.id};return static_cast<Pool*>(self->pool_pointer)->acquire(ops,self->session,object,tmp.token)==StrongLeaseResult::Ok&&stabilize_retained_identity(ops,tmp.id);};
  release=[](Dispatcher*self,Temporary&tmp){TargetStrongReferenceOps ops{self->base,{-1,0,0}};if(tmp.token&&static_cast<Pool*>(self->pool_pointer)->release(ops,self->session,tmp.token)!=StrongLeaseResult::Ok)return false;tmp={};return true;};
  owner=p.owner; // Correlate cleanup before text allocation or the first hook.
  TargetOwnedTextOps text_ops{base};const uint16_t empty[1]{};if(create_owned_text(text_ops,empty_text,empty,1)!=OwnedTextResult::Ok){reject(e33_skill_install::rollback(*this,rejected,uncertain),1800);return;}
  HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(wrapper),&pinned)){reject(e33_skill_install::rollback(*this,rejected,uncertain),1801);return;}
  unsigned hook_targets[22]{},target_count=0;for(unsigned i=0;i<profile.count;++i){hook_targets[target_count++]=rules[i].effect;hook_targets[target_count++]=rules[i].execute;}if(profile.meter_enabled){hook_targets[target_count++]=meter;hook_targets[target_count++]=reset;hook_targets[target_count++]=battle_start;hook_targets[target_count++]=component_damage;}
  unsigned route_targets[22]{},route_count=0;
  if(!e33_narrative_routes::unique_inputs(hook_targets,target_count,route_targets,route_count,[&](unsigned input){return local_read<uint64_t>(ids[input].address+24);})){reject(e33_skill_install::rollback(*this,rejected,uncertain),1802);return;}
  for(unsigned i=0;i<route_count;++i){const auto input=route_targets[i];if(!BlueprintDirectTrace::retain_narrative(base,ids[input].address)){reject(e33_skill_install::rollback(*this,rejected,uncertain),1900+input);return;}route_inputs[routing_count++]=input;}
  live=this;for(unsigned i=0;i<target_count;++i){const auto input=hook_targets[i];const auto fn=ids[input].address;if(!e33_blueprint_transform::attach(this,fn,pre,post)){reject(e33_skill_install::rollback(*this,rejected,uncertain),2000+input);return;}if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(fn+0xd8),reinterpret_cast<void*>(wrapper),reinterpret_cast<void*>(base+0x13937a0))!=reinterpret_cast<void*>(base+0x13937a0)){reject(e33_skill_install::rollback(*this,rejected,uncertain),2100+input);return;}hooks[hook_count++]=fn;}
  owner=p.owner;std::memset(executed,0,sizeof(executed));std::memset(effects,0,sizeof(effects));damages=buffs=heals=meter_hits=meter_procs=stage=0;meter_starts=meter_initialized=meter_forwarded=0;meter_world={};last_factor=last_bonus=0.;cast_next=0;for(auto&c:casts)c={};for(auto&pending:meter_calls)pending={};p.state=1;
 }
};
}
