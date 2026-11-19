#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include "battle_qte_timing.h"
using namespace e33_battle_qte_timing;
template<size_t N>void text(char(&out)[N],const char*value){assert(std::strlen(value)<N);std::memset(out,0,N);std::memcpy(out,value,std::strlen(value));}
static bool near(double a,double b){return std::abs(a-b)<1e-9;}
int main(){
 e33_battle_qte::Profile p;text(p.paths[0],"/Game/SDK/Sample/Sequence.Sequence");text(p.paths[1],"/Game/SDK/Sample/Character.Character_C");text(p.paths[2],"/Game/SDK/Sample/Skill.Skill_C");p.validity=.2;p.anticipation=.4;p.lead=.01;p.bonus_per_input=.15;p.damage_reason=1;
 for(unsigned n:{1U,4U,16U}){
  p.count=n;std::memset(p.impacts,0,sizeof(p.impacts));for(unsigned i=0;i<n;++i)p.impacts[i]=1.5+i;
  for(double now:{0.,.02,10000.})for(double asset:{0.,.5,1.,1.2}){
   Window windows[16]{};assert(plan(now,asset,p,windows)==Result::Ready);
   for(unsigned i=0;i<n;++i){const auto&w=windows[i];assert(w.start-w.anticipation>now);assert(w.anticipation>0.&&w.anticipation<=p.anticipation);assert(near(w.validity,p.validity));assert(near(w.start+w.validity-now+asset,p.impacts[i]));}
  }
  Window late[16]{};late[0].start=777;assert(plan(0,1.4,p,late)==Result::TooLate);assert(late[0].start==777);assert(plan(0,.5,p,late)==Result::Ready);
 }
 for(double invalid:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-1.,1e12}){Window windows[16]{};assert(plan(invalid,.5,p,windows)==Result::Invalid);assert(plan(0.,invalid,p,windows)==Result::Invalid);}
 p.impacts[1]=p.impacts[0];assert(!e33_battle_qte::valid(p));
 std::cout<<"Configured QTE nominal, frame hitch, past-window and clock checks passed\n";
}
