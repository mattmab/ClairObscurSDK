#include "battle_parameter_owner.h"
#include "battle_entry_copy_stub.h"
#include <cassert>
#include <vector>
#include <stdexcept>
using namespace e33_enemy_spawn;
struct Ops {
    bool admitted=true,ready=true,cleanup=true,copy_unknown=false;
    int fail_acquire=-1,unknown_acquire=-1,throw_acquire=-1,fail_release=-1,unknown_release=-1;
    bool inconsistent=false;
    bool entry_allowed=true,retirement=false,throw_entry=false;
    ParameterCall entry_result=ParameterCall::Completed;
    unsigned entries=0,retirement_checks=0;
    BattleParameterOwner* inspect_entry_owner=nullptr;
    bool throw_retirement=false;
    bool copy_ready=false,throw_copy_proof=false;
    unsigned copy_proofs=0;
    unsigned acquired=0,released=0,destroyed=0;
    std::vector<int> events;
    bool admit(){return admitted;}
    bool entry_preflight(const void* data){assert(data);return entry_allowed;}
    ParameterCall invoke_entry(const void* data){
        assert(data);++entries;
        if(inspect_entry_owner){
            assert(inspect_entry_owner->entry_state()==BattleEntryState::DispatchUnknown);
            assert(inspect_entry_owner->pending()&&inspect_entry_owner->quarantined());
            assert(!inspect_entry_owner->close(*this));
            assert(destroyed==0&&released==0);
        }
        if(throw_entry)throw std::runtime_error("entry unknown");return entry_result;
    }
    bool entry_retirement_ready(){++retirement_checks;if(throw_retirement)throw std::runtime_error("retirement proof unavailable");return retirement;}
    ParameterCall apply(void*){return ParameterCall::Completed;}
    bool owned_parameter_copy_ready(const void* data){assert(data);++copy_proofs;if(throw_copy_proof)throw std::runtime_error("copy proof unavailable");return copy_ready;}
    ParameterCall acquire(unsigned at,uint64_t& token){
        ++acquired;events.push_back(int(at));
        if(int(at)==throw_acquire)throw std::runtime_error("acquire unknown");
        if(int(at)==fail_acquire){if(inconsistent)token=999;return ParameterCall::NotDispatched;}
        token=100+at;return int(at)==unknown_acquire?ParameterCall::Unknown:ParameterCall::Completed;
    }
    bool release_ready(){return ready;}
    ParameterCall release(unsigned at,uint64_t token){
        assert(token==100+at);++released;events.push_back(20+int(at));
        if(int(at)==fail_release)return ParameterCall::NotDispatched;
        return int(at)==unknown_release?ParameterCall::Unknown:ParameterCall::Completed;
    }
    struct FrameOps {
        Ops& owner;
        bool preflight(){return true;}
        bool cleanup_ready(){return owner.cleanup;}
        ParameterCall initialize(void*){owner.events.push_back(10);return ParameterCall::Completed;}
        ParameterCall copy(void*){owner.events.push_back(11);return owner.copy_unknown?ParameterCall::Unknown:ParameterCall::Completed;}
        ParameterCall destroy(void*){++owner.destroyed;owner.events.push_back(12);return ParameterCall::Completed;}
    };
    FrameOps frame_ops(const ParameterLease (&)[3]){return {*this};}
};
int main(){
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.pending());assert(owner.copied_data());assert(!owner.open(o));assert(owner.close(o));assert(!owner.pending());assert(owner.close(o));assert(o.events==std::vector<int>({0,1,2,10,11,12,22,21,20}));}
    {BattleParameterOwner owner;Ops o;o.admitted=false;assert(!owner.open(o));assert(!owner.attempted());assert(o.acquired==0);assert(owner.close(o));}
    {BattleParameterOwner owner;Ops o;assert(owner.close(o));assert(!owner.open(o));assert(o.acquired==0);}
    for(int at=0;at<3;++at){BattleParameterOwner owner;Ops o;o.fail_acquire=at;assert(!owner.open(o));assert(!owner.open(o));assert(owner.close(o));assert(o.destroyed==0&&o.released==unsigned(at));assert(!owner.pending());}
    for(int at=0;at<3;++at){BattleParameterOwner owner;Ops o;o.unknown_acquire=at;assert(!owner.open(o));assert(owner.quarantined());assert(!owner.close(o));assert(o.released==0);assert(owner.pending());}
    for(int at=0;at<3;++at){BattleParameterOwner owner;Ops o;o.throw_acquire=at;try{owner.open(o);assert(false);}catch(const std::runtime_error&){}assert(owner.quarantined());assert(!owner.close(o));assert(o.released==0);}
    {BattleParameterOwner owner;Ops o;o.fail_acquire=1;o.inconsistent=true;assert(!owner.open(o));assert(owner.quarantined());assert(!owner.close(o));assert(o.released==0);}
    {BattleParameterOwner owner;Ops o;o.copy_unknown=true;assert(!owner.open(o));assert(owner.quarantined());assert(!owner.close(o));assert(o.destroyed==0&&o.released==0);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));o.cleanup=false;assert(!owner.close(o));assert(o.destroyed==0&&o.released==0);o.cleanup=true;assert(owner.close(o));}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));o.ready=false;assert(!owner.close(o));assert(o.destroyed==1&&o.released==0);o.ready=true;assert(owner.close(o));assert(o.destroyed==1&&o.released==3);}
    for(int at=0;at<3;++at){BattleParameterOwner owner;Ops o;assert(owner.open(o));o.fail_release=at;assert(!owner.close(o));const auto before=o.released;assert(owner.lease(unsigned(at)).state==ParameterLeaseState::Held);o.fail_release=-1;assert(owner.close(o));assert(o.released==before+unsigned(at)+1);assert(o.destroyed==1);}
    for(int at=0;at<3;++at){BattleParameterOwner owner;Ops o;assert(owner.open(o));o.unknown_release=at;assert(!owner.close(o));const auto before=o.released;assert(owner.quarantined());assert(!owner.close(o));assert(o.released==before&&o.destroyed==1);}
    {BattleParameterOwner owner;Ops o;assert(!owner.dispatch_entry(o));assert(owner.open(o));assert(!owner.dispatch_entry(o));assert(o.entries==0);assert(owner.close(o));}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));assert(owner.dispatch_entry(o));assert(owner.entry_state()==BattleEntryState::Returned);assert(!owner.dispatch_entry(o));assert(!owner.close(o));assert(owner.pending());assert(o.entries==1&&o.destroyed==0&&o.released==0);o.retirement=true;assert(owner.close(o));assert(owner.entry_state()==BattleEntryState::Retired);assert(!owner.pending());assert(owner.close(o));assert(o.destroyed==1&&o.released==3);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));o.entry_allowed=false;assert(!owner.dispatch_entry(o));assert(owner.entry_state()==BattleEntryState::Empty);assert(o.entries==0);assert(owner.close(o));assert(o.retirement_checks==0);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));o.entry_result=ParameterCall::NotDispatched;assert(!owner.dispatch_entry(o));assert(owner.entry_state()==BattleEntryState::NotDispatched);assert(!owner.dispatch_entry(o));assert(owner.close(o));assert(o.entries==1&&o.destroyed==1&&o.released==3);}
    for(bool throws:{false,true}){BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));o.entry_result=ParameterCall::Unknown;o.throw_entry=throws;try{assert(!owner.dispatch_entry(o));assert(!throws);}catch(const std::runtime_error&){assert(throws);}assert(owner.quarantined());o.retirement=true;assert(!owner.close(o));assert(!owner.dispatch_entry(o));assert(o.entries==1&&o.destroyed==0&&o.released==0&&o.retirement_checks==0);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));assert(owner.dispatch_entry(o));o.retirement=true;o.cleanup=false;assert(!owner.close(o));assert(owner.entry_state()==BattleEntryState::Retired);assert(o.destroyed==0);o.cleanup=true;assert(owner.close(o));assert(o.retirement_checks==1&&o.destroyed==1&&o.released==3);}
    {BattleEntryTransaction entry;Ops o;assert(!entry.dispatch(nullptr,o));assert(o.entries==0);assert(entry.retire(o));assert(o.retirement_checks==0);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));o.inspect_entry_owner=&owner;assert(owner.dispatch_entry(o));assert(o.entries==1&&o.destroyed==0);o.retirement=true;assert(owner.close(o));}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));assert(owner.dispatch_entry(o));o.throw_retirement=true;try{owner.close(o);assert(false);}catch(const std::runtime_error&){}assert(owner.entry_state()==BattleEntryState::Returned&&owner.pending());assert(o.destroyed==0&&o.released==0);o.throw_retirement=false;o.retirement=true;assert(owner.close(o));}
    {BattleParameterOwner owner;Ops o;o.copy_ready=true;assert(!owner.confirm_entry_copy(o));assert(owner.open(o));assert(owner.apply_policy(o));assert(!owner.confirm_entry_copy(o));assert(o.copy_proofs==0);assert(owner.dispatch_entry(o));assert(owner.confirm_entry_copy(o));assert(owner.entry_state()==BattleEntryState::CopyVerified&&owner.pending());assert(!owner.confirm_entry_copy(o));assert(!owner.dispatch_entry(o));assert(owner.close(o));assert(o.retirement_checks==0&&o.destroyed==1&&o.released==3);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));assert(owner.dispatch_entry(o));assert(!owner.confirm_entry_copy(o));assert(!owner.close(o));assert(o.destroyed==0&&o.released==0);o.copy_ready=true;assert(owner.confirm_entry_copy(o));assert(owner.close(o));assert(o.entries==1&&o.copy_proofs==2);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));o.entry_result=ParameterCall::Unknown;assert(!owner.dispatch_entry(o));o.copy_ready=true;assert(!owner.confirm_entry_copy(o));assert(!owner.close(o));assert(o.copy_proofs==0&&o.destroyed==0&&o.released==0);}
    {BattleParameterOwner owner;Ops o;assert(owner.open(o));assert(owner.apply_policy(o));assert(owner.dispatch_entry(o));o.throw_copy_proof=true;try{owner.confirm_entry_copy(o);assert(false);}catch(const std::runtime_error&){}assert(owner.entry_state()==BattleEntryState::Returned);assert(!owner.close(o));assert(o.destroyed==0&&o.released==0);o.throw_copy_proof=false;o.copy_ready=true;assert(owner.confirm_entry_copy(o));assert(owner.close(o));}
    {
        std::array<uint8_t,36> code{};
        for(auto pair:std::vector<std::pair<unsigned,unsigned>>{{0,0x64},{9,0},{18,0x46},{27,0x1d},{32,0x16},{33,4},{34,0xb},{35,0x53}})code[pair.first]=static_cast<uint8_t>(pair.second);
        const uint64_t destination=0x10000,source=0x20000,graph=0x30000;
        const int32_t entry=41580;
        std::memcpy(code.data()+1,&destination,8);std::memcpy(code.data()+10,&source,8);std::memcpy(code.data()+19,&graph,8);std::memcpy(code.data()+28,&entry,4);
        BattleEntryCopyStub decoded;
        assert(decode_battle_entry_copy_stub(code.data(),36,decoded));
        assert(decoded.destination==destination&&decoded.source==source&&decoded.graph==graph);
        for(unsigned size:{0U,35U,37U})assert(!decode_battle_entry_copy_stub(code.data(),size,decoded));
        assert(!decode_battle_entry_copy_stub(nullptr,36,decoded));
        for(unsigned offset:{0U,9U,18U,27U,28U,32U,33U,34U,35U}){
            auto bad=code;bad[offset]^=1;assert(!decode_battle_entry_copy_stub(bad.data(),36,decoded));assert(decoded.graph==0);
        }
        for(unsigned offset:{1U,10U,19U})for(uint64_t value:{0ULL,0x10001ULL}){
            auto bad=code;std::memcpy(bad.data()+offset,&value,8);assert(!decode_battle_entry_copy_stub(bad.data(),36,decoded));
        }
        for(unsigned offset:{10U,19U}){auto bad=code;std::memcpy(bad.data()+offset,&destination,8);assert(!decode_battle_entry_copy_stub(bad.data(),36,decoded));}
    }
    return 0;
}
