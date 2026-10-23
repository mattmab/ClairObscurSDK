#include "battle_parameter_frame.h"
#include "battle_parameter_arena.h"
#include <cassert>
#include <stdexcept>
#include <type_traits>
using namespace e33_enemy_spawn;
struct Ops {
    ParameterCall init=ParameterCall::Completed,assign=ParameterCall::Completed,retire=ParameterCall::Completed;
    bool valid=true,ready=true,throw_init=false,throw_copy=false,throw_destroy=false;
    unsigned checks=0,initializations=0,copies=0,destructions=0;
    bool fail_second=false;
    bool preflight(){return valid && !(++checks==2 && fail_second);}
    bool cleanup_ready(){return ready;}
    ParameterCall initialize(void* p){assert(reinterpret_cast<uintptr_t>(p)%8==0);++initializations;if(throw_init)throw std::runtime_error("init unknown");return init;}
    ParameterCall copy(void*){++copies;if(throw_copy)throw std::runtime_error("copy unknown");return assign;}
    ParameterCall destroy(void*){++destructions;if(throw_destroy)throw std::runtime_error("destroy unknown");return retire;}
};
struct PolicyOps {
    ParameterCall result=ParameterCall::Completed;bool throws=false;unsigned calls=0;
    ParameterCall apply(void*){++calls;if(throws)throw std::runtime_error("policy unknown");return result;}
};
struct ArenaOps {
    ParameterCall result=ParameterCall::Completed;bool throws=false;unsigned calls=0;
    ParameterCall bind(void*){++calls;if(throws)throw std::runtime_error("arena unknown");return result;}
};
int main(){
    {
        std::array<uint8_t,40> soft{};
        assert(empty_battle_arena_soft_value(soft.data()));assert(!empty_battle_arena_soft_value(nullptr));
        for(unsigned i=0;i<8;++i)soft[i]=0xff;
        assert(empty_battle_arena_soft_value(soft.data()));
        for(unsigned i=8;i<40;++i){auto authored=soft;authored[i]=1;assert(!empty_battle_arena_soft_value(authored.data()));}
    }
    for(const auto outcome:{ParameterCall::Completed,ParameterCall::NotDispatched,ParameterCall::Unknown}){
        BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));ArenaOps arena;arena.result=outcome;
        assert(f.bind_arena(arena)==(outcome==ParameterCall::Completed));assert(!f.bind_arena(arena));assert(arena.calls==1);
        if(outcome==ParameterCall::Unknown){assert(f.quarantined());assert(!f.copied_data());assert(!f.close(o));assert(o.destructions==0);}
        else{
            assert(f.state()==(outcome==ParameterCall::Completed?ParameterFrameState::ArenaBound:ParameterFrameState::Copied));
            PolicyOps policy;assert(f.apply_policy(policy));assert(f.state()==ParameterFrameState::PolicyApplied);assert(f.close(o));
        }
    }
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));ArenaOps arena;arena.throws=true;try{f.bind_arena(arena);assert(false);}catch(const std::runtime_error&){}assert(f.quarantined());assert(!f.close(o));assert(!f.bind_arena(arena));}
    {BattleParameterFrame f;ArenaOps arena;assert(!f.bind_arena(arena));assert(arena.calls==0);}
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));ArenaOps arena;assert(f.bind_arena(arena));PolicyOps policy;policy.result=ParameterCall::NotDispatched;assert(!f.apply_policy(policy));assert(f.state()==ParameterFrameState::ArenaBound);assert(f.close(o));}
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));PolicyOps policy;assert(f.apply_policy(policy));ArenaOps arena;assert(!f.bind_arena(arena));assert(arena.calls==0);assert(f.close(o));}
    for(const auto outcome:{ParameterCall::Completed,ParameterCall::NotDispatched,ParameterCall::Unknown}){
        BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));PolicyOps p;p.result=outcome;
        assert(f.apply_policy(p)==(outcome==ParameterCall::Completed));assert(!f.apply_policy(p));assert(p.calls==1);
        if(outcome==ParameterCall::Unknown){assert(f.quarantined());assert(!f.copied_data());assert(!f.close(o));assert(o.destructions==0);}
        else {assert(f.copied_data());assert(f.state()==(outcome==ParameterCall::Completed?ParameterFrameState::PolicyApplied:ParameterFrameState::Copied));assert(f.close(o));}
    }
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));PolicyOps p;p.throws=true;try{f.apply_policy(p);assert(false);}catch(const std::runtime_error&){}assert(f.quarantined());assert(!f.close(o));assert(!f.apply_policy(p));}
    {BattleParameterFrame f;PolicyOps p;assert(!f.apply_policy(p));assert(p.calls==0);}
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));assert(f.close(o));PolicyOps p;assert(!f.apply_policy(p));assert(p.calls==0);}
    {const uint64_t source=0x1000;
     assert(!parameter_destination_separate(0,source));
     assert(!parameter_destination_separate(source+48,source));
     assert(!parameter_destination_separate(source+40,source));
     assert(!parameter_destination_separate(source+384,source));
     assert(!parameter_destination_separate(source+393,source));
     assert(parameter_destination_separate(source+392,source));
     assert(parameter_destination_separate(source+48-344,source));
     assert(!parameter_destination_separate(std::numeric_limits<uintptr_t>::max()-7,source));
     assert(!parameter_destination_separate(0x1000,std::numeric_limits<uint64_t>::max()-7));}
    static_assert(!std::is_copy_constructible_v<BattleParameterFrame>);
    static_assert(!std::is_move_constructible_v<BattleParameterFrame>);
    {BattleParameterFrame f;Ops o;assert(!f.copied_data());assert(f.initialize_copy(o));assert(f.copied_data());assert(!f.initialize_copy(o));assert(f.close(o));assert(f.close(o));assert(o.initializations==1&&o.copies==1&&o.destructions==1);}
    {BattleParameterFrame f;Ops o;o.valid=false;assert(!f.initialize_copy(o));assert(!f.attempted());assert(o.initializations==0);assert(f.close(o));}
    {BattleParameterFrame f;Ops o;o.init=ParameterCall::NotDispatched;assert(!f.initialize_copy(o));assert(!f.initialize_copy(o));assert(o.initializations==1&&o.copies==0);assert(f.close(o));assert(o.destructions==0);}
    {BattleParameterFrame f;Ops o;o.init=ParameterCall::Unknown;assert(!f.initialize_copy(o));assert(f.quarantined());assert(!f.close(o));assert(!f.initialize_copy(o));assert(o.destructions==0);}
    {BattleParameterFrame f;Ops o;o.fail_second=true;assert(!f.initialize_copy(o));assert(f.state()==ParameterFrameState::Initialized);assert(o.copies==0);assert(f.close(o));}
    {BattleParameterFrame f;Ops o;o.assign=ParameterCall::NotDispatched;assert(!f.initialize_copy(o));assert(f.state()==ParameterFrameState::Initialized);assert(f.close(o));assert(o.destructions==1);}
    {BattleParameterFrame f;Ops o;o.assign=ParameterCall::Unknown;assert(!f.initialize_copy(o));assert(f.quarantined());assert(!f.close(o));assert(o.destructions==0);}
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));o.ready=false;assert(!f.close(o));assert(o.destructions==0);o.ready=true;assert(f.close(o));}
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));o.retire=ParameterCall::NotDispatched;assert(!f.close(o));assert(f.state()==ParameterFrameState::Copied);o.retire=ParameterCall::Completed;assert(f.close(o));}
    {BattleParameterFrame f;Ops o;assert(f.initialize_copy(o));o.retire=ParameterCall::Unknown;assert(!f.close(o));assert(f.quarantined());assert(!f.close(o));assert(o.destructions==1);}
    for(unsigned stage=0;stage<3;++stage){BattleParameterFrame f;Ops o;o.throw_init=stage==0;o.throw_copy=stage==1;try{assert(f.initialize_copy(o));if(stage==2){o.throw_destroy=true;f.close(o);}}catch(const std::runtime_error&){}assert(f.quarantined());assert(!f.close(o));assert(!f.initialize_copy(o));}
    return 0;
}
