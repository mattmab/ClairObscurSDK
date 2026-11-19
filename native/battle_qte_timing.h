#pragma once
#include "battle_qte_profile.h"
namespace e33_battle_qte_timing {
enum class Result {Ready,TooLate,Invalid};
struct Window {double start=0.,anticipation=0.,validity=0.,now=0.;};
// Preserve the full input interval; a late declaration can consume only anticipation.
inline Result plan(double now,double asset,const e33_battle_qte::Profile&p,Window(&windows)[16]){
 if(!e33_battle_qte::valid(p)||!std::isfinite(now)||!std::isfinite(asset)||now<0||now>1e9||asset<-.1||asset>3600)return Result::Invalid;
 Window staged[16]{};
 for(unsigned i=0;i<p.count;++i){const double until_start=p.impacts[i]-asset-p.validity;if(until_start<=p.lead)return Result::TooLate;const double remaining=until_start-p.lead;staged[i]={now+until_start,remaining<p.anticipation?remaining:p.anticipation,p.validity,now};}
 for(unsigned i=0;i<p.count;++i)windows[i]=staged[i];return Result::Ready;
}
}
