#pragma once
#include "story_skill_install.h"
#include "battle_qte_timing.h"
// Configured native QTE windows, installed in the original declaration
// call before playback advances. Mutation callbacks never use the trace lock.
namespace e33_battle_qte {
constexpr uint32_t operation=256,rejected=4250,uncertain=4251;
#pragma pack(push,1)
struct Packet {uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[10]{};uint64_t leases[10]{};uint32_t guid[4]{},mode=0,injected=0;uint8_t diagnostics[68]{};Profile profile{};uint8_t tail[19308]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Battle QTE packet");
struct Dispatcher {
 uint64_t base=0,session=0,owner=0;CallIdentity ids[10]{};uint64_t leases[10]{};uint32_t guid[4]{},injected=0,observations[6]{};size_t hook=0,damage_hook=0;bool routing=false,damage_routing=false,unknown=false;DWORD thread=0;inline static Dispatcher*live=nullptr;Profile profile{};
 struct DamageFrame{uint64_t frame=0,locals=0;double original=0.;};DamageFrame damage_frames[8]{};
 uint32_t damage_hits=0,damage_bonus_hits=0;double last_damage_multiplier=0.,last_qte_multiplier=0.;
 CallIdentity pending[8]{},pending_sequence[8]{},seen[64]{};unsigned used=0,seen_next=0;uint32_t stage=0;double clock_now=0.,clock_asset=0.;
 bool configured(uint64_t object,unsigned i,bool type=false)const{const std::string path(profile.paths[i]);const auto dot=path.find('.');if(dot==std::string::npos)return false;const auto package=path.substr(0,dot),name=path.substr(dot+1);return type?picto_class(base,object,name.c_str(),package.c_str()):e33_mesh::named(base,object,name.c_str(),package.c_str());}
 bool active()const{return owner||hook||routing||damage_hook||damage_routing;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto t:leases)if(t==token)return true;return false;}
 bool bound()const{e33_story_action::Dispatcher p;p.base=base;p.gi=ids[0];std::memcpy(p.guid,guid,16);return p.bound();}
 bool method(uint64_t f,const char*name,int size,uint32_t flags)const{
  return call_capture(base,f).address&&exact_name(base,f+24,name)&&e33_mesh::named(base,local_read<uint64_t>(f+32),"BP_BattleSequenceTimeline_C","/Game/Gameplay/Battle/SkillCombos/BP_BattleSequenceTimeline")&&local_read<uint32_t>(f+0xb0)==flags&&local_read<uint16_t>(f+0xb6)==size&&local_read<uint64_t>(f+0xd8)==base+0x13937a0;
 }
 void observe(void*object,void*frame){
  ++observations[0];if(unknown||thread!=GetCurrentThreadId()||!bound())return;
  ++observations[1];
  const auto obj=reinterpret_cast<uint64_t>(object),f=reinterpret_cast<uint64_t>(frame);
  if(!obj||!f||!picto_class(base,obj,"BP_BattleSequenceTimeline_C","/Game/Gameplay/Battle/SkillCombos/BP_BattleSequenceTimeline"))return;
  ++observations[2];const auto locals=local_read<uint64_t>(f+0x28);
  if(local_read<uint64_t>(f+0x10)!=ids[3].address||local_read<uint64_t>(f+0x18)!=obj||!locals||zone_ref(base,local_read<uint64_t>(locals),"LevelSequence")!=ids[1].address)return;
  ++observations[3];const auto character=zone_ref(base,local_read<uint64_t>(locals),"SourceCharacter"),stats=zone_ref(base,character,"AC_jRPG_CharacterStats");
  if(!character||!stats||!configured(character,1,true)||zone_ref(base,local_read<uint64_t>(local_read<uint64_t>(character+32)+32),"OwningGameInstance")!=ids[0].address)return;
  ++observations[4];auto candidate=call_capture(base,obj);if(!candidate.address)return;
  const auto sequence=call_capture(base,local_read<uint64_t>(locals));if(!sequence.address)return;
  for(const auto&previous:seen)if(previous.address==sequence.address&&previous.index==sequence.index&&previous.serial==sequence.serial)return;
  for(unsigned i=0;i<used;++i)if(pending_sequence[i].address==sequence.address)return;
  ++observations[5];if(used==8){unknown=true;return;}pending[used]=candidate;pending_sequence[used++]=sequence;
 }
 static e33_blueprint_transform::Decision pre(void*ctx,uint64_t,void*object,void*frame){auto*self=static_cast<Dispatcher*>(ctx);unsigned before=self->used;__try{self->observe(object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;}return {self->used>before?1ULL:0ULL,false};}
 static void post(void*ctx,uint64_t token){auto*self=static_cast<Dispatcher*>(ctx);if(!token)return;__try{self->inject();}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;}}
 static void __fastcall wrapper(void*object,void*frame,void*result){auto*self=live;if(!self)return;auto decision=pre(self,self->ids[3].address,object,frame);reinterpret_cast<e33_trace::Entry>(self->base+0x13937a0)(object,frame,result);post(self,decision.token);}
 // This callee-frame transform applies the configured bonus per successful
 // input, without changing base power or break damage.
 e33_blueprint_transform::Decision damage_begin(void*object,void*frame){
  if(unknown||!owner||thread!=GetCurrentThreadId())return {};
  const auto f=reinterpret_cast<uint64_t>(frame),obj=reinterpret_cast<uint64_t>(object);
  if(!f||local_read<uint64_t>(f+0x10)!=ids[8].address||local_read<uint64_t>(f+0x18)!=obj)return {};
  const auto locals=local_read<uint64_t>(f+0x28);if(!locals)return {};
  const auto script=local_read<uint64_t>(locals+72);
  if(!configured(script,2,true))return {};
  const auto character=zone_ref(base,script,"CurrentCharacter"),stats=zone_ref(base,character,"AC_jRPG_CharacterStats");
  if(!character||!stats||local_read<uint64_t>(locals+32)!=stats||local_read<uint8_t>(locals+48)!=profile.damage_reason||
   !configured(character,1,true)||
   zone_ref(base,local_read<uint64_t>(local_read<uint64_t>(character+32)+32),"OwningGameInstance")!=ids[0].address||!bound())return {};
  // A direct Blueprint route and UFunction wrapper can observe the same frame.
  // Correlate the live frame so a successful input never multiplies it twice.
  unsigned slot=8;for(unsigned i=0;i<8;++i){if(damage_frames[i].frame==f)return {};if(!damage_frames[i].frame)slot=i;}
  if(slot==8){unknown=true;return {};}
  const double factor=local_read<double>(locals+16);if(!std::isfinite(factor)||factor<0.||factor>100.){unknown=true;return {};}
  alignas(16)uint8_t combo[4096]{};dispatch(character,ids[9].address,combo);
  const int success=*reinterpret_cast<int32_t*>(combo+4),fail=*reinterpret_cast<int32_t*>(combo+8),perfect=*reinterpret_cast<int32_t*>(combo+12);
  // The original getter exposes success/perfect tallies independently. Do not
  // assume disjoint categories when two perfect prompts are accepted.
  if(success<0||fail<0||perfect<0||unsigned(success)>profile.count||unsigned(fail)>profile.count||unsigned(perfect)>profile.count){unknown=true;return {};}
  const double bonus=1.+profile.bonus_per_input*double(success+perfect),corrected=factor*bonus;
  damage_frames[slot]={f,locals,factor};std::memcpy(reinterpret_cast<void*>(locals+16),&corrected,8);
  ++damage_hits;if(success+perfect)++damage_bonus_hits;last_damage_multiplier=corrected;last_qte_multiplier=bonus;
  return {uint64_t(slot+1),false};
 }
 static e33_blueprint_transform::Decision damage_pre(void*ctx,uint64_t,void*object,void*frame){auto*self=static_cast<Dispatcher*>(ctx);__try{return self->damage_begin(object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;return {};}}
 static void damage_post(void*ctx,uint64_t token){if(!token||token>8)return;auto*self=static_cast<Dispatcher*>(ctx);auto&f=self->damage_frames[token-1];__try{if(f.frame&&f.locals)std::memcpy(reinterpret_cast<void*>(f.locals+16),&f.original,8);f={};}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;}}
 static void __fastcall damage_wrapper(void*object,void*frame,void*result){auto*self=live;if(!self)return;auto decision=damage_pre(self,self->ids[8].address,object,frame);reinterpret_cast<e33_trace::Entry>(self->base+0x13937a0)(object,frame,result);damage_post(self,decision.token);}
 void dispatch(uint64_t receiver,uint64_t fn,void*args){const auto pe=local_read<uint64_t>(local_read<uint64_t>(receiver)+0x268);reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(receiver),reinterpret_cast<void*>(fn),args);}
 template<class Pool>void poll(Pool&){} // Initialization is synchronous with the retained callee frame.
 void inject(){
  if(!active()||unknown||!used)return;
  if(thread!=GetCurrentThreadId()||!bound()){used=0;return;}
  while(used){
   auto id=pending[0];const auto sequence=pending_sequence[0];for(unsigned i=1;i<used;++i){pending[i-1]=pending[i];pending_sequence[i-1]=pending_sequence[i];}--used;
   const auto fresh=call_capture(base,id.address);if(fresh.index!=id.index||fresh.address!=id.address||(id.serial&&fresh.serial!=id.serial))continue;
   if(!call_identity(base,sequence)||zone_ref(base,id.address,"CurrentBattleSequence")!=sequence.address||zone_ref(base,sequence.address,"LevelSequence")!=ids[1].address)continue;
   stage=1;const auto pe=local_read<uint64_t>(local_read<uint64_t>(id.address)+0x268);if(pe!=base+0x1393330&&pe!=base+0x332bb90){unknown=true;return;}
   // The original declaration's live frame still retains its timeline and
   // sequence arguments. No delayed raw identity or extra engine lease.
   seen[seen_next++%64]=sequence;
   alignas(16)uint8_t now_args[4096]{},asset_args[4096]{};
   stage=4;dispatch(id.address,ids[5].address,now_args);stage=5;dispatch(id.address,ids[6].address,asset_args);
   const auto now=*reinterpret_cast<double*>(now_args);const auto asset=*reinterpret_cast<float*>(asset_args);
   // Convert configured asset impacts into the live declaration clock.
   stage=6;clock_now=now;clock_asset=asset;e33_battle_qte_timing::Window windows[16]{};
   const auto timing=e33_battle_qte_timing::plan(now,asset,profile,windows);
   if(timing==e33_battle_qte_timing::Result::Invalid){unknown=true;return;}
   // Once the full input interval no longer fits before damage, do not create
   // past-due keys or mark this safely unmodified owner unknown. Stage 11 is
   // an explicit missed-timing diagnostic; subsequent casts can still work.
   if(timing==e33_battle_qte_timing::Result::TooLate){stage=11;return;}
   // The pre-event remains in the future even if this frame consumed part of
   // the normal anticipation. Both 180 ms input windows still end on impact.
   unknown=true;
   stage=7;for(unsigned i=0;i<profile.count;++i){const auto&window=windows[i];
    alignas(16)double args[512]{};args[0]=window.start;args[1]=window.anticipation;args[2]=window.validity;args[3]=window.now;
    dispatch(id.address,ids[4].address,args);
   }
   stage=8;alignas(16)uint8_t args[4096]{};dispatch(id.address,ids[7].address,args);
   stage=10;unknown=false;++injected;
  }
 }
 bool close(){
  if(unknown)return false;
  for(const auto&f:damage_frames)if(f.frame)return false;
  if(damage_hook){auto*p=reinterpret_cast<void*volatile*>(ids[8].address+0xd8);if(InterlockedCompareExchangePointer(p,reinterpret_cast<void*>(base+0x13937a0),reinterpret_cast<void*>(damage_wrapper))!=reinterpret_cast<void*>(damage_wrapper)){unknown=true;return false;}damage_hook=0;}
  if(hook){auto*p=reinterpret_cast<void*volatile*>(ids[3].address+0xd8);if(InterlockedCompareExchangePointer(p,reinterpret_cast<void*>(base+0x13937a0),reinterpret_cast<void*>(wrapper))!=reinterpret_cast<void*>(wrapper)){unknown=true;return false;}hook=0;}
  if(routing||damage_routing){e33_blueprint_transform::detach(this);if(damage_routing){if(!BlueprintDirectTrace::release_narrative(ids[8].address))return false;damage_routing=false;}if(routing){if(!BlueprintDirectTrace::release_narrative(ids[3].address))return false;routing=false;}}live=nullptr;
  used=0;owner=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.injected||p.guid[0]!=0xe33c5701U||!valid(p.profile)){p.error=rejected;return;}
  for(auto v:p.diagnostics)if(v){p.error=rejected;return;}for(auto v:p.tail)if(v){p.error=rejected;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(guid,p.guid,16)||std::memcmp(&profile,&p.profile,sizeof(profile))){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   p.injected=injected;std::memcpy(p.diagnostics,observations,sizeof(observations));std::memcpy(p.diagnostics+24,&stage,4);std::memcpy(p.diagnostics+28,&clock_now,8);std::memcpy(p.diagnostics+36,&clock_asset,8);std::memcpy(p.diagnostics+44,&damage_hits,4);std::memcpy(p.diagnostics+48,&damage_bonus_hits,4);std::memcpy(p.diagnostics+52,&last_damage_multiplier,8);std::memcpy(p.diagnostics+60,&last_qte_multiplier,8);if(unknown){p.error=uncertain;return;}p.state=2;return;
  }
  if(active()){p.error=rejected;return;}
  for(unsigned i=0;i<10;++i)if(!call_identity(b,p.ids[i])||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  base=b;session=s;profile=p.profile;std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,16);
  if(!bound()||!configured(ids[1].address,0)||
   !configured(ids[2].address,1)||
   !method(ids[3].address,"DeclareBattleSequenceTimingsAsList",104,214040576)||!method(ids[4].address,"AddQTEPresetKeyframes",32,209977344)||
   !method(ids[5].address,"GetCurrentTimeForBattleSequenceTimeline",8,474087424)||!method(ids[6].address,"GetCurrentBattleSequenceTimeInAsset",4,482476032)||!method(ids[7].address,"QueueNextBattleSequenceKeyframe",0,209846272)){p.error=4252;return;}
  const auto f=ids[4].address;const char*names[]={"WindowStartTime","AnticipationDuration","ValidityDuration","NowTime"};
  for(unsigned i=0;i<4;++i)if(!picto_struct_field(b,f,names[i],"DoubleProperty",i*8,8)){p.error=4253;return;}
  if(!exact_name(b,ids[8].address+24,"MakeDamageBuilder")||!e33_mesh::named(b,local_read<uint64_t>(ids[8].address+32),"FL_BattleHelpers_C","/Game/Gameplay/Battle/FL_BattleHelpers")||
   local_read<uint32_t>(ids[8].address+0xb0)!=205660160||local_read<uint16_t>(ids[8].address+0xb6)!=88||local_read<uint64_t>(ids[8].address+0xd8)!=b+0x13937a0||
   !exact_name(b,ids[9].address+24,"GetLastSkillComboInfo")||!e33_mesh::named(b,local_read<uint64_t>(ids[9].address+32),"BP_jRPG_Character_Battle_Base_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_Battle_Base")||
   local_read<uint32_t>(ids[9].address+0xb0)!=1547829248||local_read<uint16_t>(ids[9].address+0xb6)!=16||local_read<uint64_t>(ids[9].address+0xd8)!=b+0x13937a0){p.error=4254;return;}
  const char*dn[]={"TargetCharacterStats","AttackElement","FinalDamageMultiplier","BreakBarDamageMultiplier","DamageSource","DamageReason","DebugReason","__WorldContext","ReturnValue"};
  const char*dt[]={"ObjectProperty","ByteProperty","DoubleProperty","DoubleProperty","InterfaceProperty","ByteProperty","StrProperty","ObjectProperty","ObjectProperty"};
  const int offsets[]={0,8,16,24,32,48,56,72,80},sizes[]={8,1,8,8,16,1,16,8,8};
  for(unsigned i=0;i<9;++i)if(!picto_struct_field(b,ids[8].address,dn[i],dt[i],offsets[i],sizes[i])){p.error=4255;return;}
  const char*cn[]={"OnlySuccess","OnlyFail","OnlyPerfect","SuccessCount","FailCount","PerfectCount"};
  for(unsigned i=0;i<6;++i)if(!picto_struct_field(b,ids[9].address,cn[i],i<3?"BoolProperty":"IntProperty",i<3?i:(i-2)*4,i<3?1:4)){p.error=4256;return;}
  owner=p.owner;thread=GetCurrentThreadId();
  if(!BlueprintDirectTrace::retain_narrative(b,ids[3].address)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}routing=true;
  if(!e33_blueprint_transform::attach(this,ids[3].address,pre,post)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}
  HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(wrapper),&pinned)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}
  live=this;if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(ids[3].address+0xd8),reinterpret_cast<void*>(wrapper),reinterpret_cast<void*>(b+0x13937a0))!=reinterpret_cast<void*>(b+0x13937a0)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}hook=1;
  if(!BlueprintDirectTrace::retain_narrative(b,ids[8].address)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}damage_routing=true;
  if(!e33_blueprint_transform::attach(this,ids[8].address,damage_pre,damage_post)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}
  if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(ids[8].address+0xd8),reinterpret_cast<void*>(damage_wrapper),reinterpret_cast<void*>(b+0x13937a0))!=reinterpret_cast<void*>(b+0x13937a0)){p.error=e33_skill_install::rollback(*this,rejected,uncertain);return;}damage_hook=1;
  std::memset(observations,0,sizeof(observations));
  owner=p.owner;thread=GetCurrentThreadId();injected=used=seen_next=damage_hits=damage_bonus_hits=0;last_damage_multiplier=last_qte_multiplier=0.;unknown=false;std::memset(seen,0,sizeof(seen));p.state=1;
 }
};
}
