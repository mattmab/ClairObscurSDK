#pragma once
#include <cstddef>
#include <cstdint>

namespace e33_enemy_spawn {
// A collector must validate exact original class ancestry, lifetime, world and
// ownership before setting reference_valid. This helper never reads memory and
// does not certify streaming readiness or authorize a spawn.
struct ArenaSlotEvidence {
    int32_t index;
    bool enemy;
    bool reference_valid;
    bool position_valid;
    bool front_arrow_valid;
    bool back_arrow_valid;
};
enum class ArenaSlotsResult : uint32_t {
    Ok, InvalidInput, InvalidReference, InvalidIndex, DuplicateIndex,
    MissingPosition, MissingOrientation, MissingRequiredSlot
};
struct ArenaSlotsObservation {
    ArenaSlotsResult result;
    uint64_t enemy_mask;
    uint64_t party_mask;
};
inline ArenaSlotsObservation validate_arena_slots(const ArenaSlotEvidence* slots,
    size_t count,uint64_t required_enemy,uint64_t required_party,bool require_backline){
    ArenaSlotsObservation out{ArenaSlotsResult::Ok,0,0};
    if(count>128 || (count&&!slots)){
        out.result=ArenaSlotsResult::InvalidInput;return out;
    }
    for(size_t i=0;i<count;++i){
        const auto& slot=slots[i];
        if(!slot.reference_valid){out.result=ArenaSlotsResult::InvalidReference;return out;}
        if(slot.index<0||slot.index>=64){out.result=ArenaSlotsResult::InvalidIndex;return out;}
        const auto bit=uint64_t(1)<<uint32_t(slot.index);
        auto& mask=slot.enemy?out.enemy_mask:out.party_mask;
        if(mask&bit){out.result=ArenaSlotsResult::DuplicateIndex;return out;}
        if(!slot.position_valid){out.result=ArenaSlotsResult::MissingPosition;return out;}
        if(!slot.front_arrow_valid||(!slot.enemy&&require_backline&&!slot.back_arrow_valid)){
            out.result=ArenaSlotsResult::MissingOrientation;return out;
        }
        mask|=bit;
    }
    if((out.enemy_mask&required_enemy)!=required_enemy ||
       (out.party_mask&required_party)!=required_party)out.result=ArenaSlotsResult::MissingRequiredSlot;
    return out;
}
}
