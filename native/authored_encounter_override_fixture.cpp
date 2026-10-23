#include "authored_encounter_override.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
using namespace e33_enemy_spawn;
struct OverrideOps {
    EncounterHandle possible{0x20000,1},selected{};
    bool ready=true,fail_write=false,fail_readback=false;unsigned writes=0;
    bool preflight(EncounterHandle value){return ready&&possible.table==value.table;}
    void write_name(uint64_t name){++writes;if(fail_write)throw std::runtime_error("fault");possible.name=name;}
    bool verify_possible(EncounterHandle value){return !fail_readback&&same_encounter(possible,value);}
    bool verify_selected(EncounterHandle value){return same_encounter(selected,value);}
};
struct MapOps {
    std::vector<unsigned char> memory=std::vector<unsigned char>(0x2000);
    bool change_header=false,change_slot=false;unsigned header_reads=0,slot_reads=0;
    template<class T> void put(uint64_t address,T value){assert(address>=0x10000&&address+sizeof(T)<=0x12000);std::memcpy(memory.data()+address-0x10000,&value,sizeof(T));}
    template<class T> T read(uint64_t address){
        T value{};assert(address>=0x10000&&address+sizeof(T)<=0x12000);
        std::memcpy(&value,memory.data()+address-0x10000,sizeof(T));
        if(change_header&&address==0x10000&&++header_reads==2)++value;
        if(change_slot&&address==0x10100&&++slot_reads==2)++value;
        return value;
    }
    bool matches_name(uint64_t address){return read<uint64_t>(address)==42;}
    MapOps(){
        put<uint64_t>(0x10000,0x10100);put<int32_t>(0x10008,3);put<int32_t>(0x1000c,3);
        put<uint32_t>(0x10010,5);put<int32_t>(0x10028,3);put<int32_t>(0x1002c,128);put<int32_t>(0x10034,1);
        put<uint64_t>(0x10100,42);put<uint64_t>(0x10108,0x11000);
        put<uint64_t>(0x10130,99);put<uint64_t>(0x10138,0x11100);
    }
};
int main(){
    const EncounterHandle expected{0x20000,42};OverrideOps ops;AuthoredEncounterOverride state;
    ops.ready=false;assert(!state.apply(ops,expected)&&!state.pending()&&!ops.writes);
    ops.ready=true;assert(!state.apply(ops,{0x30000,42})&&!state.pending());
    assert(!state.apply(ops,{0x20000,0})&&!state.pending());
    assert(state.apply(ops,expected)&&ops.writes==1&&state.phase()==EncounterOverridePhase::Applied);
    assert(!state.apply(ops,expected)&&ops.writes==1);
    assert(!state.verify_initialized(ops));ops.selected=expected;
    assert(state.verify_initialized(ops)&&state.phase()==EncounterOverridePhase::Verified);
    ops.selected.name=99;assert(!state.verify_initialized(ops));
    ops.selected=expected;ops.possible.name=99;assert(!state.verify_initialized(ops));
    OverrideOps fault;fault.fail_write=true;AuthoredEncounterOverride attempted;
    try{attempted.apply(fault,expected);assert(false);}catch(const std::runtime_error&){}
    assert(attempted.phase()==EncounterOverridePhase::Attempted&&!attempted.apply(fault,expected)&&fault.writes==1);
    OverrideOps readback;readback.fail_readback=true;AuthoredEncounterOverride uncertain;
    assert(!uncertain.apply(readback,expected)&&uncertain.pending()&&!uncertain.apply(readback,expected));
    uint64_t key=999;MapOps map;assert(find_unique_encounter_key(map,0x10000,key)&&key==42);
    MapOps missing;missing.put<uint64_t>(0x10100,77);assert(!find_unique_encounter_key(missing,0x10000,key)&&!key);
    MapOps duplicate;duplicate.put<uint64_t>(0x10130,42);assert(!find_unique_encounter_key(duplicate,0x10000,key));
    MapOps occupancy;occupancy.put<int32_t>(0x10034,0);assert(!find_unique_encounter_key(occupancy,0x10000,key));
    MapOps capacity;capacity.put<int32_t>(0x1000c,4097);assert(!find_unique_encounter_key(capacity,0x10000,key));
    MapOps bitmap;bitmap.put<int32_t>(0x1002c,256);assert(!find_unique_encounter_key(bitmap,0x10000,key));
    MapOps nullrow;nullrow.put<uint64_t>(0x10108,0);assert(!find_unique_encounter_key(nullrow,0x10000,key));
    MapOps changing;changing.change_header=true;assert(!find_unique_encounter_key(changing,0x10000,key));
    MapOps changedslot;changedslot.change_slot=true;assert(!find_unique_encounter_key(changedslot,0x10000,key));
    puts("Authored encounter fixture passed: exact live row, sparse-map bounds/occupancy/stability, single owned mutation, no replay after fault, post-initialization checks.");
}
