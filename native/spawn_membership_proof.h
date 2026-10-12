#pragma once
#include "bound_camera_proof.h"
namespace e33_camera_binding {
struct WeakIdentity {int32_t index,serial;};
struct RegisterIdentity {uint64_t pointer,control;};
static_assert(sizeof(WeakIdentity)==8);
enum class MembershipResult {empty,member,rejected};
template<class Ops>
MembershipResult spawn_register_lookup(Ops& ops,const Guid& guid,WeakIdentity& result) {
    result={};
    if(!ops.context() || !allowed(ops.profile(),guid) || !ops.owner_valid())return MembershipResult::rejected;
    RegisterIdentity before{},after{};
    if(!ops.capture_register(before))return MembershipResult::rejected;
    Guid input=guid;uint32_t root=0;WeakIdentity weak{};
    if(ops.lookup(before.pointer,&weak,&input,&root)!=&weak || !same(input,guid) || root ||
       !ops.context() || !ops.owner_valid() || !ops.capture_register(after) ||
       before.pointer!=after.pointer || before.control!=after.control)return MembershipResult::rejected;
    if(!weak.index && !weak.serial)return MembershipResult::empty;
    if(weak.index<0 || weak.serial<=0)return MembershipResult::rejected;
    result=weak;return MembershipResult::member;
}
template<class Ops,class Identity>
bool spawn_register_member(Ops& ops,const Guid& guid,const Identity& candidate) {
    if(!ops.valid(candidate))return false;
    WeakIdentity weak{};
    if(spawn_register_lookup(ops,guid,weak)!=MembershipResult::member)return false;
    return ops.weak_matches(weak,candidate) && ops.valid(candidate);
}
}
