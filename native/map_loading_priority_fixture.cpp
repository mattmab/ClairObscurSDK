#include "map_loading_priority.h"
#include <cassert>
#include <cstdio>
#include <stdexcept>
using namespace e33_map_loading_priority;

struct Ops {
    Observation observed{{41,1,{1,101,0x10000},{2,102,0x20000},{3,103,0x30000},{4,104,0x50000}},0x40000,0x95};
    bool eligible=true,valid_graph=true,fail_read=false,mutate_neighbor=false,expire_hold=false;
    bool throw_call=false,reenter=false;
    Proof proof=Proof::Live;
    Dispatch dispatch=Dispatch::Returned;
    unsigned reads=0,calls=0,enable_calls=0,restore_calls=0;
    Journal* journal=nullptr;
    bool inspect_held(Observation& out){++reads;out=observed;return eligible&&valid_graph&&!fail_read;}
    bool held(const Binding& b){return eligible&&valid_graph&&same(b,observed.binding);}
    Proof inspect_owned(const Binding&,Observation& out){
        ++reads;out=observed;return fail_read||!valid_graph?Proof::Unresolved:proof;
    }
    Dispatch set_original(const Observation& before,bool value,bool require_held){
        if(!valid_graph||fail_read||proof!=Proof::Live||!same_target(before,observed)||
           before.byte!=observed.byte||(require_held&&!held(before.binding)))return Dispatch::NotDispatched;
        if(dispatch==Dispatch::NotDispatched)return dispatch;
        ++calls;if(value)++enable_calls;else ++restore_calls;
        if(reenter){assert(journal);assert(journal->close(*this)==Result::Unknown);}
        observed.byte=value?uint8_t(observed.byte|priority_mask):uint8_t(observed.byte&~priority_mask);
        if(mutate_neighbor)observed.byte^=0x40;
        if(expire_hold)eligible=false;
        if(throw_call)throw std::runtime_error("original call fault");
        return dispatch;
    }
};

