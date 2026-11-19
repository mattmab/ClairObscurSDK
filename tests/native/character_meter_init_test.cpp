#include <cassert>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "character_meter_init.h"
using namespace e33_character_meter_init;
struct Ops {
 bool bound=true,has_state=false,spawned=true,activated=true;
 unsigned parent_count=0;std::string failure,unbind_after;std::vector<std::string>calls;
 bool context()const{return bound;}
 void call(const char*name){calls.emplace_back(name);if(failure==name)throw uint32_t(999);if(unbind_after==name)bound=false;}
 void parent(){++parent_count;call("parent");}
 bool existing(){call("existing");return has_state;}
 bool spawn(){call("spawn");return spawned;}
 void link_ui(){call("link_ui");}
 bool activate(){call("activate");return activated;}
 void link_state(){call("link_state");}
 void reset_ui(){call("reset_ui");}
 void forward(){call("forward");}
};
int main(int argc,char**argv){
 if(argc==5){
  Ops ops;ops.has_state=std::string(argv[2])=="existing";ops.spawned=std::string(argv[3])=="spawn";ops.activated=std::string(argv[4])=="activate";
  Journal journal;run(journal,ops,std::string(argv[1])=="battle"?Origin::BattleStart:Origin::Damage);
  for(const auto&call:ops.calls)std::cout<<call<<'\n';return 0;
 }
 assert(argc==1);
 {
  Ops ops;Journal journal;run(journal,ops,Origin::BattleStart);
  assert((ops.calls==std::vector<std::string>{"parent","spawn","link_ui","activate","link_state","reset_ui"}));
  assert(ops.parent_count==1&&journal.stage==Stage::Complete);
  bool denied=false;try{run(journal,ops,Origin::BattleStart);}catch(uint32_t){denied=true;}assert(denied&&ops.parent_count==1);
 }
 {
  Ops ops;ops.has_state=true;Journal journal;run(journal,ops,Origin::Damage);
  assert((ops.calls==std::vector<std::string>{"existing","forward"}));assert(!ops.parent_count);
 }
 {
  Ops ops;Journal journal;run(journal,ops,Origin::Damage);
  assert((ops.calls==std::vector<std::string>{"existing","spawn","link_ui","activate","link_state","forward"}));
 }
 for(auto origin:{Origin::BattleStart,Origin::Damage})for(bool spawn_fail:{false,true}){
  Ops ops;ops.spawned=!spawn_fail;ops.activated=false;Journal journal;run(journal,ops,origin);
  assert(journal.stage==Stage::Complete);
  for(const auto&call:ops.calls)assert(call!="link_state"&&call!="forward");
  if(origin==Origin::BattleStart)assert(ops.calls.back()=="reset_ui"&&ops.parent_count==1);
 }
 for(auto origin:{Origin::BattleStart,Origin::Damage}){
  Ops baseline;Journal reference;run(reference,baseline,origin);
  for(const auto&step:baseline.calls){
   Ops ops;ops.failure=step;Journal journal;bool failed=false;
   try{run(journal,ops,origin);}catch(uint32_t){failed=true;}
   assert(failed&&journal.active());const auto count=ops.calls.size();
   try{run(journal,ops,origin);}catch(uint32_t){}assert(ops.calls.size()==count&&ops.parent_count<=1);
  }
  for(const auto&step:baseline.calls){
   Ops ops;ops.unbind_after=step;Journal journal;bool failed=false;
   try{run(journal,ops,origin);}catch(uint32_t){failed=true;}assert(failed&&journal.active());
   assert(ops.calls.back()==step&&ops.parent_count<=1);
  }
 }
 {Ops ops;ops.bound=false;Journal journal;bool failed=false;try{run(journal,ops,Origin::BattleStart);}catch(uint32_t){failed=true;}assert(failed&&ops.calls.empty());}
}
