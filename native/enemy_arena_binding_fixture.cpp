#include "enemy_arena_binding.h"
#include <cstdio>
#include <cstdlib>
#include <string>
using namespace e33_enemy_spawn;
struct Ops {
    bool ready=true,dependencies=true,conversion=true,assignment=true,verification=true,cleanup=true;
    std::string events;
    bool preflight(){events+='p';return ready;}
    bool dependencies_supported(){events+='d';return dependencies;}
    bool convert(){events+='c';return conversion;}
    bool assign(){events+='a';return assignment;}
    bool verify(){events+='v';return verification;}
    bool clear_temporary(){events+='x';return cleanup;}
};
int main(){
    unsigned tests=0;
    auto check=[&](bool value){++tests;if(!value){std::fprintf(stderr,"arena binding check %u failed\n",tests);std::exit(1);}};
    {
        CallIdentity arena{12,0,0x20000};
        check(adopt_converted_arena_identity(arena,{12,1200,0x20000})&&arena.serial==1200);
        check(adopt_converted_arena_identity(arena,{12,1200,0x20000}));
        check(!adopt_converted_arena_identity(arena,{12,1201,0x20000})&&arena.serial==1200);
        check(!adopt_converted_arena_identity(arena,{13,1200,0x20000}));
        check(!adopt_converted_arena_identity(arena,{12,1200,0x30000}));
        check(!adopt_converted_arena_identity(arena,{12,0,0x20000}));
        CallIdentity unassigned{12,0,0x20000};
        check(!adopt_converted_arena_identity(unassigned,{12,0,0x20000})&&unassigned.serial==0);
        check(!adopt_converted_arena_identity(unassigned,{12,1000,0x20000})&&unassigned.serial==0);
    }
    {
        Ops ops;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::Ok);
        check(ops.events=="pdcavx"&&state.attempted&&state.assigned&&state.verified&&!state.temporary_live);
        check(bind_owned_arena(ops,state)==ArenaBindingResult::AlreadyAttempted&&ops.events=="pdcavx");
        check(close_arena_binding_temporary(ops,state)&&ops.events=="pdcavx");
    }
    {
        Ops ops;ops.ready=false;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::PreflightRejected);
        check(ops.events=="p"&&!state.attempted&&!state.temporary_live);
    }
    {
        Ops ops;ops.dependencies=false;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::AuthoredDependenciesUnresolved);
        check(ops.events=="pd"&&!state.attempted&&!state.assigned);
    }
    {
        Ops ops;ops.conversion=false;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::ConversionFailed);
        check(ops.events=="pdcx"&&state.attempted&&!state.temporary_live&&!state.assigned);
    }
    {
        Ops ops;ops.assignment=false;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::AssignmentFailed);
        check(ops.events=="pdcax"&&!state.verified&&!state.temporary_live);
    }
    {
        Ops ops;ops.verification=false;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::VerificationFailed);
        check(ops.events=="pdcavx"&&state.assigned&&!state.verified);
    }
    {
        Ops ops;ops.cleanup=false;ArenaBindingState state;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::TemporaryCleanupFailed);
        check(state.temporary_live&&state.assigned&&state.verified);
        check(!close_arena_binding_temporary(ops,state)&&state.temporary_live);
        ops.cleanup=true;check(close_arena_binding_temporary(ops,state)&&!state.temporary_live);
        const auto events=ops.events;
        check(bind_owned_arena(ops,state)==ArenaBindingResult::AlreadyAttempted&&ops.events==events);
    }
    std::printf("%u arena binding checks passed\n",tests);return 0;
}
