#include "spawn_membership_proof.h"
#include <cassert>
#include <iostream>
struct CallIdentity {int32_t index,serial;uint64_t address;};
template<class T> T local_read(uint64_t);
#include "target_spawn_register_membership.h"
struct ContextQueryFixture {
    mutable unsigned context_checks=0,reservations=0;
    bool valid_context=true;
    bool validate_context(const e33_camera_binding::BindingValue& binding)const {
        ++context_checks;
        assert(binding.sequence_id==0 && binding.resolve_parent_index==-1);
        assert(binding.guid[0]==3868951513u && binding.guid[3]==2702779930u);
        return valid_context;
    }
    bool validate(const e33_camera_binding::BindingValue&)const {++reservations;return false;}
};
using namespace e33_camera_binding;
struct FakeMembership {
    bool live=true,owner=true,identity=true,register_ok=true,changed=false,wrong_out=false,mutate_guid=false,mutate_root=false;
    bool changed_control=false,drop_owner=false,drop_context=false,drop_identity=false;
    Profile selected=Profile::locomotive;
    WeakIdentity weak{17,29};uint32_t captures=0,calls=0;
    bool context()const{return live;}
    Profile profile()const{return selected;}
    bool owner_valid()const{return owner;}
    bool valid(uint64_t candidate)const{return identity && candidate==99;}
    bool capture_register(RegisterIdentity& out) {++captures;out={uint64_t(changed&&captures==2 ? 24:8),uint64_t(changed_control&&captures==2 ? 24:16)};return register_ok;}
    WeakIdentity* lookup(uint64_t,WeakIdentity* out,Guid* guid,uint32_t* root) {
        ++calls;if(drop_owner)owner=false;if(drop_context)live=false;if(drop_identity)identity=false;*out=weak;if(mutate_guid)guid->words[3]^=1;if(mutate_root)*root=1;
        return wrong_out ? nullptr:out;
    }
    bool weak_matches(const WeakIdentity& value,uint64_t candidate)const {
        return candidate==99 && value.index==17 && value.serial==29;
    }
};
int main() {
    const Guid guid{{3868951513u,1230066568u,4000387518u,2702779930u}};
    {ContextQueryFixture query;TargetSpawnRegisterMembership<ContextQueryFixture> adapter{query,guid};
     // One output may already be retained. Membership must revalidate the full
     // context path, never request a new dispatch reservation.
     assert(adapter.owner_valid()&&query.context_checks==1&&query.reservations==0);
     query.valid_context=false;assert(!adapter.owner_valid()&&query.context_checks==2&&query.reservations==0);}
    {FakeMembership ops;assert(spawn_register_member(ops,guid,uint64_t(99)));assert(ops.calls==1&&ops.captures==2);}
    {FakeMembership ops;ops.weak={0,0};WeakIdentity out{88,99};assert(spawn_register_lookup(ops,guid,out)==MembershipResult::empty);
     assert(out.index==0&&out.serial==0&&ops.calls==1&&ops.captures==2);}
    for(unsigned failure=0;failure<5;++failure) {
        FakeMembership ops;
        switch(failure){case 0:ops.live=false;break;case 1:ops.owner=false;break;case 2:ops.identity=false;break;
         case 3:ops.register_ok=false;break;case 4:ops.selected=Profile::none;break;}
        assert(!spawn_register_member(ops,guid,uint64_t(99))&&ops.calls==0);
    }
    for(unsigned failure=0;failure<13;++failure) {
        FakeMembership ops;
        switch(failure){case 0:ops.changed=true;break;case 1:ops.wrong_out=true;break;case 2:ops.mutate_guid=true;break;
         case 3:ops.mutate_root=true;break;case 4:ops.weak={0,0};break;case 5:ops.weak.index=-1;break;
         case 6:ops.weak.serial=-1;break;case 7:ops.weak.index=18;break;case 8:ops.weak.serial=30;break;case 9:ops.changed_control=true;break;
         case 10:ops.drop_owner=true;break;case 11:ops.drop_context=true;break;case 12:ops.drop_identity=true;break;}
        assert(!spawn_register_member(ops,guid,uint64_t(99))&&ops.calls==1);
    }
    {FakeMembership ops;Guid wrong=guid;wrong.words[1]^=1;assert(!spawn_register_member(ops,wrong,uint64_t(99))&&ops.calls==0);}
    std::cout<<"Exact spawn-register membership fixtures passed\n";
}
