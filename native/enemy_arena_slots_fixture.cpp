#include "enemy_arena_slots.h"
#include <cstdio>
#include <cstdlib>
using namespace e33_enemy_spawn;
int main(){
    unsigned tests=0;
    auto check=[&](bool value){++tests;if(!value){std::fprintf(stderr,"arena slot check %u failed\n",tests);std::exit(1);}};
    // Actual observed order in both original QA assemblies, not name suffixes.
    ArenaSlotEvidence slots[]={
        {0,true,true,true,true,false},{3,true,true,true,true,false},
        {2,true,true,true,true,false},{1,true,true,true,true,false},
        {2,false,true,true,true,true},{0,false,true,true,true,true},
        {1,false,true,true,true,true}};
    auto observed=validate_arena_slots(slots,7,15,7,true);
    check(observed.result==ArenaSlotsResult::Ok&&observed.enemy_mask==15&&observed.party_mask==7);
    check(validate_arena_slots(nullptr,0,0,0,false).result==ArenaSlotsResult::Ok);
    check(validate_arena_slots(nullptr,1,0,0,false).result==ArenaSlotsResult::InvalidInput);
    check(validate_arena_slots(slots,129,0,0,false).result==ArenaSlotsResult::InvalidInput);
    check(validate_arena_slots(slots,7,31,7,true).result==ArenaSlotsResult::MissingRequiredSlot);
    slots[1].index=0;check(validate_arena_slots(slots,7,0,0,false).result==ArenaSlotsResult::DuplicateIndex);slots[1].index=3;
    slots[0].index=-1;check(validate_arena_slots(slots,7,0,0,false).result==ArenaSlotsResult::InvalidIndex);
    slots[0].index=64;check(validate_arena_slots(slots,7,0,0,false).result==ArenaSlotsResult::InvalidIndex);slots[0].index=0;
    slots[0].reference_valid=false;check(validate_arena_slots(slots,7,0,0,false).result==ArenaSlotsResult::InvalidReference);slots[0].reference_valid=true;
    slots[0].position_valid=false;check(validate_arena_slots(slots,7,0,0,false).result==ArenaSlotsResult::MissingPosition);slots[0].position_valid=true;
    slots[0].front_arrow_valid=false;check(validate_arena_slots(slots,7,0,0,false).result==ArenaSlotsResult::MissingOrientation);slots[0].front_arrow_valid=true;
    slots[4].back_arrow_valid=false;
    check(validate_arena_slots(slots,7,15,7,false).result==ArenaSlotsResult::Ok);
    check(validate_arena_slots(slots,7,15,7,true).result==ArenaSlotsResult::MissingOrientation);
    slots[4].back_arrow_valid=true;slots[0].index=63;
    observed=validate_arena_slots(slots,7,uint64_t(1)<<63,7,true);
    check(observed.result==ArenaSlotsResult::Ok&&(observed.enemy_mask&(uint64_t(1)<<63)));
    std::printf("%u arena slot checks passed\n",tests);return 0;
}
