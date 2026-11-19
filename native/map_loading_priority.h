#pragma once
#include <cstdint>

// The adapter must use the original
// KismetSystemLibrary::SetBoolPropertyByName, never write a WorldSettings byte.
namespace e33_map_loading_priority {

// Qualified against the supported game build's reflected layer-root schema.
// Names, owner paths, class constraints, widths, dimensions, flags and vtables
// must all be checked by the adapter, not merely the following offsets.
struct LinkSchema {const char* owner;const char* name;const char* constraint;uint32_t offset;uint64_t flags;};
inline constexpr LinkSchema links[]={
    {"World","PersistentLevel","Level",48,79938962105311744ULL},
    {"Level","OwningWorld","World",192,79938962105311744ULL},
    {"Level","WorldSettings","WorldSettings",672,93449760987415040ULL},
};
inline constexpr uint64_t object_property_vtable=0x6e11d38ULL;
inline constexpr uint64_t bool_property_vtable=0x6e119b0ULL;
inline constexpr uint64_t priority_flags=6755468160532480ULL;
inline constexpr uint32_t priority_offset=670,priority_encoding=0x20200001U;
inline constexpr uint8_t priority_mask=0x20;
inline constexpr uint32_t world_extent=2296,level_extent=792,settings_extent=1216;
inline constexpr const char* priority_name="bHighPriorityLoadingLocal";
// Original function contract is also in story_npc_config_profiles.h, functions[2].
inline constexpr uint32_t setter_flags=67249155,setter_params=17,setter_extent=24;
inline constexpr uint16_t setter_return=65535;
inline constexpr uint64_t setter_entry=0x387aae0ULL;

struct Identity {int32_t index=-1,serial=0;uint64_t address=0;};
inline bool same(const Identity& a,const Identity& b){return a.index==b.index&&a.serial==b.serial&&a.address==b.address;}
inline bool valid(const Identity& id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
struct Binding {
    uint64_t owner=0,hold=0;
    Identity world{},level{},settings{},viewport{};
};
inline bool same(const Binding& a,const Binding& b){
    return a.owner==b.owner&&a.hold==b.hold&&same(a.world,b.world)&&same(a.level,b.level)&&same(a.settings,b.settings)&&same(a.viewport,b.viewport);
}
inline bool valid(const Binding& b){
    return b.owner&&b.hold&&valid(b.world)&&valid(b.level)&&valid(b.settings)&&valid(b.viewport)&&
        b.world.address!=b.level.address&&b.world.address!=b.settings.address&&b.level.address!=b.settings.address;
}
struct Observation {Binding binding{};uint64_t property=0;uint8_t byte=0;};
inline bool valid(const Observation& o){return valid(o.binding)&&o.property>=0x10000&&o.property<=0x7fffffffffffULL&&!(o.property&7);}
inline bool same_target(const Observation& a,const Observation& b){return same(a.binding,b.binding)&&a.property==b.property;}

enum class Proof {Live,Retired,Unresolved};
enum class Dispatch {NotDispatched,Returned,Unknown};
enum class Result {Ok,Rejected,Pending,Unknown};
enum class State {Empty,Borrowed,Owned,Rejected,Closed,Unknown};

// Priority is an optional optimization, not movement authority. Its cleanup
// outcome is journalled separately and must never suppress guard restoration.
template<class Ops> uint32_t release_guard(Ops& ops){
    ops.release_priority();return ops.release_movement();
}

// Required Ops contract:
// inspect_held(out): fresh engine-thread/GC-safe context + current MapLoadGate
// owner/hold sequence, held pawn/movement authority and no cinematic. Validate
// the full exact World -> PersistentLevel -> WorldSettings graph and reflected
// priority descriptor; capture positive generations without retaining a world.
// held(binding): revalidate that SAME held authority, never just owner.active().
// inspect_owned(binding,out): does NOT require a surviving player controller.
// Live means the same exact live graph and descriptor, even if possession has
// changed. Retired requires conclusive old-object/world retirement proof; a
// failed read, GC window, replacement viewport, or missing controller alone is
// Unresolved. Never resolve an old identity to a replacement object.
// set_original(before,value,require_held): revalidate exact graph, field schema,
// original byte, original qualified setter/CDO and game-thread context directly
// before dispatch. For enable, also revalidate held authority. Extract the
// FName from the qualified property, invoke the original setter, classify the
// dispatch outcome. No speculative replay and no callback on a retired object.
class Journal {
    State state_=State::Empty;
    Observation original_{};
    bool enable_returned_=false,restore_returned_=false,retired_=false;
    bool repeat(const Binding& next)const{
        return original_.binding.owner==next.owner&&original_.binding.hold>=next.hold;
    }
public:
    State state()const{return state_;}
    bool active()const{return state_==State::Owned||state_==State::Borrowed||state_==State::Unknown;}
    bool unknown()const{return state_==State::Unknown;}
    bool enable_returned()const{return enable_returned_;}
    bool restore_returned()const{return restore_returned_;}
    bool retired()const{return retired_;}
    const Observation& original()const{return original_;}

    template<class Ops> Result begin(Ops& ops){
        if(state_!=State::Empty&&state_!=State::Closed&&state_!=State::Rejected)return Result::Rejected;
        Observation before{};
        if(!ops.inspect_held(before)||!valid(before)||repeat(before.binding))return Result::Rejected;
        original_=before;enable_returned_=restore_returned_=retired_=false;
        if(before.byte&priority_mask){state_=State::Borrowed;return Result::Ok;}
        // Record uncertainty BEFORE an original callback: faults/reentrancy can
        // never erase this attempt or cause a second dispatch.
        state_=State::Unknown;
        const auto call=ops.set_original(before,true,true);
        if(call==Dispatch::NotDispatched){state_=State::Rejected;return Result::Rejected;}
        if(call!=Dispatch::Returned)return Result::Unknown;
        enable_returned_=true;
        Observation after{};
        if(ops.inspect_owned(before.binding,after)!=Proof::Live||!valid(after)||
           !same_target(before,after)||after.byte!=uint8_t(before.byte|priority_mask))return Result::Unknown;
        state_=State::Owned;
        // If an original callback yielded the hold, undo our acknowledged
        // enable immediately. This does not depend on Python polling.
        return ops.held(before.binding)?Result::Ok:close(ops);
    }

    template<class Ops> Result close(Ops& ops){
        if(state_==State::Unknown)return Result::Unknown;
        if(state_==State::Empty||state_==State::Closed||state_==State::Rejected)return Result::Ok;
        if(state_==State::Borrowed){state_=State::Closed;return Result::Ok;}
        Observation before{};
        const auto proof=ops.inspect_owned(original_.binding,before);
        if(proof==Proof::Retired){retired_=true;state_=State::Closed;return Result::Ok;}
        if(proof!=Proof::Live||!valid(before)||!same_target(original_,before))return Result::Pending;
        // Another original system may already have cleared the flag. Do not
        // re-enable it or overwrite any unrelated WorldSettings flags.
        if(!(before.byte&priority_mask)){state_=State::Closed;return Result::Ok;}
        state_=State::Unknown;
        const auto call=ops.set_original(before,false,false);
        if(call==Dispatch::NotDispatched){state_=State::Owned;return Result::Pending;}
        if(call!=Dispatch::Returned)return Result::Unknown;
        restore_returned_=true;
        Observation after{};
        if(ops.inspect_owned(original_.binding,after)!=Proof::Live||!valid(after)||
           !same_target(before,after)||after.byte!=uint8_t(before.byte&~priority_mask))return Result::Unknown;
        state_=State::Closed;return Result::Ok;
    }

    template<class Ops> Result poll(Ops& ops){
        if(state_==State::Unknown)return Result::Unknown;
        if((state_==State::Owned||state_==State::Borrowed)&&!ops.held(original_.binding))return close(ops);
        return Result::Ok;
    }
};
}
