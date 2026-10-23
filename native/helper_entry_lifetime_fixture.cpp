#include "helper_entry_lifetime.h"
#include "helper_parameter_anchor.h"
#include "helper_source_frame.h"
#include <limits>
#include <cassert>
#include <cstdio>
int main(){
    using namespace e33_enemy_spawn;
    struct Possession{
        bool source=true,pawn=true;unsigned source_reads=0,pawn_reads=0;
        bool source_current(){++source_reads;return source;}
        bool pawn_current(){++pawn_reads;return source&&pawn;}
    } possession;
    assert(helper_entry_source_context(possession,true));
    possession.pawn=false; // mounted or transiently unpossessed
    assert(helper_entry_source_context(possession,true));
    assert(possession.source_reads==2&&possession.pawn_reads==0);
    assert(!helper_entry_source_context(possession,false)); // ordinary enemy unchanged
    possession.pawn=true; // dismounted
    assert(helper_entry_source_context(possession,true));
    possession.source=false; // retained world/controller no longer valid
    assert(!helper_entry_source_context(possession,true));
    assert(!helper_entry_source_context(possession,false));
    const double sine=std::sqrt(.5);
    double arena[12]={0,0,sine,sine,1000000,2000000,300,0,1,1,1,0};
    double local[12]={0,0,0,1,10,20,-15000,0,1,1,1,0},composed[12]{};
    assert(compose_helper_source_frame(arena,local,composed));
    assert(std::abs(composed[4]-999980)<.00001&&std::abs(composed[5]-2000010)<.00001&&composed[6]==-14700);
    double same[12];std::memcpy(same,composed,sizeof(same));
    for(unsigned i=0;i<4;++i)same[i]=-same[i];assert(same_helper_world_frame(same,composed));
    same[4]+=.2;assert(!same_helper_world_frame(same,composed));
    local[8]=2;assert(!compose_helper_source_frame(arena,local,composed));local[8]=1;
    local[0]=sine;local[3]=sine;assert(!compose_helper_source_frame(arena,local,composed));
    local[0]=0;local[3]=1;local[4]=std::numeric_limits<double>::quiet_NaN();
    assert(!compose_helper_source_frame(arena,local,composed));
    HelperParameterAnchorProof admitted{true,true,true,false,true,true,true};
    assert(helper_parameter_anchor_admitted(admitted));
    auto rejected=admitted;rejected.owned_identity=false;assert(!helper_parameter_anchor_admitted(rejected));
    rejected=admitted;rejected.current_context=false;assert(!helper_parameter_anchor_admitted(rejected));
    rejected=admitted;rejected.original_helper=false;assert(!helper_parameter_anchor_admitted(rejected));
    rejected=admitted;rejected.arena=true;assert(!helper_parameter_anchor_admitted(rejected));
    rejected=admitted;rejected.prepared=false;assert(!helper_parameter_anchor_admitted(rejected));
    rejected=admitted;rejected.construction_complete=false;assert(!helper_parameter_anchor_admitted(rejected));
    rejected=admitted;rejected.battle_quiescent=false;assert(!helper_parameter_anchor_admitted(rejected));
    HelperEntryLifetime state;
    assert(state.ready()&&!state.pending()&&!state.begin(0));
    assert(state.begin(123)&&state.name()==123&&state.pending()&&!state.ready());
    assert(!state.begin(456)&&state.name()==123);
    for(unsigned i=0;i<100;++i){state.observe(false,true);assert(!state.ready());}
    state.observe(false,false);assert(state.phase()==HelperEntryPhase::AwaitingActive);
    state.observe(true,false);assert(state.phase()==HelperEntryPhase::ActiveSeen&&!state.ready());
    state.observe(true,true);assert(state.phase()==HelperEntryPhase::ActiveSeen&&!state.ready());
    state.observe(false,false);assert(!state.ready());
    state.observe(false,true);assert(state.ready()&&!state.pending());
    assert(!state.begin(789));state.observe(true,false);assert(state.phase()==HelperEntryPhase::Retired);
    HelperEntryLifetime fresh;fresh.observe(true,true);assert(fresh.ready()&&fresh.phase()==HelperEntryPhase::Empty);
    puts("Helper entry lifetime fixture passed: startup idle cannot retire, no timeout/replay, own activity then idle, contradictory/unknown evidence retained.");
}