int main(){
    // These match the captured property and original setter contracts, not
    // assumed C++ bitfield positions or a replicated property's schema.
    static_assert(priority_flags==6755468160532480ULL&&priority_encoding==0x20200001U);
    static_assert(priority_offset==670&&settings_extent==1216&&priority_mask==0x20);
    static_assert(links[0].offset==48&&links[1].offset==192&&links[2].offset==672);
    static_assert(setter_entry==0x387aae0ULL&&setter_params==17&&setter_extent==24);
    {Ops ops;Journal j;const auto original=ops.observed.byte;
        assert(j.begin(ops)==Result::Ok&&j.state()==State::Owned&&ops.enable_calls==1);
        assert(ops.observed.byte==uint8_t(original|priority_mask));
        assert(j.begin(ops)==Result::Rejected&&ops.calls==1);
        assert(j.poll(ops)==Result::Ok&&ops.calls==1);
        assert(j.close(ops)==Result::Ok&&ops.observed.byte==original&&ops.restore_calls==1);
        assert(j.close(ops)==Result::Ok&&ops.calls==2);
        assert(j.begin(ops)==Result::Rejected); // Never reassert in the released hold.
        ++ops.observed.binding.hold;assert(j.begin(ops)==Result::Ok&&ops.enable_calls==2);
        assert(j.close(ops)==Result::Ok&&ops.restore_calls==2);
    }
    {Ops ops;Journal j;ops.observed.byte|=priority_mask;const auto original=ops.observed.byte;
        assert(j.begin(ops)==Result::Ok&&j.state()==State::Borrowed&&!ops.calls);
        ops.eligible=false;ops.fail_read=true;
        assert(j.poll(ops)==Result::Ok&&j.state()==State::Closed&&!ops.calls&&ops.observed.byte==original);
    }
    for(unsigned mode=0;mode<7;++mode){Ops ops;Journal j;
        if(mode==0)ops.eligible=false;
        if(mode==1)ops.valid_graph=false;
        if(mode==2)ops.observed.binding.settings.serial=0;
        if(mode==3)ops.observed.binding.world.address=0x10001;
        if(mode==4)ops.observed.binding.level.address=ops.observed.binding.world.address;
        if(mode==5)ops.observed.binding.hold=0;
        if(mode==6)ops.observed.property=0;
        assert(j.begin(ops)==Result::Rejected&&!ops.calls&&!j.active());
    }
    {Ops ops;Journal j;ops.dispatch=Dispatch::NotDispatched;
        assert(j.begin(ops)==Result::Rejected&&!j.unknown()&&!ops.calls);
        ops.dispatch=Dispatch::Returned;assert(j.begin(ops)==Result::Rejected&&!ops.calls);
        ++ops.observed.binding.hold;assert(j.begin(ops)==Result::Ok&&ops.calls==1);
    }
    for(unsigned mode=0;mode<3;++mode){Ops ops;Journal j;
        ops.dispatch=mode==0?Dispatch::Unknown:Dispatch::Returned;
        ops.mutate_neighbor=mode==1;ops.throw_call=mode==2;
        if(mode==2){try{j.begin(ops);assert(false);}catch(const std::runtime_error&){}}
        else assert(j.begin(ops)==Result::Unknown);
        assert(j.unknown()&&ops.calls==1);
        assert(j.begin(ops)==Result::Rejected&&j.close(ops)==Result::Unknown&&j.poll(ops)==Result::Unknown&&ops.calls==1);
    }
    {Ops ops;Journal j;ops.journal=&j;ops.reenter=true;
        assert(j.begin(ops)==Result::Ok&&ops.calls==1);
        assert(j.close(ops)==Result::Ok&&ops.calls==2);
    }
    {Ops ops;Journal j;ops.expire_hold=true;
        assert(j.begin(ops)==Result::Ok&&j.state()==State::Closed&&ops.calls==2);
    }
    // Controller loss, cinematic takeover and explicit hold release all revoke
    // eligibility; restoration uses the owned graph, not the current controller.
    for(unsigned reason=0;reason<3;++reason){Ops ops;Journal j;
        assert(j.begin(ops)==Result::Ok);ops.eligible=false;
        assert(j.poll(ops)==Result::Ok&&j.state()==State::Closed&&ops.restore_calls==1);
    }
    {Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);ops.eligible=false;ops.proof=Proof::Retired;
        assert(j.poll(ops)==Result::Ok&&j.retired()&&ops.restore_calls==0);
    }
    {Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);ops.eligible=false;ops.fail_read=true;
        assert(j.poll(ops)==Result::Pending&&j.state()==State::Owned&&ops.calls==1);
        ops.fail_read=false;assert(j.poll(ops)==Result::Ok&&ops.restore_calls==1);
    }
    {Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);ops.observed.binding.settings.serial++;
        assert(j.close(ops)==Result::Pending&&j.state()==State::Owned&&ops.calls==1);
        ops.proof=Proof::Retired;assert(j.close(ops)==Result::Ok&&ops.calls==1);
    }
    {Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);ops.observed.byte^=0x40;
        const auto before=ops.observed.byte;
        assert(j.close(ops)==Result::Ok&&ops.observed.byte==uint8_t(before&~priority_mask));
    }
    {Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);ops.observed.byte&=uint8_t(~priority_mask);
        assert(j.close(ops)==Result::Ok&&ops.calls==1);
    }
    {Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);ops.dispatch=Dispatch::NotDispatched;
        assert(j.close(ops)==Result::Pending&&j.state()==State::Owned&&ops.calls==1);
        ops.dispatch=Dispatch::Returned;assert(j.close(ops)==Result::Ok&&ops.calls==2);
    }
    for(unsigned mode=0;mode<2;++mode){Ops ops;Journal j;assert(j.begin(ops)==Result::Ok);
        ops.dispatch=mode==0?Dispatch::Unknown:Dispatch::Returned;ops.mutate_neighbor=mode==1;
        assert(j.close(ops)==Result::Unknown&&j.unknown()&&ops.calls==2);
        assert(j.close(ops)==Result::Unknown&&j.poll(ops)==Result::Unknown&&ops.calls==2);
    }
    // A failed optional priority cleanup never prevents the existing movement
    // guard from releasing. The journal stays owned for a separate close check.
    for(unsigned mode=0;mode<3;++mode){
        Ops ops;Journal journal;assert(journal.begin(ops)==Result::Ok);
        if(mode==0)ops.dispatch=Dispatch::Unknown;
        if(mode==1)ops.fail_read=true;
        if(mode==2)ops.dispatch=Dispatch::NotDispatched;
        struct Cleanup {
            Journal& journal;Ops& ops;unsigned movement_calls=0;Result priority=Result::Ok;
            void release_priority(){priority=journal.close(ops);}
            uint32_t release_movement(){++movement_calls;return 0;}
        } cleanup{journal,ops};
        assert(!release_guard(cleanup)&&cleanup.movement_calls==1&&journal.active());
        assert(cleanup.priority==(mode==0?Result::Unknown:Result::Pending));
        const auto calls=ops.calls;
        if(mode==0){assert(!release_guard(cleanup)&&cleanup.movement_calls==2&&ops.calls==calls);}
    }
    std::puts("map loading priority ownership fixture passed");
}
