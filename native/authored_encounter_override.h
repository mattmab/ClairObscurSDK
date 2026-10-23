#pragma once
#include <cstdint>

namespace e33_enemy_spawn {
// A row handle contains one UObject reference and one POD FName. This journal
// never allocates an Unreal array or owns/copies a string. The engine adapter
// must independently prove object ownership, exact schema and row provenance.
struct EncounterHandle { uint64_t table=0,name=0; };
inline bool same_encounter(EncounterHandle a,EncounterHandle b){return a.table==b.table&&a.name==b.name;}
enum class EncounterOverridePhase { Empty, Attempted, Applied, Verified };
class AuthoredEncounterOverride {
    EncounterOverridePhase phase_=EncounterOverridePhase::Empty;
    EncounterHandle expected_{};
public:
    EncounterOverridePhase phase()const{return phase_;}
    bool pending()const{return phase_!=EncounterOverridePhase::Empty;}
    EncounterHandle expected()const{return expected_;}
    // Ops must resolve the row from the exact live table, validate a private
    // single-element array and its original row, and revalidate before writing.
    // Mark before the only write: a fault or readback failure cannot be replayed.
    template<class Ops> bool apply(Ops& ops,EncounterHandle expected){
        if(pending()||!expected.table||!expected.name||!ops.preflight(expected))return false;
        expected_=expected;phase_=EncounterOverridePhase::Attempted;
        ops.write_name(expected.name);
        if(!ops.verify_possible(expected))return false;
        phase_=EncounterOverridePhase::Applied;return true;
    }
    // Original initialization chooses SelectedEncounter. Do not manufacture it
    // or release the hidden staging hold unless both handles still agree.
    template<class Ops> bool verify_initialized(Ops& ops){
        if(phase_!=EncounterOverridePhase::Applied&&phase_!=EncounterOverridePhase::Verified)return false;
        if(!ops.verify_possible(expected_)||!ops.verify_selected(expected_))return false;
        phase_=EncounterOverridePhase::Verified;return true;
    }
};

// Supported-build DataTable sparse-map layout, already inspected by the SDK's
// read-only research probe. The caller validates table identity/class/accessor.
// Read each slot and bitmap twice plus the complete header. A game-thread caller
// supplies read<T> and matches_name(address); no numeric names cross the wire.
template<class Ops> bool find_unique_encounter_key(Ops& ops,uint64_t map,uint64_t& result){
    result=0;
    uint64_t header[10]{};
    for(unsigned i=0;i<10;++i)header[i]=ops.template read<uint64_t>(map+i*8);
    const auto data=header[0],heap=header[4];
    const auto count=int32_t(uint32_t(header[1])),cap=int32_t(uint32_t(header[1]>>32));
    const auto bits=int32_t(uint32_t(header[5])),bitcap=int32_t(uint32_t(header[5]>>32));
    const auto free=int32_t(uint32_t(header[6]>>32));
    if(count<0||count>cap||cap>4096||bits!=count||bitcap<bits||bitcap>4096||free<0||free>count||
       (!heap&&bitcap>128)||(heap&&(heap<0x10000||(heap&7)))||
       (count&&(data<0x10000||(data&7))))return false;
    const auto masks=heap?heap:map+16;
    int live=0,matches=0;uint64_t found=0;
    for(int n=0;n<count;++n){
        const auto word_at=masks+uint64_t(n/32)*4;
        const auto word=ops.template read<uint32_t>(word_at);
        if(word&(uint32_t(1)<<(n%32))){
            ++live;const auto at=data+uint64_t(n)*24;
            const auto key=ops.template read<uint64_t>(at),row=ops.template read<uint64_t>(at+8);
            if(!key||row<0x10000||(row&7))return false;
            if(ops.matches_name(at)){++matches;found=key;}
            if(ops.template read<uint64_t>(at)!=key||ops.template read<uint64_t>(at+8)!=row)return false;
        }
        if(ops.template read<uint32_t>(word_at)!=word)return false;
    }
    for(unsigned i=0;i<10;++i)if(ops.template read<uint64_t>(map+i*8)!=header[i])return false;
    if(live!=count-free||matches!=1)return false;
    result=found;return true;
}
}
