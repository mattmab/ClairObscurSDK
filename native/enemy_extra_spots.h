#pragma once
#include <cstddef>
#include <cstdint>

namespace e33_enemy_spawn {
enum class ExtraSpotsResult : uint32_t {
    Ok, InvalidCount, AlreadyAttempted, PreflightRejected, CreationFailed,
    VerificationFailed, CleanupDeferred, CleanupFailed
};

// A world teardown can destroy an explicitly retained UObject and recycle its
// address. Do not inspect that address or dispatch against its replacement.
// Lease release concerns the registered holder, not the old UObject address.
template<class Record,class Ops>
bool retire_extra_spot_record(Record& record,Ops& ops){
    if(!record.destroyed){
        if(ops.component_current(record)&&ops.component_live(record)&&!ops.destroy_owned(record))return false;
        record.destroyed=true;
    }
    return ops.release_child(record)&&ops.release_component(record);
}

// The engine adapter supplies identity/lease-bearing Records. It must validate
// the current owned encounter, exact original ChildActorComponent/spot classes,
// schemas and game thread in preflight and before each create/retire. Only
// records created through this transaction may be retired; original slots0..3
// are borrowed and never entered here. create must journal outputs immediately.
// A failed/unknown create remains live until retire can reconcile its outcome.
template<class Record>
class ExtraSpotsTransaction {
    Record records_[6]{};
    bool live_[6]{};
    bool attempted_=false,verified_=false;
public:
    bool pending()const{
        for(bool live:live_)if(live)return true;
        return false;
    }
    bool verified()const{return verified_;}
    const Record& record(size_t index)const{return records_[index];}

    template<class Ops> ExtraSpotsResult close(Ops& ops){
        if(!pending()){attempted_=false;verified_=false;return ExtraSpotsResult::Ok;}
        // No component destruction or lease release during active combat or
        // an unavailable game thread. Deferred records remain owned.
        if(!ops.cleanup_ready())return ExtraSpotsResult::CleanupDeferred;
        verified_=false;
        for(size_t i=6;i>0;--i){
            const auto at=i-1;
            if(!live_[at])continue;
            if(!ops.retire(records_[at]))return ExtraSpotsResult::CleanupFailed;
            live_[at]=false;records_[at]={};
        }
        attempted_=false;
        return ExtraSpotsResult::Ok;
    }

    template<class Ops> ExtraSpotsResult stage(Ops& ops,uint32_t total){
        if(total<5||total>10)return ExtraSpotsResult::InvalidCount;
        if(attempted_||pending())return ExtraSpotsResult::AlreadyAttempted;
        if(!ops.preflight(total))return ExtraSpotsResult::PreflightRejected;
        attempted_=true;
        for(uint32_t slot=4;slot<total;++slot){
            const auto at=slot-4;
            // Set before engine dispatch: an exception cannot erase partial
            // creation evidence, and stage cannot replay this transaction.
            live_[at]=true;
            if(!ops.create(slot,records_[at])){
                close(ops);
                return ExtraSpotsResult::CreationFailed;
            }
        }
        if(!ops.verify((uint64_t(1)<<total)-1)){
            close(ops);
            return ExtraSpotsResult::VerificationFailed;
        }
        verified_=true;
        return ExtraSpotsResult::Ok;
    }
};
}
