#pragma once
#include <cstdint>
// Exact known executable/asset profile. Ops supplies guarded target reads.
namespace e33_battle_completion {
template<class Ops> bool completion_schema(Ops& o,uint64_t function,uint64_t controller,bool worldmap){
 if(!o.live(function)||!o.live(controller)||!o.named(function+24,"ResumeExplorationOnBattleEnd"))return false;
 const auto owner=o.template read<uint64_t>(function+32),cls=o.template read<uint64_t>(controller+16);
 const char* name=worldmap?"BP_PlayerController_WorldMap_C":"BP_jRPG_Controller_World_C";
 const char* package=worldmap?"/Game/Gameplay/WorldMap/BP_PlayerController_WorldMap":"/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Controller_World";
 if(owner!=cls||!o.is_class(owner)||!o.object_name(owner,name,package)||
    o.template read<uint32_t>(function+0xb0)!=(worldmap?0x0c020000U:0x0c820000U)||
    o.template read<uint16_t>(function+0xb6)!=9||o.template read<uint16_t>(function+0xb8)!=65535||
    o.template read<uint32_t>(function+0x58)!=(worldmap?9U:128U)||
    o.template read<uint64_t>(function+0xd8)!=o.base+0x13937a0)return false;
 unsigned params=0,count=0;auto p=o.template read<uint64_t>(function+0x50);
 for(;p&&count<128;++count,p=o.template read<uint64_t>(p+0x18)){
  if(o.template read<uint64_t>(p+0x10)!=(function|1))return false;
  const auto flags=o.template read<uint64_t>(p+0x38);if(!(flags&0x80))continue;
  if(params>=2||flags!=0x8001040000294ULL||o.template read<uint32_t>(p+0x30)!=1)return false;
  const bool name_param=params==0;
  if(!o.named(p+0x20,name_param?"EnemyGlobalID":"BattleEndResult")||
     !o.named(o.template read<uint64_t>(p+8),name_param?"NameProperty":"ByteProperty")||
     o.template read<uint64_t>(p)!=o.base+(name_param?0x6e13040ULL:0x6e10420ULL)||
     o.template read<uint32_t>(p+0x34)!=(name_param?8U:1U)||
     o.template read<uint32_t>(p+0x44)!=(name_param?0U:8U))return false;
  if(!name_param){
   const auto enumeration=o.template read<uint64_t>(p+0x70);
   if(!o.object_name(enumeration,"EBattleEndResult","/Game/Gameplay/Battle/EBattleEndResult"))return false;
   const auto data=o.template read<uint64_t>(enumeration+0x40);
   const auto member_count=o.template read<int32_t>(enumeration+0x48),capacity=o.template read<int32_t>(enumeration+0x4c);
   if(!data||member_count!=5||capacity<member_count||capacity>16)return false;
   const char* members[]={"EBattleEndResult::NewEnumerator0","EBattleEndResult::NewEnumerator1",
     "EBattleEndResult::NewEnumerator2","EBattleEndResult::NewEnumerator3","EBattleEndResult::EBattleEndResult_MAX"};
   for(unsigned i=0;i<5;++i)if(!o.named(data+i*16,members[i])||o.template read<int64_t>(data+i*16+8)!=i)return false;
  }
  ++params;
 }
 return !p&&params==2&&count==(worldmap?2U:18U);
}
}
