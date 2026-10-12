#include "game_owned_cinematic_admission.h"
#include <cassert>
#include <iostream>
struct AdmissionOps {
    bool live=true,function=true,schema=true,constraint=true,asset=true;
    bool live_target()const{return live;}
    bool exact_function(GameOwnedCinematicCall)const{return function;}
    bool exact_schema(GameOwnedCinematicCall)const{return schema;}
    bool game_action_constraint(const CallIdentity&)const{return constraint;}
    bool original_scavenger(const CallIdentity&)const{return asset;}
};
int main() {
    CallPacket pause{};pause.version=1;pause.entry_rva=0x13937a0;pause.return_offset=65535;
    pause.allocation_extent=16;pause.function_flags=0xc840000;pause.target={1,2,0x1000};pause.function={3,4,0x2000};
    CallPacket execute=pause;execute.function_flags=0xc020000;execute.parameter_size=8;
    execute.field_count=execute.object_count=1;
    execute.fields[0].kind=CallObject;execute.fields[0].width=8;execute.fields[0].dimension=1;
    execute.fields[0].constraint={5,6,0x3000};execute.fields[0].flags=0x8001000000294ULL;strcpy_s(execute.fields[0].name,"GameAction");
    execute.objects[0].identity={17,29,0x1000};
    assert(validate_call_packet(pause)==0&&validate_call_packet(execute)==0);
    AdmissionOps ops;
#ifndef E33_GAME_OWNED_CINEMATIC_SESSION
    assert(!admit_game_owned_cinematic(ops,pause));assert(!admit_game_owned_cinematic(ops,execute));
#else
    assert(admit_game_owned_cinematic(ops,pause));assert(admit_game_owned_cinematic(ops,execute));
    for(unsigned i=0;i<9;++i) {
        auto bad=execute;
        switch(i) {case 0:bad.function_flags^=1;break;case 1:bad.entry_rva++;break;case 2:bad.allocation_extent=8;break;
         case 3:bad.parameter_size=16;break;case 4:bad.object_count=0;break;case 5:bad.fields[0].flags^=1;break;
         case 6:bad.fields[0].name[0]='X';break;case 7:bad.data[0]=1;break;case 8:bad.fields[0].kind=CallClass;break;}
        assert(!admit_game_owned_cinematic(ops,bad));
    }
    for(unsigned i=0;i<5;++i) {
        AdmissionOps bad;
        switch(i){case 0:bad.live=false;break;case 1:bad.function=false;break;case 2:bad.schema=false;break;
         case 3:bad.constraint=false;break;case 4:bad.asset=false;break;}
        assert(!admit_game_owned_cinematic(bad,execute));
    }
    {auto bad=pause;bad.field_count=1;assert(!admit_game_owned_cinematic(ops,bad));}
    {auto bad=pause;bad.object_count=1;assert(!admit_game_owned_cinematic(ops,bad));}
#endif
    std::cout<<"Narrow game-owned Blueprint admission fixtures passed\n";
}
