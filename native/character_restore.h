#pragma once
#include "character_restore_rules.h"
#include "character_restore_profile.h"
#include "owned_action_array_copy.h"
#include "npc_current_context_guard.h"
namespace e33_character_restore {
constexpr uint32_t operation=261,rejected=4300,uncertain=4301;
constexpr unsigned count=10;
// GI, current CharacterData, exact configured graph, original refresh/load/slot
// functions, original save-state UScriptStruct, and scoped original file-read
// result (or the configured graph for a live-state repair), and original cosmetic
// setter/load callbacks. No client skill or customization values are accepted.
#pragma pack(push,1)
struct Packet{uint32_t version=5,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[count]{};uint64_t leases[count]{};uint32_t guid[4]{},mode=0,stage=0,source=0,unlocked=0,equipped=0;int32_t slot=-1;uint32_t file_count=0;char16_t file[260]{};e33_character_graph::Profile profile{};uint8_t tail[15600]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Character restore packet");
static_assert(offsetof(Packet,leases)==184&&offsetof(Packet,guid)==264&&offsetof(Packet,mode)==280&&offsetof(Packet,stage)==284&&offsetof(Packet,slot)==300&&offsetof(Packet,file)==308&&offsetof(Packet,profile)==828&&offsetof(Packet,tail)==5384,"Character restore protocol 5 layout");
struct Dispatcher {
 uint64_t base=0,session=0,owner=0;CallIdentity ids[count]{};uint64_t leases[count]{};uint32_t guid[4]{},stage=0,source=0;
 bool unknown=false,done=false;uint64_t names[9]{},assets[9]{},character_name=0;
 int32_t selected_slot=-1;uint32_t selected_file_count=0;char16_t selected_file[260]{};
 e33_character_restore_rules::Snapshot saved{};
 e33_character_restore_rules::Appearance current_appearance{},selected_appearance{};
 uint64_t customization_struct=0,appearance_alignment_padding=0;
 // Caller-owned parameter values outlive all dispatch/verification. The original
 // Blueprint copies its by-value input into its VM frame; it never owns these
 // buffers. They remain pinned in the owner if execution/readback is uncertain.
 alignas(16)uint8_t arguments[448]{};
 alignas(16)uint8_t appearance_arguments[32]{};
 e33_character_graph::Profile profile{};uint32_t profile_padding=0;
 bool active()const{return owner!=0||unknown;}
 void diagnostics(Packet&p)const{p.stage=stage;p.source=source;p.unlocked=saved.unlock_count;p.equipped=saved.equip_count;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto t:leases)if(t==token)return true;return false;}
 bool close(){if(unknown)return false;owner=0;done=false;std::memset(arguments,0,sizeof(arguments));std::memset(appearance_arguments,0,sizeof(appearance_arguments));saved={};current_appearance={};selected_appearance={};return true;}
 bool inner(uint64_t descriptor,const char*kind,int width)const{
  const auto p=local_read<uint64_t>(descriptor+0x78);
  return !(local_read<uint8_t>(descriptor+0x70)&1)&&p&&local_read<uint64_t>(p+16)==descriptor&&exact_name(base,local_read<uint64_t>(p+8),kind)&&
   local_read<int32_t>(p+0x30)==1&&local_read<int32_t>(p+0x34)==width&&local_read<int32_t>(p+0x44)==0;
 }
 bool array(uint64_t at,uint64_t*out,unsigned limit,unsigned&n)const{
  const auto data=local_read<uint64_t>(at);const int length=local_read<int32_t>(at+8),capacity=local_read<int32_t>(at+12);
  if(length<0||length>int(limit)||capacity<length||capacity>64||(length&&(!data||(data&7))))return false;
  n=unsigned(length);for(unsigned i=0;i<n;++i)out[i]=local_read<uint64_t>(data+uint64_t(i)*8);return true;
 }
 bool method(unsigned i,const char*name,const char*cls,const char*package,int size,uint32_t flags=209846272U)const{
  const auto f=ids[i].address;
  return exact_name(base,f+24,name)&&e33_mesh::named(base,local_read<uint64_t>(f+32),cls,package)&&local_read<uint32_t>(f+0xb0)==flags&&
   local_read<uint16_t>(f+0xb6)==size&&local_read<uint16_t>(f+0xb8)==65535&&local_read<uint64_t>(f+0xd8)==base+0x13937a0;
 }
 bool context()const{
  e33_story_action::Dispatcher p;p.base=base;p.gi=ids[0];std::memcpy(p.guid,guid,16);
  e33_retired_world::Snapshot world{};e33_retired_world::TargetOps proof{base};
  if(!p.bound()||!proof.observe(world)||zone_ref(base,world.world.address,"OwningGameInstance")!=ids[0].address)return false;
  const auto manager=zone_ref(base,ids[0].address,"SaveManager");uint64_t ld=0,sd=0;
  if(!manager||!picto_class(base,manager,"BP_SaveManager_C","/Game/Gameplay/Save/BP_SaveManager")||zone_ref(base,manager,"GameInstanceReference")!=ids[0].address)return false;
  const auto loading=picto_field(base,manager,"LoadIsInProgress","BoolProperty",169,1,&ld),loaded=picto_field(base,ids[0].address,"SaveLoaded","BoolProperty",2680,1,&sd);
  if(!loading||!loaded||local_read<uint32_t>(ld+0x70)!=0xff010001U||local_read<uint32_t>(sd+0x70)!=0xff010001U||local_read<uint8_t>(loading)||local_read<uint8_t>(loaded)!=1)return false;
  uint64_t changing_descriptor=0;const auto changing=picto_field(base,ids[0].address,"IsChangingMap","BoolProperty",464,1,&changing_descriptor);
  if(!changing||local_read<uint32_t>(changing_descriptor+0x70)!=0xff010001U||local_read<uint8_t>(changing))return false;
  const auto player=console_find(base,nullptr,"LocalPlayer");
  const auto controller=player?call_capture(base,zone_ref(base,player,"PlayerController")):CallIdentity{};
  if(!controller.address||!proof.controller_world(controller,world.world))return false;
  e33_npc_presentation::CurrentContextGuard battle{base,controller,world.world};if(!battle.battle_quiescent())return false;
  e33_inventory_reward::Dispatcher maps;uint64_t actor=0;
  return maps.map_object(base,ids[0].address,"CharactersCollection",2344,character_name,actor)&&actor==ids[1].address;
 }
 bool graph(){
  if(!e33_mesh::named(base,ids[2].address,profile.graph_asset,profile.graph_package))return false;
  uint64_t d=0;const auto nodes=picto_field(base,ids[2].address,"Nodes","ArrayProperty",48,16,&d);
  if(!nodes||!inner(d,"StructProperty",56))return false;
  const auto st=local_read<uint64_t>(local_read<uint64_t>(d+0x78)+0x70);
  if(!e33_mesh::named(base,st,"FSkillGraphNode","/Game/Gameplay/SkillTree/FSkillGraphNode"))return false;
  const auto unlock=picto_struct_field(base,st,"SkillUnlock_3_15FA1C06433ACE049603919CDF6155FF","StructProperty",0,40);
  const auto us=unlock?local_read<uint64_t>(unlock+0x70):0;
  if(!e33_mesh::named(base,us,"FSkillUnlockData","/Game/Gameplay/SkillTree/FSkillUnlockData")||
   !picto_struct_field(base,us,"Skill_2_9E4FC5804778258FBAA04BBF7F68F799","ObjectProperty",0,8)||
   !picto_struct_field(base,us,"UnlockCost_5_E90ABE13467BBA2959E91AB582E679AF","IntProperty",8,4))return false;
  const auto start=picto_struct_field(base,us,"IsStartingSkill_13_E1837512408188F4B7D355B6B67B8C1E","BoolProperty",12,1);
  if(!start||local_read<uint32_t>(start+0x70)!=0xff010001U)return false;
  const auto data=local_read<uint64_t>(nodes);const auto n=local_read<int32_t>(nodes+8),cap=local_read<int32_t>(nodes+12);
  if(n!=int(profile.count)||cap<n||cap>64||!data||(data&7))return false;
  unsigned seen=0;
  for(int j=0;j<n;++j){const auto row=data+uint64_t(j)*56,skill=local_read<uint64_t>(row);if(!call_capture(base,skill).address)return false;
   const auto name=picto_field(base,skill,"NameID","NameProperty",96,8);if(!name)return false;
   const int i=e33_character_restore_rules::index(names,local_read<uint64_t>(name),profile.count);if(i<0||(seen&(1U<<i)))return false;
   const auto&spec=profile.skills[i];if(!e33_mesh::named(base,skill,spec.asset,spec.package)||local_read<int32_t>(row+8)!=int32_t(spec.cost)||local_read<uint8_t>(row+12)!=spec.starter)return false;
   seen|=1U<<i;assets[i]=skill;
  }return seen==((1U<<profile.count)-1);
 }
 bool object_skills(uint64_t system,e33_character_restore_rules::Snapshot&out)const{
  if(!call_capture(base,system).address||!picto_class(base,system,"BP_CharacterSkillGraphSystem_C","/Game/Gameplay/SkillTree/BP_CharacterSkillGraphSystem")||
   zone_ref(base,system,"TempCharacterData")!=ids[1].address)return false;
  const char*fields[]={"UnlockedSkills","EquippedSkills"};const int offsets[]={48,72};
  for(unsigned k=0;k<2;++k){uint64_t d=0;const auto a=picto_field(base,system,fields[k],"ArrayProperty",offsets[k],16,&d);
   uint64_t objects[9]{};unsigned n=0;if(!a||!inner(d,"ObjectProperty",8)||!array(a,objects,k?6U:9U,n))return false;
   auto*values=k?out.equipped:out.unlocked;if(k)out.equip_count=n;else out.unlock_count=n;
   for(unsigned j=0;j<n;++j){if(!objects[j]){if(!k)return false;values[j]=0;continue;}int found=-1;for(int i=0;i<9;++i)if(objects[j]==assets[i])found=i;if(found<0)return false;values[j]=names[found];}
  }return true;
 }
 uint64_t loaded_save(uint64_t manager){
  stage=550;
  const auto slot=picto_field(base,manager,"SelectedSlot","IntProperty",288,4),slots=picto_field(base,manager,"SaveSlots","ArrayProperty",48,16),
   relevant=picto_field(base,ids[0].address,"LastRelevantSaveName","StrProperty",2984,16);
  uint64_t busy_descriptor=0;const auto busy=picto_field(base,manager,"SaveIsInProgress","BoolProperty",81,1,&busy_descriptor);
  if(!slot||!slots||!relevant||!busy||local_read<uint32_t>(busy_descriptor+0x70)!=0xff010001U||local_read<uint8_t>(busy))return 0;
  stage=551;const auto active=local_read<uint64_t>(relevant);
  const int length=local_read<int32_t>(relevant+8),capacity=local_read<int32_t>(relevant+12),slot_count=local_read<int32_t>(slots+8),slot_cap=local_read<int32_t>(slots+12);
  if(active<0x10000||active>0x7fffffffffffULL||(active&1)||capacity<length||capacity>1024||slot_cap<slot_count||slot_cap>32)return 0;
  stage=552;
  if(!e33_character_restore_rules::selected_file(selected_slot,local_read<int32_t>(slot),slot_count,selected_file,int(selected_file_count),reinterpret_cast<const char16_t*>(active),length))return 0;
  // The engine discards AsyncLoad's UObject frame references after the handoff.
  // Python calls only original ComputeSaveFilePath / LoadGameFromSlot and the
  // retained typed-result protocol pins this exact object before exposing it.
  // Its selected filename and embedded save GUID are independently rechecked.
  stage=56;const auto save=ids[7].address;
  if(!call_identity(base,ids[7])||!picto_class(base,save,"BP_SaveGameObject_V8_C","/Game/Gameplay/Save/SaveObjects/BP_SaveGameObject_V8"))return 0;
  return save;
 }
 bool appearance(uint64_t at,e33_character_restore_rules::Appearance&out)const{
  if(!at)return false;
  out={local_read<uint64_t>(at),local_read<uint64_t>(at+8)};
  // These are copied from engine-owned state, never client-provided FNames.
  // Qualify the allocator entry before passing either name back to the game.
  for(auto value:{out.skin,out.face}){char name[128]{};if(value&&!asset_name(base,uint32_t(value),name,sizeof(name)))return false;}
  return true;
 }
 bool read_appearance(e33_character_restore_rules::Appearance&out)const{
  uint64_t d=0;const auto at=picto_field(base,ids[1].address,"CharacterCustomizationItemData","StructProperty",2072,16,&d);
  return at&&local_read<uint64_t>(d+0x38)==2251869606969861ULL&&local_read<uint64_t>(d+0x70)==customization_struct&&appearance(at,out);
 }
 bool snapshot(){
  stage=50;if(!read_appearance(current_appearance))return false;
  selected_appearance=current_appearance;
  // A configured graph already active means the user may have unsaved choices.
  // Never roll these back to the older save object during a definition repair.
  if(zone_ref(base,ids[1].address,"SkillGraph")==ids[2].address){source=2;if(ids[7].address!=ids[2].address||selected_slot!=-1||selected_file_count)return false;return object_skills(zone_ref(base,ids[1].address,"SkillGraphSystem"),saved);}
  source=1;stage=51;const auto manager=zone_ref(base,ids[0].address,"SaveManager");uint64_t ld=0,sd=0;
  if(!manager||!picto_class(base,manager,"BP_SaveManager_C","/Game/Gameplay/Save/BP_SaveManager")||zone_ref(base,manager,"GameInstanceReference")!=ids[0].address)return false;
  stage=52;const auto loading=picto_field(base,manager,"LoadIsInProgress","BoolProperty",169,1,&ld),loaded=picto_field(base,ids[0].address,"SaveLoaded","BoolProperty",2680,1,&sd);
  if(!loading||!loaded||local_read<uint32_t>(ld+0x70)!=0xff010001U||local_read<uint32_t>(sd+0x70)!=0xff010001U||local_read<uint8_t>(loading)||local_read<uint8_t>(loaded)!=1)return false;
  const auto save=loaded_save(manager);if(!save)return false;
  stage=57;
  uint64_t marker_descriptor=0;const auto marker=picto_field(base,save,"InteractedDialogues","MapProperty",1944,80,&marker_descriptor);
  std::vector<e33_story_identity::Entry> entries; e33_story_identity::Entry found{};
  if(!marker||!e33_story_identity::snapshot(marker,marker_descriptor,entries)||e33_story_identity::marker(entries,found)!=1||std::memcmp(found.guid,guid,16)||found.value!=e33_story_identity::stage)return false;
  stage=58;uint64_t d=0;const auto map=picto_field(base,save,"CharactersCollection","MapProperty",64,80,&d);e33_inventory_reward::Dispatcher maps;
  if(!map||!maps.map_schema(base,d,"StructProperty",448,464)||local_read<uint64_t>(local_read<uint64_t>(d+0x78)+0x70)!=ids[6].address)return false;
  stage=59;PictoSparseView view{};if(!picto_sparse(map,464,128,view))return false;uint64_t row=0;
  for(int i=0;i<view.count;++i)if(view.active(i)){const auto at=view.data+uint64_t(i)*464;if(local_read<uint64_t>(at)==character_name){if(row)return false;row=at+8;}}
  stage=60;if(!row||local_read<uint64_t>(row)!=character_name)return false;
  stage=61;if(!array(row+392,saved.unlocked,9,saved.unlock_count))return false;
  stage=62;if(!array(row+408,saved.equipped,6,saved.equip_count))return false;
  stage=63;e33_character_restore_rules::Appearance checkpoint{};
  if(!appearance(row+424,checkpoint))return false;
  selected_appearance=e33_character_restore_rules::selection(current_appearance,checkpoint);return true;
 }
 void dispatch(uint64_t object,unsigned fn,void*args){
  const auto pe=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);if(pe!=base+0x1393330&&pe!=base+0x332bb90)throw uncertain;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(ids[fn].address),args);
 }
 bool schemas(){
  const char*package="/Game/Gameplay/SkillTree/BP_CharacterSkillGraphSystem";
  if(!method(3,"LoadCharacterBaseDataFromID","BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData",8)||
   !method(4,"LoadCharacterState","BP_CharacterSkillGraphSystem_C",package,448)||!method(5,"EquipSkillAtSlot","BP_CharacterSkillGraphSystem_C",package,12,205651968U)||
   !picto_struct_field(base,ids[3].address,"HardcodedNameID","NameProperty",0,8)||!picto_struct_field(base,ids[5].address,"SkillDefinition","ObjectProperty",0,8)||!picto_struct_field(base,ids[5].address,"Index","IntProperty",8,4))return false;
  const auto param=picto_struct_field(base,ids[4].address,"CharacterSaveState","StructProperty",0,448),st=ids[6].address;
  if(!param||local_read<uint64_t>(param+0x38)!=2251799813685396ULL||local_read<uint64_t>(param+0x70)!=st||
   !e33_mesh::named(base,st,"S_jRPG_CharacterSaveState","/Game/jRPGTemplate/Structures/S_jRPG_CharacterSaveState")||
   !picto_struct_field(base,st,"CharacterHardcodedName_36_FB9BA9294D02CFB5AD3668B0C4FD85A5","NameProperty",0,8))return false;
  const auto u=picto_struct_field(base,st,"UnlockedSkills_197_FAA1BD934F68CFC542FB048E3C0F3592","ArrayProperty",392,16),e=picto_struct_field(base,st,"EquippedSkills_201_05B6B5E9490E2586B23751B11CDA521F","ArrayProperty",408,16);
  if(!u||!e||!inner(u,"NameProperty",8)||!inner(e,"NameProperty",8))return false;
  if(!method(8,"SetCharacterCustomizationItemData","BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData",16,201457664U)||
   !method(9,"LoadCharacterCustomizationFromItemData","BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData",0,201457664U))return false;
  const auto input=picto_struct_field(base,ids[8].address,"CharacterCustomizationItemData","StructProperty",0,16);
  const auto saved_field=picto_struct_field(base,st,"CharacterCustomization_204_6208BA0E4E743356022DAEB14D88C37C","StructProperty",424,16);
  customization_struct=input?local_read<uint64_t>(input+0x70):0;
  if(!input||!saved_field||local_read<uint64_t>(input+0x38)!=2251869606904468ULL||local_read<uint64_t>(saved_field+0x38)!=2251869606904325ULL||local_read<uint64_t>(saved_field+0x70)!=customization_struct||
   !e33_mesh::named(base,customization_struct,"S_CharacterCustomizationItemData","/Game/Gameplay/CharacterCustomization/Blueprints/S_CharacterCustomizationItemData"))return false;
  const char*fields[]={"CharacterSkin_4_D6F8B7E048CBA86E677340839167C4FA","CharacterFace_6_069193A2473BA2E48EDF77841A8F3AFD"};
  for(unsigned i=0;i<2;++i){const auto field=picto_struct_field(base,customization_struct,fields[i],"NameProperty",int(i*8),8);if(!field||local_read<uint64_t>(field+0x38)!=2251869606904325ULL)return false;}
  return true;
 }
 uint64_t empty_copy_property()const{
  // The existing SDK engine-copy qualification is reused only for this exact
  // ObjectProperty array. The caller cannot choose a destination or contents.
  const auto cls=local_read<uint64_t>(ids[4].address+32);
  const auto d=picto_struct_field(base,cls,"EquippedSkills","ArrayProperty",72,16);
  if(!d||local_read<uint64_t>(d)!=base+e33_action_clone::array_property_table||local_read<uint64_t>(d+0x38)!=65541ULL||!inner(d,"ObjectProperty",8))return 0;
  const auto item=local_read<uint64_t>(d+0x78);
  if(local_read<uint64_t>(item)!=base+0x6e11d38||!e33_mesh::named(base,local_read<uint64_t>(item+0x70),"BP_DataAsset_Skill_C","/Game/Gameplay/SkillTree/BP_DataAsset_Skill")||
   local_read<uint64_t>(base+e33_action_clone::array_property_table+0xf0)!=base+e33_action_clone::array_copy_entry||
   std::memcmp(reinterpret_cast<void*>(base+e33_action_clone::array_copy_entry),e33_action_clone::array_copy_prefix,sizeof(e33_action_clone::array_copy_prefix)))return 0;
  return d;
 }
 void restore(){
  std::memset(arguments,0,sizeof(arguments));std::memcpy(arguments,&character_name,8);
  const uint64_t up=reinterpret_cast<uint64_t>(saved.unlocked),ep=reinterpret_cast<uint64_t>(saved.equipped);
  std::memcpy(arguments+392,&up,8);std::memcpy(arguments+400,&saved.unlock_count,4);std::memcpy(arguments+404,&saved.unlock_count,4);
  std::memcpy(arguments+408,&ep,8);std::memcpy(arguments+416,&saved.equip_count,4);std::memcpy(arguments+420,&saved.equip_count,4);
  const auto snapshot_copy=saved;uint8_t params_copy[448]{};std::memcpy(params_copy,arguments,448);
  stage=10;unknown=true;uint64_t refresh_arg=character_name;dispatch(ids[1].address,3,&refresh_arg);
  if(refresh_arg!=character_name||!context()||zone_ref(base,ids[1].address,"SkillGraph")!=ids[2].address)throw uncertain;
  const auto system=zone_ref(base,ids[1].address,"SkillGraphSystem");e33_character_restore_rules::Snapshot initial{};
  if(!object_skills(system,initial)||initial.unlock_count!=1||initial.unlocked[0]!=names[0])throw uncertain;
  stage=11;dispatch(system,4,arguments);
  if(std::memcmp(&snapshot_copy,&saved,sizeof(saved))||std::memcmp(params_copy,arguments,448))throw uncertain;
  if(e33_character_restore_rules::empty_loadout(saved)){
   stage=13;const auto d=empty_copy_property();uint64_t current_descriptor=0;
   const auto destination=picto_field(base,system,"EquippedSkills","ArrayProperty",72,16,&current_descriptor);
   if(!d||d!=current_descriptor||!destination||!context()||zone_ref(base,ids[1].address,"SkillGraphSystem")!=system||zone_ref(base,system,"TempCharacterData")!=ids[1].address)throw uncertain;
   // All values are null: the saved FName zeroes also form the exact desired
   // UObject pointer array. CopyCompleteValue frees/replaces only the new
   // system's engine-owned array; it never borrows this parameter buffer.
   using Copy=void(*)(void*,void*,const void*,int);
   reinterpret_cast<Copy>(base+e33_action_clone::array_copy_entry)(reinterpret_cast<void*>(d),reinterpret_cast<void*>(destination),arguments+408,1);
   if((saved.equip_count&&local_read<uint64_t>(destination)==reinterpret_cast<uint64_t>(saved.equipped))||
    std::memcmp(&snapshot_copy,&saved,sizeof(saved))||std::memcmp(params_copy,arguments,448))throw uncertain;
  }
  e33_character_restore_rules::Snapshot actual{};
  if(!context()||zone_ref(base,ids[1].address,"SkillGraphSystem")!=system||!object_skills(system,actual)||
   !e33_character_restore_rules::unlocked_equal(saved,actual.unlocked,actual.unlock_count)||actual.equip_count!=(e33_character_restore_rules::empty_loadout(saved)?saved.equip_count:e33_character_restore_rules::native_equipped_length(saved))||std::memcmp(actual.equipped,saved.equipped,actual.equip_count*8))throw uncertain;
  if(actual.equip_count<saved.equip_count){stage=12;alignas(8)uint8_t slot[16]{};const int last=int(saved.equip_count-1);std::memcpy(slot+8,&last,4);dispatch(system,5,slot);}
  actual={};if(!context()||zone_ref(base,ids[1].address,"SkillGraphSystem")!=system||!object_skills(system,actual)||actual.unlock_count!=saved.unlock_count||actual.equip_count!=saved.equip_count||std::memcmp(actual.unlocked,saved.unlocked,saved.unlock_count*8)||std::memcmp(actual.equipped,saved.equipped,saved.equip_count*8))throw uncertain;
  struct CosmeticOps{
   Dispatcher&owner_ref;uint64_t graph_system;
   bool read(e33_character_restore_rules::Appearance&out){return owner_ref.context()&&zone_ref(owner_ref.base,owner_ref.ids[1].address,"SkillGraphSystem")==graph_system&&owner_ref.read_appearance(out);}
   bool set(const e33_character_restore_rules::Appearance&value){
    std::memset(owner_ref.appearance_arguments,0,sizeof(owner_ref.appearance_arguments));std::memcpy(owner_ref.appearance_arguments,&value,sizeof(value));
    owner_ref.dispatch(owner_ref.ids[1].address,8,owner_ref.appearance_arguments);
    return !std::memcmp(owner_ref.appearance_arguments,&value,sizeof(value));
   }
   bool apply(){owner_ref.dispatch(owner_ref.ids[1].address,9,owner_ref.appearance_arguments);return true;}
  }cosmetics{*this,system};
  if(!e33_character_restore_rules::apply_appearance(cosmetics,selected_appearance,stage))throw uncertain;
  // Customization notifications must not have changed the preserved graph.
  actual={};if(!context()||zone_ref(base,ids[1].address,"SkillGraphSystem")!=system||!object_skills(system,actual)||actual.unlock_count!=saved.unlock_count||actual.equip_count!=saved.equip_count||std::memcmp(actual.unlocked,saved.unlocked,saved.unlock_count*8)||std::memcmp(actual.equipped,saved.equipped,saved.equip_count*8))throw uncertain;
  stage=20;unknown=false;done=true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(p.version!=5||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.stage||p.source||p.unlocked||p.equipped||p.guid[0]!=0xe33c5701U||!e33_character_graph::valid(p.profile)){p.error=rejected;return;}
  if(!e33_character_restore_rules::file_request(p.slot,p.file,p.file_count)){p.error=rejected;return;}
  for(auto v:p.tail)if(v){p.error=rejected;return;}
  if(p.mode){if(owner!=p.owner||session!=s||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(guid,p.guid,16)||std::memcmp(&profile,&p.profile,sizeof(profile))||selected_slot!=p.slot||selected_file_count!=p.file_count||std::memcmp(selected_file,p.file,sizeof(selected_file))){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   p.stage=stage;p.source=source;p.unlocked=saved.unlock_count;p.equipped=saved.equip_count;if(unknown||!done){p.error=uncertain;return;}p.state=2;return;
  }
  if(active()){p.error=unknown?uncertain:rejected;return;}
  for(unsigned i=0;i<count;++i)if(!call_identity(b,p.ids[i])||!p.leases[i]||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  base=b;session=s;profile=p.profile;std::memset(names,0,sizeof(names));std::memset(assets,0,sizeof(assets));std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,16);saved={};source=0;stage=0;current_appearance={};selected_appearance={};customization_struct=0;selected_slot=p.slot;selected_file_count=p.file_count;std::memcpy(selected_file,p.file,sizeof(selected_file));
  if(!e33_blueprint_names::resolve(b,profile.character,character_name)){p.error=rejected;return;}
  for(unsigned i=0;i<profile.count;++i)if(!e33_blueprint_names::resolve(b,profile.skills[i].id,names[i])){p.error=rejected;return;}
  stage=1;if(!context()){p.error=rejected;diagnostics(p);return;}
  stage=2;const auto role=picto_field(b,ids[1].address,"HardcodedNameID","NameProperty",48,8);
  if(!picto_class(b,ids[1].address,"BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData")||local_read<uint64_t>(ids[1].address+32)!=ids[0].address||!role||local_read<uint64_t>(role)!=character_name){p.error=rejected;diagnostics(p);return;}
  stage=3;if(!schemas()){p.error=rejected;diagnostics(p);return;}
  stage=4;if(!graph()){p.error=rejected;diagnostics(p);return;}
  stage=5;if(!snapshot()){p.error=rejected;diagnostics(p);return;}
  stage=6;if(!e33_character_restore_rules::valid(saved,names,profile.count)){p.error=rejected;diagnostics(p);return;}
  stage=7;if(e33_character_restore_rules::empty_loadout(saved)&&!empty_copy_property()){p.error=rejected;diagnostics(p);return;}
  owner=p.owner;try{restore();}catch(...){unknown=true;p.error=uncertain;diagnostics(p);return;}
  diagnostics(p);p.state=1;
 }
};
}
