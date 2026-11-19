#pragma once
#include <cstdint>

// Keep an owned source dormant between original construction and its explicit
// radius/configuration transaction. A frame must never see the 50,000 default.
namespace e33_story_source_staging {
constexpr uint32_t rejected=4370,uncertain=4371;
struct Journal {bool attempted=false,acknowledged=false;};
struct Observation {uint64_t component=0,field=0;uint8_t enabled=0;};
template<class Ops> uint32_t disable(Journal& journal,Ops& ops){
    Observation before{},after{};
    if(journal.attempted||!ops.observe(before)||!before.component||!before.field||before.enabled>1)return rejected;
    // The construction owner retains this attempt even if the write faults.
    journal.attempted=true;
    if(before.enabled&&!ops.write(before))return uncertain;
    if(!ops.observe(after)||after.component!=before.component||after.field!=before.field||after.enabled)return uncertain;
    journal.acknowledged=true;return 0;
}
}
