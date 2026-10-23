#include "enemy_extra_spots.h"
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>
using namespace e33_enemy_spawn;
struct Record {uint32_t slot=0;bool acknowledged=false;};
struct Ops {
    bool ready=true,battle=false,valid=true,unknown=false;
    uint32_t fail_at=99,throw_at=99,retire_failure=99;
    std::vector<uint32_t> created,retired;
    uint64_t mask=0;
    bool preflight(uint32_t){return ready;}
    bool cleanup_ready(){return !battle;}
    bool create(uint32_t slot,Record& record){
        record.slot=slot;created.push_back(slot);
        if(slot==throw_at)throw std::runtime_error("unknown engine outcome");
        record.acknowledged=slot!=fail_at;
        return record.acknowledged;
    }
    bool verify(uint64_t required){mask=required;return valid;}
    bool retire(Record& record){
        if(record.slot==retire_failure||(!record.acknowledged&&unknown))return false;
        retired.push_back(record.slot);return true;
    }
};
struct RetireRecord {bool destroyed=false;};
struct RetireOps {
    bool current=true,live=true,owned=true,child_release=true;
    unsigned live_reads=0,destroy_calls=0,child_releases=0,component_releases=0;
    bool component_current(const RetireRecord&){return current;}
    bool component_live(const RetireRecord&){++live_reads;return live;}
    bool destroy_owned(const RetireRecord&){if(!owned)return false;++destroy_calls;return true;}
    bool release_child(RetireRecord&){++child_releases;return child_release;}
    bool release_component(RetireRecord&){++component_releases;return true;}
};
int main(){
    unsigned checks=0;
    auto check=[&](bool value){++checks;if(!value){std::fprintf(stderr,"extra spot check %u failed\n",checks);std::exit(1);}};
    {
        Ops ops;ExtraSpotsTransaction<Record> state;
        check(state.stage(ops,10)==ExtraSpotsResult::Ok);
        check(ops.created==std::vector<uint32_t>({4,5,6,7,8,9})&&ops.mask==1023&&state.verified());
        check(state.stage(ops,10)==ExtraSpotsResult::AlreadyAttempted);
        ops.battle=true;check(state.close(ops)==ExtraSpotsResult::CleanupDeferred&&ops.retired.empty()&&state.pending());
        ops.battle=false;check(state.close(ops)==ExtraSpotsResult::Ok);
        check(ops.retired==std::vector<uint32_t>({9,8,7,6,5,4})&&!state.pending());
    }
    {
        Ops ops;ops.fail_at=6;ExtraSpotsTransaction<Record> state;
        check(state.stage(ops,10)==ExtraSpotsResult::CreationFailed);
        check(ops.created==std::vector<uint32_t>({4,5,6})&&ops.retired==std::vector<uint32_t>({6,5,4})&&!state.pending());
    }
    {
        Ops ops;ops.fail_at=6;ops.unknown=true;ExtraSpotsTransaction<Record> state;
        check(state.stage(ops,10)==ExtraSpotsResult::CreationFailed&&state.pending());
        check(state.stage(ops,10)==ExtraSpotsResult::AlreadyAttempted&&ops.retired.empty());
        ops.unknown=false;check(state.close(ops)==ExtraSpotsResult::Ok&&!state.pending());
    }
    {
        Ops ops;ops.throw_at=5;ExtraSpotsTransaction<Record> state;
        try{state.stage(ops,10);check(false);}catch(const std::runtime_error&){}
        check(state.pending()&&state.stage(ops,10)==ExtraSpotsResult::AlreadyAttempted);
        check(state.close(ops)==ExtraSpotsResult::Ok&&ops.retired==std::vector<uint32_t>({5,4}));
    }
    {
        Ops ops;ops.valid=false;ops.retire_failure=5;ExtraSpotsTransaction<Record> state;
        check(state.stage(ops,6)==ExtraSpotsResult::VerificationFailed&&state.pending()&&!state.verified());
        ops.retire_failure=99;check(state.close(ops)==ExtraSpotsResult::Ok&&!state.pending());
    }
    {
        Ops ops;ExtraSpotsTransaction<Record> state;
        check(state.stage(ops,4)==ExtraSpotsResult::InvalidCount&&state.stage(ops,11)==ExtraSpotsResult::InvalidCount);
        ops.ready=false;check(state.stage(ops,10)==ExtraSpotsResult::PreflightRejected&&ops.created.empty());
    }
    {
        RetireRecord record;RetireOps ops;ops.current=false;
        check(retire_extra_spot_record(record,ops));
        check(record.destroyed&&ops.live_reads==0&&ops.destroy_calls==0&&ops.child_releases==1&&ops.component_releases==1);
    }
    {
        RetireRecord record;RetireOps ops;ops.child_release=false;
        check(!retire_extra_spot_record(record,ops)&&record.destroyed&&ops.destroy_calls==1&&ops.component_releases==0);
        ops.child_release=true;check(retire_extra_spot_record(record,ops)&&ops.destroy_calls==1&&ops.component_releases==1);
    }
    {
        RetireRecord record;RetireOps ops;ops.owned=false;
        check(!retire_extra_spot_record(record,ops)&&!record.destroyed&&ops.child_releases==0&&ops.component_releases==0);
        ops.owned=true;ops.live=false;
        check(retire_extra_spot_record(record,ops)&&ops.destroy_calls==0&&record.destroyed);
    }
    std::printf("extra spot lifecycle: %u checks passed\n",checks);
}
