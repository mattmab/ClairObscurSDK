#pragma once
#include "wardrobe_config.h"
namespace e33_battle_qte {
#pragma pack(push,1)
struct Profile {char paths[3][384]{};uint32_t count=0;double impacts[16]{},validity=0,anticipation=0,lead=0,bonus_per_input=0;uint32_t damage_reason=0;};
#pragma pack(pop)
static_assert(sizeof(Profile)==1320);
inline bool valid(const Profile&p){
 for(unsigned i=0;i<3;++i)if(!e33_wardrobe_config::valid_path(p.paths[i],i>0))return false;
 if(!p.count||p.count>16||!std::isfinite(p.validity)||p.validity<=0||p.validity>10||!std::isfinite(p.anticipation)||p.anticipation<0||p.anticipation>10||!std::isfinite(p.lead)||p.lead<=0||p.lead>1||!std::isfinite(p.bonus_per_input)||p.bonus_per_input<0||p.bonus_per_input>10||p.damage_reason>255)return false;
 for(unsigned i=0;i<16;++i){if(i>=p.count){if(p.impacts[i]!=0||std::signbit(p.impacts[i]))return false;}else if(!std::isfinite(p.impacts[i])||p.impacts[i]<=0||p.impacts[i]>3600||(i&&p.impacts[i]<=p.impacts[i-1]))return false;}return true;
}
}
