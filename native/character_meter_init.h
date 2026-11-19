#pragma once
#include <cstdint>
namespace e33_character_meter_init {
enum class Origin : uint8_t { BattleStart, Damage };
enum class Stage : uint8_t { Empty, Parent, SelectState, Spawn, LinkUI, Activate, LinkState, ResetUI, ForwardDamage, Complete };
struct Journal {
 Origin origin=Origin::BattleStart;Stage stage=Stage::Empty;
 bool active()const{return stage!=Stage::Empty&&stage!=Stage::Complete;}
};
// Ops holds the exact actor/component/stats and any created state. Journal the
// next side effect before dispatch; an exception leaves that record unresolved.
// The caller quarantines its owner and retains all leases instead of replaying.
template<class Ops>void run(Journal&journal,Ops&ops,Origin origin){
 if(journal.stage!=Stage::Empty)throw uint32_t(4288);
 journal.origin=origin;
 auto before=[&](Stage stage){if(!ops.context())throw uint32_t(4288);journal.stage=stage;};
 auto finish=[&](){if(!ops.context())throw uint32_t(4288);journal.stage=Stage::Complete;};
 if(origin==Origin::BattleStart){before(Stage::Parent);ops.parent();}
 before(Stage::SelectState);
 bool state=origin==Origin::Damage&&ops.existing();
 if(!state){
  before(Stage::Spawn);state=ops.spawn();
  if(state){
   before(Stage::LinkUI);ops.link_ui();
   before(Stage::Activate);state=ops.activate();
   if(state){before(Stage::LinkState);ops.link_state();}
  }
 }
 if(origin==Origin::BattleStart){before(Stage::ResetUI);ops.reset_ui();}
 else if(state){before(Stage::ForwardDamage);ops.forward();}
 finish();
}
}
