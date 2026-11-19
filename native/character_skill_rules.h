#pragma once
#include "character_skill_config.h"
namespace e33_character_skill_rules {
struct Effect {double damage=0.,breaking=0.;uint8_t element=0;int buff=-1,duration=0;bool heal=false;};
inline bool qte_counts(int success,int fail,int perfect){return success>=0&&fail>=0&&perfect>=0&&success<=64&&fail<=64&&perfect<=64&&success+fail+perfect<=64;}
inline Effect effect(const e33_character_skill_config::Skill&s,int success,int perfect,bool last,bool charged,uint8_t weapon){
 const double qte=1.+s.qte_bonus*double(success+perfect);
 return {s.damage*qte*(charged?s.charged_multiplier:1.)*(last?s.final_multiplier:1.),s.breaking,uint8_t(s.element==256?weapon:s.element),(s.flags&512)&&!last?-1:s.buff,s.duration,(s.flags&128)!=0};
}
inline bool qualifies_meter(const e33_character_skill_config::Profile&p,bool own_source,uint8_t reason,double amount,uint64_t frame,int64_t previous){return p.meter_enabled&&(!p.own_only||own_source)&&reason<64&&(p.reason_mask&(1ULL<<reason))&&amount>0&&int64_t(frame)!=previous;}
inline int next_meter(const e33_character_skill_config::Profile&p,int previous){const unsigned next=unsigned(previous)+p.increment;return int(next>p.cap?p.cap:next);}
}
