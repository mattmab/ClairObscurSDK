#pragma once
#include "story_layer_batch.h"
#include "zone_travel.h"

namespace e33_story_layers {
inline bool live(uint64_t base,const CallIdentity& world_id,const CallIdentity& controller_id,const RetainedCallPacket& packet,uint32_t mode){
    const auto world=call_identity(base,world_id),pc=call_identity(base,controller_id);
    const auto manager=call_identity(base,packet.call.target),function=call_identity(base,packet.call.function);
    const auto layer=call_identity(base,packet.call.objects[0].identity);
    if(!world||!pc||!manager||!function||!layer)return false;
    for(const auto object:{world,pc,manager,layer})if(local_read<uint32_t>(object+8)&0x40018030U)return false;
    const auto named=[&](uint64_t object,const char* name){return zone_named(base,local_read<uint64_t>(object+16),name,"/Script/Engine");};
    if(!named(world,"World")||!named(manager,"DataLayerManager")||!named(layer,"DataLayerInstanceWithAsset"))return false;
    const auto fn_owner=local_read<uint64_t>(function+32);
    if(!zone_named(base,fn_owner,"DataLayerManager","/Script/Engine")||
       !exact_name(base,function+24,mode==1?"GetDataLayerInstanceRuntimeState":"SetDataLayerInstanceRuntimeState"))return false;
    const auto player=zone_ref(base,pc,"Player"),viewport=zone_ref(base,player,"ViewportClient");
    if(!player||!viewport||zone_ref(base,player,"PlayerController")!=pc||zone_ref(base,viewport,"World")!=world)return false;
    const auto derives=[&](uint64_t object,const char* name){
        auto cls=local_read<uint64_t>(object+16);
        for(unsigned i=0;cls&&i<32;++i,cls=local_read<uint64_t>(cls+0x40))
            if(zone_named(base,cls,name,"/Script/Engine"))return true;
        return false;
    };
    if(!derives(pc,"PlayerController")||!derives(player,"LocalPlayer")||!derives(viewport,"GameViewportClient")||
       (local_read<uint32_t>(player+8)&0x40018030U)||(local_read<uint32_t>(viewport+8)&0x40018030U))return false;
    // A LocalPlayer can briefly point at the outgoing controller after its
    // viewport switches World. The controller must belong to this World too.
    uint64_t pc_world=0;
    auto outer=local_read<uint64_t>(pc+32);
    for(unsigned outer_depth=0;outer&&outer_depth<8;++outer_depth,outer=local_read<uint64_t>(outer+32)){
        if(!call_capture(base,outer).address||(local_read<uint32_t>(outer+8)&0x40018030U))return false;
        if(named(outer,"World")){pc_world=outer;break;}
        // Only the normal Level -> World actor ownership chain is accepted.
        if(!named(outer,"Level"))return false;
    }
    if(pc_world!=world)return false;
    const auto level=zone_ref(base,world,"PersistentLevel"),settings=zone_ref(base,level,"WorldSettings"),partition=zone_ref(base,settings,"WorldPartition");
    const auto container=zone_ref(base,level,"WorldDataLayers");
    if(!level||!settings||!partition||!container||!named(level,"Level")||!named(settings,"WorldSettings")||
       !named(partition,"WorldPartition")||!named(container,"WorldDataLayers")||zone_ref(base,level,"OwningWorld")!=world||
       zone_ref(base,partition,"DataLayerManager")!=manager)return false;
    return local_read<uint64_t>(manager+32)==partition&&local_read<uint64_t>(partition+32)==settings&&
        local_read<uint64_t>(settings+32)==level&&local_read<uint64_t>(level+32)==world&&
        local_read<uint64_t>(container+32)==level&&local_read<uint64_t>(layer+32)==container;
}
// Callbacks are the same retention/enum/POD validators as SessionRetainedInvoke.
struct RuntimeOps {
    uint64_t base;
    const CallPodValidation* pod;
    const CallEntryValidation* entry;
    uint32_t (*preflight)(void*,const CallPacket&);
    uint32_t (*capture)(void*,uint32_t,CallIdentity&);
    bool (*enum_validate)(uint64_t,uint64_t,const CallIdentity&,const uint8_t*);
    bool validate(const CallIdentity& world,const CallIdentity& pc,RetainedCallPacket& p,uint32_t mode){
        if(!live(base,world,pc,p,mode))return false;
        CallRetention retention{&p,preflight,capture};CallEnumValidation enums{&p,enum_validate};
        return !reflected_call(base,p.call,&retention,pod,nullptr,&enums,true,entry);
    }
    void dispatch(const CallIdentity& world,const CallIdentity& pc,RetainedCallPacket& p,uint32_t mode){
        if(!live(base,world,pc,p,mode)){p.call.error=rejected;return;}
        CallRetention retention{&p,preflight,capture};CallEnumValidation enums{&p,enum_validate};
        p.call.error=reflected_call(base,p.call,&retention,pod,nullptr,&enums,false,entry);
    }
};
}
