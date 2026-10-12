#pragma once
#include "bound_object_frame.h"
#include "bound_camera_proof.h"
#include "target_strong_reference.h"
#include "stable_identity.h"
#include "strong_lease_pool.h"
#include "factory_binding_overrides.h"

// Private native adapter, never a raw-address Python call. Caller retains its
// factory-created player/actor/asset and supplies the native owner's token check.
template<class Pool>
struct TargetBoundObjectQuery {
    uint64_t base,session;
    CallIdentity player,actor,asset,function;
    e33_camera_binding::Profile profile;
    Pool& outputs;
    void* owner;
    bool (*owns)(void*,const CallIdentity&,const CallIdentity&,const CallIdentity&);
    bool (*asset_profile)(uint64_t,e33_camera_binding::Profile,const CallIdentity&);
    bool (*binding_profile)(const TargetBoundObjectQuery&,const e33_camera_binding::Guid&);
    bool context()const {TargetStrongReferenceOps guard{base,{}};return guard.can_assign();}
    bool same(const CallIdentity& a,const CallIdentity& b)const{return !std::memcmp(&a,&b,sizeof(a));}
    bool valid(const CallIdentity& id)const{return id.address && call_identity(base,id)==id.address && !(local_read<uint32_t>(id.address+8)&0x40000000);}
    bool named(uint64_t object,const char* name,const char* package)const {
        auto id=call_capture(base,object);if(!valid(id) || !exact_name(base,object+24,name))return false;
        auto outer=call_capture(base,local_read<uint64_t>(object+32));
        return valid(outer) && exact_name(base,outer.address+24,package);
    }
    uint64_t field(uint64_t owner_object,const char* name,uint32_t offset,uint32_t width,uint64_t table,uint64_t flags)const {
        auto p=local_read<uint64_t>(owner_object+0x50);
        for(unsigned i=0;p && i<128;++i,p=local_read<uint64_t>(p+0x18)) {
            if(!exact_name(base,p+0x20,name))continue;
            return local_read<uint64_t>(p)==base+table && local_read<uint64_t>(p+0x10)==(owner_object|1) &&
                local_read<uint32_t>(p+0x30)==1 && local_read<uint32_t>(p+0x34)==width &&
                local_read<uint64_t>(p+0x38)==flags && local_read<uint32_t>(p+0x44)==offset ? p:0;
        }
        return 0;
    }
    bool script(uint64_t object,const char* name,const char* package,uint32_t width)const {
        return named(object,name,package) && named(local_read<uint64_t>(object+16),"ScriptStruct","/Script/CoreUObject") &&
            local_read<uint32_t>(object+0x58)==width && !local_read<uint64_t>(object+0x40);
    }
    bool validate_context(const e33_camera_binding::BindingValue& binding)const {
        e33_camera_binding::Guid guid{};std::memcpy(guid.words,binding.guid,16);
        if(!context() || !session || !owns || !asset_profile || !binding_profile || !owner ||
           !e33_camera_binding::allowed(profile,guid) || binding.sequence_id!=0 || binding.resolve_parent_index!=-1 ||
           !valid(player) || !valid(actor) || !valid(asset) || !valid(function) ||
           !owns(owner,player,actor,asset) || !asset_profile(base,profile,asset) || !binding_profile(*this,guid))return false;
        auto actor_class=local_read<uint64_t>(actor.address+16),player_class=local_read<uint64_t>(player.address+16);
        if(!call_is_class(base,actor_class) || !named(actor_class,"LevelSequenceActor","/Script/LevelSequence") ||
           !call_is_class(base,player_class) || !named(player_class,"LevelSequencePlayer","/Script/LevelSequence") ||
           local_read<uint64_t>(player.address+32)!=actor.address)return false;
        auto actor_player=field(actor_class,"SequencePlayer",720,8,0x6e11d38,80501912059257404ULL);
        auto actor_asset=field(actor_class,"LevelSequenceAsset",728,8,0x6e11d38,80220437082014261ULL);
        auto overrides=field(actor_class,"BindingOverrides",752,8,0x6e11d38,80501912059249180ULL);
        if(!actor_player || !actor_asset || !overrides || local_read<uint64_t>(actor_player+0x70)!=player_class ||
           !named(local_read<uint64_t>(actor_asset+0x70),"LevelSequence","/Script/LevelSequence") ||
           !named(local_read<uint64_t>(overrides+0x70),"MovieSceneBindingOverrides","/Script/MovieScene") ||
           local_read<uint64_t>(actor.address+720)!=player.address || local_read<uint64_t>(actor.address+728)!=asset.address)return false;
        // Constructor-created empty override object is not an effective override.
        // The exact lookup cache, not only reflected BindingData, must be empty.
        const auto override_object=local_read<uint64_t>(actor.address+752);
        if(override_object) {
            CallIdentity observed_override{};
            if(!empty_factory_binding_overrides(*this,override_object,observed_override))return false;
        }
        auto function_owner=local_read<uint64_t>(function.address+32);
        if(!call_is_class(base,function_owner) || !named(function_owner,"MovieSceneSequencePlayer","/Script/MovieScene") ||
           !call_derives(base,player_class,function_owner) || !exact_name(base,function.address+24,"GetBoundObjects") ||
           local_read<uint64_t>(function.address)!=base+0x6dea198 || local_read<uint32_t>(function.address+0xb0)!=67240963 ||
           local_read<uint16_t>(function.address+0xb6)!=40 || local_read<uint16_t>(function.address+0xb8)!=24 ||
           local_read<uint32_t>(function.address+0x58)!=40 || local_read<uint64_t>(function.address+0xd8)!=base+0x2d68650)return false;
        auto sequence=field(function_owner,"Sequence",656,8,0x6e11d38,84451357825704448ULL);
        if(!sequence || !named(local_read<uint64_t>(sequence+0x70),"MovieSceneSequence","/Script/MovieScene") ||
           local_read<uint64_t>(player.address+656)!=asset.address)return false;
        auto input=field(function.address,"ObjectBinding",0,24,0x6e136a0,6755468160532608ULL);
        auto result=field(function.address,"ReturnValue",24,16,0x6e0de80,4503599627372416ULL);
        if(!input || !result || local_read<uint64_t>(function.address+0x50)!=input ||
           local_read<uint64_t>(input+0x18)!=result || local_read<uint64_t>(result+0x18) || (local_read<uint8_t>(result+0x70)&1))return false;
        auto binding_type=local_read<uint64_t>(input+0x70);
        if(!script(binding_type,"MovieSceneObjectBindingID","/Script/MovieScene",24))return false;
        auto guid_field=field(binding_type,"Guid",0,16,0x6e136a0,20266268116386305ULL);
        auto sequence_id=field(binding_type,"SequenceID",16,4,0x6e10a98,20266268116386304ULL);
        auto parent=field(binding_type,"ResolveParentIndex",20,4,0x6e10a98,20266268116386304ULL);
        if(!guid_field || !sequence_id || !parent || local_read<uint64_t>(binding_type+0x50)!=guid_field ||
           local_read<uint64_t>(guid_field+0x18)!=sequence_id || local_read<uint64_t>(sequence_id+0x18)!=parent ||
           local_read<uint64_t>(parent+0x18))return false;
        auto guid_type=local_read<uint64_t>(guid_field+0x70);
        if(!script(guid_type,"Guid","/Script/CoreUObject",16))return false;
        const char* names[]={"A","B","C","D"};auto next=local_read<uint64_t>(guid_type+0x50);
        for(unsigned i=0;i<4;++i) {auto f=field(guid_type,names[i],i*4,4,0x6e10a98,6755469251052033ULL);
            if(!f || next!=f)return false;next=local_read<uint64_t>(f+0x18);}
        if(next)return false;
        auto inner=local_read<uint64_t>(result+0x78);
        if(!inner || local_read<uint64_t>(inner)!=base+0x6e11d38 || local_read<uint64_t>(inner+0x10)!=result ||
           !exact_name(base,local_read<uint64_t>(inner+8),"ObjectProperty") ||
           local_read<uint32_t>(inner+0x30)!=1 || local_read<uint32_t>(inner+0x34)!=8 || local_read<uint32_t>(inner+0x44) ||
           !named(local_read<uint64_t>(inner+0x70),"Object","/Script/CoreUObject"))return false;
        auto dispatch=local_read<uint64_t>(local_read<uint64_t>(player.address)+0x268);
        return (dispatch==base+0x1393330 || dispatch==base+0x332bb90) && context();
    }
    bool validate(const e33_camera_binding::BindingValue& binding)const {
        // Only dispatch needs eight available slots. Context validation remains
        // repeatable while returned objects are already retained in this pool.
        return validate_context(binding) && outputs.preflight(session,8)==StrongLeaseResult::Ok && context();
    }
    void dispatch(void* arguments)const {
        using Dispatch=void(__fastcall*)(void*,void*,void*);
        const auto entry=local_read<uint64_t>(local_read<uint64_t>(player.address)+0x268);
        reinterpret_cast<Dispatch>(entry)(reinterpret_cast<void*>(player.address),reinterpret_cast<void*>(function.address),arguments);
    }
    bool read_pointer(uint64_t address,uint64_t& out)const{out=local_read<uint64_t>(address);return true;}
    bool capture(uint64_t object,CallIdentity& out)const{out=call_capture(base,object);return valid(out);}
    bool retain(CallIdentity& id) {
        TargetStrongReferenceOps ops{base,id};uint64_t token{};
        return outputs.acquire(ops,session,id.address,token)==StrongLeaseResult::Ok && stabilize_retained_identity(ops,id);
    }
    void free_array(uint64_t address)const {
        // Established engine allocator ABI: owned-text-core/owned-text-abi.json;
        // exact GetBoundObjects thunk transfers this allocation to return slot.
        reinterpret_cast<void(__fastcall*)(void*)>(base+0x107c7d0)(reinterpret_cast<void*>(address));
    }
    bool outputs_released()const{return outputs.active()==0;}
};
