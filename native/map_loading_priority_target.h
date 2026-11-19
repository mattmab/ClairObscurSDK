#pragma once
#include "map_loading_priority.h"
#include "story_npc_config_profiles.h"
#include "validated_engine_profile_call.h"

namespace e33_map_loading_priority {
inline CallIdentity call_id(Identity id){return {id.index,id.serial,id.address};}
inline Identity priority_id(CallIdentity id){return {id.index,id.serial,id.address};}
class Target {
    CallIdentity cdo_{},setter_{};
    Binding binding_{};
    bool configured_=false;
    static bool live(uint64_t base,CallIdentity id){
        return id.serial>0&&call_identity(base,id)==id.address&&id.address&&!(local_read<uint32_t>(id.address+8)&0x40018030U);
    }
    static bool native_class(uint64_t base,uint64_t object,const char* name,uint32_t extent=0){
        const auto cls=local_read<uint64_t>(object+16);
        return call_capture(base,cls).address&&call_is_class(base,cls)&&
            e33_mesh::named(base,cls,name,"/Script/Engine")&&(!extent||local_read<uint32_t>(cls+0x58)==extent);
    }
    static bool viewport_class(uint64_t base,uint64_t object){
        auto cls=local_read<uint64_t>(object+16);
        for(unsigned n=0;cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40))
            if(call_capture(base,cls).address&&call_is_class(base,cls)&&
               e33_mesh::named(base,cls,"GameViewportClient","/Script/Engine"))return true;
        return false;
    }
    static uint64_t link(uint64_t base,uint64_t object,unsigned which){
        const auto& s=links[which];const auto cls=local_read<uint64_t>(object+16);
        uint64_t field=0;const auto storage=picto_field(base,object,s.name,"ObjectProperty",s.offset,8,&field);
        if(!storage||!field||!e33_mesh::named(base,cls,s.owner,"/Script/Engine")||
           local_read<uint64_t>(field)!=base+object_property_vtable||local_read<uint64_t>(field+16)!=(cls|1)||
           local_read<uint64_t>(field+0x38)!=s.flags||local_read<uint32_t>(field+0x30)!=1||
           !e33_mesh::named(base,local_read<uint64_t>(field+0x70),s.constraint,"/Script/Engine"))return 0;
        return local_read<uint64_t>(storage);
    }
    static bool graph(uint64_t base,const Binding& binding,Observation& out){
        if(!TargetPodSchemaOps{base}.context()||!valid(binding)||!live(base,call_id(binding.world))||
           !live(base,call_id(binding.level))||!live(base,call_id(binding.settings))||!live(base,call_id(binding.viewport)))return false;
        const auto world=binding.world.address,level=binding.level.address,settings=binding.settings.address;
        if(!native_class(base,world,"World",world_extent)||!native_class(base,level,"Level",level_extent)||
           !native_class(base,settings,"WorldSettings",settings_extent)||
           !viewport_class(base,binding.viewport.address)||
           link(base,world,0)!=level||link(base,level,1)!=world||link(base,level,2)!=settings||
           local_read<uint64_t>(level+32)!=world||local_read<uint64_t>(settings+32)!=level||
           zone_ref(base,binding.viewport.address,"World")!=world)return false;
        const auto cls=local_read<uint64_t>(settings+16);uint64_t field=0;
        const auto storage=picto_field(base,settings,priority_name,"BoolProperty",priority_offset,1,&field);
        if(!storage||!field||local_read<uint64_t>(field)!=base+bool_property_vtable||
           local_read<uint64_t>(field+16)!=(cls|1)||local_read<uint64_t>(field+0x38)!=priority_flags||
           local_read<uint32_t>(field+0x30)!=1||local_read<uint32_t>(field+0x70)!=priority_encoding||
           local_read<uint64_t>(base+bool_property_vtable+0x78)!=base+0x10044f0||
           local_read<uint64_t>(base+bool_property_vtable+0x80)!=base+0x10044f0)return false;
        out={binding,field,local_read<uint8_t>(storage)};return TargetPodSchemaOps{base}.context();
    }
    bool setter_valid(uint64_t base)const{
        if(!configured_||!live(base,setter_)||!call_identity(base,cdo_)||
           (local_read<uint32_t>(cdo_.address+8)&0x40018000U)||
           !e33_mesh::named(base,cdo_.address,"Default__KismetSystemLibrary","/Script/Engine")||
           !native_class(base,cdo_.address,"KismetSystemLibrary")||
           !exact_name(base,local_read<uint64_t>(setter_.address+16)+24,"Function"))return false;
        e33_engine_profile_call::TargetOps call{base,setter_.address,cdo_.address,e33_story_npc::functions[2],nullptr};
        return call.context()&&call.identities()&&call.exact_profile()&&call.recipient_derives()&&call.dispatch_entry();
    }
public:
    bool configured()const{return configured_;}
    const Binding& binding()const{return binding_;}
    bool configure(uint64_t base,const CallIdentity* ids){
        if(configured_||!ids||ids[0].serial<=0||ids[1].serial<=0)return false;
        cdo_=ids[0];setter_=ids[1];configured_=true;
        if(!setter_valid(base)){configured_=false;cdo_=setter_={};return false;}return true;
    }
    template<class Pool> bool prepare(uint64_t base,uint64_t session,Pool& pool,uint64_t owner,uint64_t hold,
            CallIdentity player,CallIdentity world){
        if(!configured_||!TargetPodSchemaOps{base}.context()||!live(base,player)||!live(base,world)||!setter_valid(base))return false;
        const auto level=link(base,world.address,0),settings=level?link(base,level,2):0;
        const auto viewport=zone_ref(base,player.address,"ViewportClient");
        if(!level||!settings||!viewport||zone_ref(base,viewport,"World")!=world.address)return false;
        CallIdentity ids[]={world,call_capture(base,level),call_capture(base,settings),call_capture(base,viewport)};
        for(auto& id:ids){
            if(!id.address)return false;
            if(id.serial>0)continue;
            TargetStrongReferenceOps refs{base,id};uint64_t token=0;
            if(pool.acquire(refs,session,id.address,token)!=StrongLeaseResult::Ok)return false;
            const auto stable=stabilize_retained_identity(refs,id);
            const auto released=pool.release(refs,session,token);
            if(!stable||released!=StrongLeaseResult::Ok)return false;
        }
        Binding candidate{owner,hold,priority_id(ids[0]),priority_id(ids[1]),priority_id(ids[2]),priority_id(ids[3])};
        Observation observed{};if(!graph(base,candidate,observed))return false;
        binding_=candidate;return true;
    }
    bool inspect(uint64_t base,Observation& out)const{return graph(base,binding_,out);}
    Proof inspect_owned(uint64_t base,const Binding& binding,Observation& out)const{
        if(!TargetPodSchemaOps{base}.context())return Proof::Unresolved;
        // A missing controller does not block restoration. The exact retained
        // weak viewport/world relation supplies authority independently of it.
        if(graph(base,binding,out))return Proof::Live;
        if(!TargetPodSchemaOps{base}.context())return Proof::Unresolved;
        const auto world=call_id(binding.world),settings=call_id(binding.settings),viewport=call_id(binding.viewport);
        const bool expired=!call_identity(base,world)||!call_identity(base,settings);
        if(expired&&TargetPodSchemaOps{base}.context()&&(!call_identity(base,world)||!call_identity(base,settings)))return Proof::Retired;
        if(!live(base,viewport)||!viewport_class(base,viewport.address))return Proof::Unresolved;
        const auto first=call_capture(base,zone_ref(base,viewport.address,"World"));
        const auto second=call_capture(base,zone_ref(base,viewport.address,"World"));
        // Two same-callback registry observations suffice for a DIFFERENT
        // address. Do not wait for the new World to gain its first weak serial;
        // that would block its own subsequent gate admission. Address reuse
        // instead takes the expired exact old-generation branch above.
        if(first.address&&first.address!=world.address&&first.index==second.index&&first.serial==second.serial&&
           first.address==second.address&&call_identity(base,first)==first.address&&
           !(local_read<uint32_t>(first.address+8)&0x40018030U)&&native_class(base,first.address,"World",world_extent)&&
           TargetPodSchemaOps{base}.context())return Proof::Retired;
        return Proof::Unresolved;
    }
    Dispatch set_original(uint64_t base,const Observation& before,bool value)const{
        Observation now{};
        if(!setter_valid(base)||inspect_owned(base,before.binding,now)!=Proof::Live||
           !same_target(before,now)||before.byte!=now.byte)return Dispatch::NotDispatched;
        alignas(16) uint8_t args[32]{};
        std::memcpy(args,&before.binding.settings.address,8);
        std::memcpy(args+8,reinterpret_cast<void*>(before.property+32),8);
        args[16]=uint8_t(value);
        return e33_engine_profile_call::invoke(base,setter_,cdo_,e33_story_npc::functions[2],args)?Dispatch::Returned:Dispatch::NotDispatched;
    }
    void clear(){configured_=false;cdo_=setter_={};binding_={};}
};
}
