#pragma once
#include "wardrobe_config.h"
namespace e33_character_skill_config {
inline constexpr unsigned dynamic[]={19,20,21,22,29,30,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,75,77};
inline constexpr unsigned kinds[]={2,2,2,1,1,1,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,0,2,2}; // 0 asset, 1 class, 2 function
#pragma pack(push,1)
struct Skill {uint32_t flags=0,element=0;int32_t buff=-1,duration=0;uint32_t cleanse_kind=0,damage_reason=0,buff_reason=0,reserved=0;double distance=0,initiative=0,damage=0,breaking=0,qte_bonus=0,charged_multiplier=0,final_multiplier=0,heal_threshold=0,heal_fraction=0,recovery_fraction=0;char16_t debug_reason[64]{};};
struct Profile {char paths[44][320]{};uint32_t count=0,meter_enabled=0,increment=0,cap=0,reset=0,buff_mask=0,own_only=0;uint64_t reason_mask=0;Skill skills[9]{};};
#pragma pack(pop)
static_assert(sizeof(Skill)==240);static_assert(sizeof(Profile)==16276);
inline bool active(unsigned i,unsigned count,bool meter){return (((i<19||i>22)&&i!=30&&i!=75&&i!=77)||meter)&&(!(i>=38&&i<74)||(i-38)/4<count);}
inline const char* path(const Profile&p,unsigned i,const char*fallback){for(unsigned k=0;k<44;++k)if(dynamic[k]==i)return p.paths[k];return fallback;}
inline bool valid_path(const char(&value)[320],unsigned kind){
 size_t n=0;for(;n<320&&value[n];++n){}if(!n||n==320)return false;for(size_t i=n;i<320;++i)if(value[i])return false;
 char copied[384]{};std::memcpy(copied,value,n);char*colon=std::strchr(copied,':');
 if(bool(colon)!=(kind==2))return false;if(colon){const char*name=colon+1;char method[96]{};size_t length=std::strlen(name);if(length>=96)return false;std::memcpy(method,name,length);if(!e33_character_graph::identifier(method))return false;*colon=0;std::memset(colon+1,0,383-size_t(colon-copied));}
 return e33_wardrobe_config::valid_path(copied,kind!=0);
}
inline bool valid(const Profile&p){
 if(!p.count||p.count>9||p.meter_enabled>1||p.own_only>1)return false;
 if(p.meter_enabled){if(!p.increment||p.increment>p.cap||p.cap>10000||p.reset>p.cap||!p.buff_mask||p.buff_mask>127||!p.reason_mask)return false;}
 else if(p.increment||p.cap||p.reset||p.buff_mask||p.own_only||p.reason_mask)return false;
 for(unsigned i=0;i<44;++i){if(active(dynamic[i],p.count,p.meter_enabled)){if(!valid_path(p.paths[i],kinds[i]))return false;}else for(auto c:p.paths[i])if(c)return false;}
 for(unsigned i=0;i<9;++i){const auto&s=p.skills[i];if(i>=p.count){const uint8_t*raw=reinterpret_cast<const uint8_t*>(&s);for(unsigned j=0;j<240;++j)if(raw[j])return false;continue;}
  if(s.flags>2047||s.element>256||s.buff< -1||s.buff>6||s.duration<0||s.duration>999||s.cleanse_kind>255||s.damage_reason>255||s.buff_reason>255||s.reserved)return false;
  const double numbers[]={s.distance,s.initiative,s.damage,s.breaking,s.qte_bonus,s.charged_multiplier,s.final_multiplier,s.heal_threshold,s.heal_fraction,s.recovery_fraction};for(auto x:numbers)if(!std::isfinite(x)||x<0||x>1e4)return false;
  if(s.heal_threshold>1||s.heal_fraction>1||s.recovery_fraction>1)return false;
  unsigned j=0;for(;j<64&&s.debug_reason[j];++j){const auto c=s.debug_reason[j];if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'))return false;}if(!j||j==64)return false;for(;j<64;++j)if(s.debug_reason[j])return false;
 }return true;
}
}
