#pragma once
#include <cstdint>
#include "invocation_protocol.h"
namespace e33_enemy_spawn {
// Only immediately after a validated Object->SoftObject engine conversion.
// That conversion may assign the object's first weak serial. It must never
// turn a previously assigned/stale serial into a wildcard.
inline bool adopt_converted_arena_identity(CallIdentity& identity,const CallIdentity& observed){
    if(identity.index<0||!identity.address||identity.serial<0||
       observed.index!=identity.index||observed.address!=identity.address||
       observed.serial<1001||(identity.serial!=0&&identity.serial!=observed.serial))return false;
    identity=observed;return true;
}
enum class ArenaBindingResult : uint32_t {
    Ok, AlreadyAttempted, PreflightRejected, AuthoredDependenciesUnresolved,
    ConversionFailed, AssignmentFailed, VerificationFailed, TemporaryCleanupFailed
};
struct ArenaBindingState {
    bool attempted=false,temporary_live=false,assigned=false,verified=false;
};
// Ops owns a zero-initialized native soft-reference temporary. Conversion and
// engine assignment may allocate strings: never memcpy an owning soft reference.
// Preflight must validate owned actor, current-world arena, engine schemas and
// copy/destruction entrypoints before this transaction permits any conversion.
// A failed temporary cleanup remains journalled for the owner's close path.
template<class Ops>
ArenaBindingResult bind_owned_arena(Ops& ops,ArenaBindingState& state){
    if(state.attempted)return ArenaBindingResult::AlreadyAttempted;
    if(!ops.preflight())return ArenaBindingResult::PreflightRejected;
    if(!ops.dependencies_supported())return ArenaBindingResult::AuthoredDependenciesUnresolved;
    state.attempted=true;
    state.temporary_live=true; // also covers a conversion that partially fails
    auto result=ArenaBindingResult::Ok;
    if(!ops.convert())result=ArenaBindingResult::ConversionFailed;
    else if(!ops.assign())result=ArenaBindingResult::AssignmentFailed;
    else {
        state.assigned=true;
        if(!ops.verify())result=ArenaBindingResult::VerificationFailed;
        else state.verified=true;
    }
    if(!ops.clear_temporary())return ArenaBindingResult::TemporaryCleanupFailed;
    state.temporary_live=false;
    return result;
}
template<class Ops>
bool close_arena_binding_temporary(Ops& ops,ArenaBindingState& state){
    if(!state.temporary_live)return true;
    if(!ops.clear_temporary())return false;
    state.temporary_live=false;return true;
}
}
