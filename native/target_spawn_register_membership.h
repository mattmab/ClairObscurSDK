#pragma once
#include "spawn_membership_proof.h"
#include "bound_object_frame.h"

// Fixed audited read-only map lookup. Not an arbitrary native-call facility.
// No SpawnObject, Blueprint callback, weak-pointer reinterpretation or write.
template<class Query> struct TargetSpawnRegisterMembership {
    const Query& query;
    e33_camera_binding::Guid binding;
    bool context()const{return query.context();}
    e33_camera_binding::Profile profile()const{return query.profile;}
    bool valid(const CallIdentity& id)const{return query.valid(id);}
    bool owner_valid()const {
        e33_camera_binding::BindingValue root{};
        std::memcpy(root.guid,binding.words,16);root.resolve_parent_index=-1;
        return query.validate_context(root);
    }
    bool capture_register(e33_camera_binding::RegisterIdentity& out)const {
        if(!context() || !owner_valid())return false;
        out={local_read<uint64_t>(query.player.address+0x358),local_read<uint64_t>(query.player.address+0x360)};
        return out.pointer && !(out.pointer&7) && out.pointer<=UINT64_MAX-0x80 && out.control &&
            !(out.control&7) && local_read<uint64_t>(out.pointer)==query.base+0x74055c0;
    }
    e33_camera_binding::WeakIdentity* lookup(uint64_t object,e33_camera_binding::WeakIdentity* output,
                                            const e33_camera_binding::Guid* guid,const uint32_t* sequence)const {
        using Lookup=e33_camera_binding::WeakIdentity*(__fastcall*)(void*,e33_camera_binding::WeakIdentity*,
            const e33_camera_binding::Guid*,const uint32_t*);
        return reinterpret_cast<Lookup>(query.base+0x2d4d9b0)(reinterpret_cast<void*>(object),output,guid,sequence);
    }
    bool weak_matches(const e33_camera_binding::WeakIdentity& weak,const CallIdentity& candidate)const {
        // call_identity independently resolves this index/serial to its registry
        // address. Compare all components, never interpret weak bytes as pointer.
        return candidate.index==weak.index && candidate.serial==weak.serial && query.valid(candidate);
    }
};
