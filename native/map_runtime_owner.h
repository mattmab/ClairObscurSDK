#pragma once
#include "engine_profiles.h"
#ifdef E33_RETIRED_WORLD_SESSION
#include "retired_world_target.h"
#include "retired_world_release.h"
#endif
#include <chrono>
#include "static_mesh_registry.h"
#include "map_runtime_readiness.h"
#include "validated_engine_profile_call.h"
#include "npc_interaction_profiles.h"
#pragma warning(push)
#pragma warning(disable:4324)

// Independent gameplay prop ownership. Only shared verified API descriptions
// are reused; no builder owner, camera, picking, input, materials or world edits.
namespace e33_map_runtime {
using namespace e33_mesh;
class Owner {
    CallIdentity ids_[17]{};
    e33_static_mesh_registry::Registry registry_;
    struct Asset {std::string path;CallIdentity mesh;uint64_t lease;};
    std::vector<Asset> assets_;
    uint64_t owner_=0;
    bool quarantined_=false;
#ifdef E33_RETIRED_WORLD_SESSION
    e33_retired_world::Anchor epoch_;bool retiring_=false;
#endif
    uint32_t step_=0;
    struct Row {CallIdentity actor,component;uint64_t lease=0;bool destroyed=false;};
    std::vector<Row> rows_;
    alignas(16) uint8_t args_[512]{};
    static constexpr size_t profiles_[10]={0,1,2,16,17,19,20,21,46,61};
    bool call(uint64_t b,size_t i,CallIdentity recipient) {
        if(i>=10 || !TargetPodSchemaOps{b}.context())return false;
        auto fn=call_identity(b,ids_[i==9?16:6+i]);const auto& p=e33_engine_profiles::profiles[profiles_[i]];
        if(!fn || !exact_name(b,local_read<uint64_t>(fn+16)+24,"Function") ||
           !exact_name(b,fn+24,p.name) || !named(b,local_read<uint64_t>(fn+32),p.owner,"/Script/Engine") ||
           local_read<uint32_t>(fn+0xb0)!=p.flags || local_read<uint16_t>(fn+0xb6)!=p.params ||
           local_read<uint16_t>(fn+0xb8)!=p.returned || local_read<int32_t>(fn+0x58)!=int(p.extent) ||
           local_read<uint64_t>(fn+0xd8)!=b+p.entry || !fields(b,fn,p.fields,p.count)){if(i==8)step_=6002;return false;}
        auto obj=call_identity(b,recipient);
        if(!obj || !call_derives(b,local_read<uint64_t>(obj+16),local_read<uint64_t>(fn+32))){if(i==8)step_=6003;return false;}
        auto pe=local_read<uint64_t>(local_read<uint64_t>(obj)+0x268);
        if(pe!=b+0x1393330 && pe!=b+0x332bb90){if(i==8)step_=6004;return false;}
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(obj),reinterpret_cast<void*>(fn),args_);
        return true;
    }
    void clear(){std::memset(args_,0,sizeof(args_));}
    template<class T> void put(size_t at,T value){std::memcpy(args_+at,&value,sizeof(value));}
    uint64_t pointer(size_t at=0){uint64_t v=0;std::memcpy(&v,args_+at,8);return v;}
    bool current(uint64_t b) {
        if(!call_identity(b,ids_[2]) || !named(b,local_read<uint64_t>(ids_[2].address+16),"World","/Script/Engine"))return false;
        clear();if(!call(b,7,ids_[0]) || pointer()!=call_identity(b,ids_[1]))return false;
        auto outer=ids_[1].address;
        for(int i=0;outer&&i<32;++i,outer=local_read<uint64_t>(outer+32))if(outer==ids_[2].address)return true;
        return false;
    }
    bool valid_pose(const uint8_t* raw) {
        double v[12];std::memcpy(v,raw,96);double norm=0;
        for(auto x:v)if(!std::isfinite(x)||std::abs(x)>1.e8)return false;
        for(int i=0;i<4;++i)norm+=v[i]*v[i];
        if(norm<.999||norm>1.001)return false;
        for(int i=8;i<11;++i)if(std::abs(v[i])<.001||std::abs(v[i])>10000)return false;
        return v[7]==0 && v[11]==0;
    }
    // Reflected, owner-checked scalar observations; no guessed component bits.
    uint64_t readiness_field(uint64_t b,CallIdentity object,const char* owner,const char* name,const char* kind,int width){
        if(!call_identity(b,object))return 0;
        for(auto cls=local_read<uint64_t>(object.address+16);cls;cls=local_read<uint64_t>(cls+0x40)){
            if(!named(b,cls,owner,"/Script/Engine"))continue;
            auto field=local_read<uint64_t>(cls+0x50);
            for(unsigned n=0;field&&n<512;++n,field=local_read<uint64_t>(field+24)){
                if(!exact_name(b,field+32,name))continue;
                const int at=local_read<int32_t>(field+0x44),extent=local_read<int32_t>(cls+0x58);
                if(local_read<uint64_t>(field+16)!=(cls|1)||!exact_name(b,local_read<uint64_t>(field+8),kind)||
                   local_read<int32_t>(field+0x30)!=1||local_read<int32_t>(field+0x34)!=width||at<0||at>extent-width)return 0;
                return field;
            }
            return 0;
        }
        return 0;
    }
    bool readiness_bool(uint64_t b,CallIdentity object,const char* owner,const char* name,bool& value){
        const auto field=readiness_field(b,object,owner,name,"BoolProperty",1);if(!field)return false;
        const auto encoding=local_read<uint32_t>(field+0x70);const auto mask=uint8_t(encoding>>24);
        if(uint8_t(encoding>>8)||!mask)return false;
        value=(local_read<uint8_t>(object.address+local_read<int32_t>(field+0x44))&mask)!=0;return true;
    }
    bool readiness_save(uint64_t b,const uint8_t* raw){
#ifdef E33_RETIRED_WORLD_SESSION
        e33_retired_world::TargetOps proof{b};
        if(!epoch_.established()||!proof.current_binding(epoch_.engine(),epoch_.viewport(),ids_[2])||
           !proof.controller_world(ids_[0],ids_[2]))return false;
#else
        return false; // No verified active-viewport epoch on this native build.
#endif
        CallIdentity gi{},manager{};std::memcpy(&gi,raw+216,16);std::memcpy(&manager,raw+232,16);
        uint32_t slot=0;std::memcpy(&slot,raw+2004,4);if(slot>0x7fffffffU)return false;
        if(!call_identity(b,gi)||!call_identity(b,manager)||
           !picto_class(b,gi.address,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom")||
           !picto_class(b,manager.address,"BP_SaveManager_C","/Game/Gameplay/Save/BP_SaveManager"))return false;
        const auto world_gi=picto_field(b,ids_[2].address,"OwningGameInstance","ObjectProperty",472,8);
        const auto gi_manager=picto_field(b,gi.address,"SaveManager","ObjectProperty",480,8);
        const auto manager_gi=picto_field(b,manager.address,"GameInstanceReference","ObjectProperty",248,8);
        uint64_t loaded_field=0,loading_field=0,slot_field=0;
        const auto loaded=picto_field(b,gi.address,"SaveLoaded","BoolProperty",2680,1,&loaded_field);
        const auto loading=picto_field(b,manager.address,"LoadIsInProgress","BoolProperty",169,1,&loading_field);
        const auto selected=picto_field(b,manager.address,"SelectedSlot","IntProperty",288,4,&slot_field);
        if(!world_gi||local_read<uint64_t>(world_gi)!=gi.address||!gi_manager||local_read<uint64_t>(gi_manager)!=manager.address||
           !manager_gi||local_read<uint64_t>(manager_gi)!=gi.address||!loaded||!loading||!selected)return false;
        const auto strict=[&](uint64_t field,uint64_t object,uint64_t table){return local_read<uint64_t>(field)==b+table&&
            local_read<uint64_t>(field+16)==(local_read<uint64_t>(object+16)|1)&&local_read<uint64_t>(field+0x38)==0x8001040010205ULL;};
        return strict(loaded_field,gi.address,0x6e119b0)&&strict(loading_field,manager.address,0x6e119b0)&&
            strict(slot_field,manager.address,0x6e10a98)&&local_read<uint32_t>(loaded_field+0x70)==0xff010001U&&
            local_read<uint32_t>(loading_field+0x70)==0xff010001U&&local_read<uint8_t>(loaded)==1&&
            local_read<uint8_t>(loading)==0&&local_read<int32_t>(selected)==int32_t(slot);
    }
    bool readiness(uint64_t b,MeshPacket& packet){
        auto* raw=reinterpret_cast<uint8_t*>(&packet);CallIdentity query[6]{},expected[2]{};
        std::memcpy(query,raw+88,sizeof(query));std::memcpy(expected,raw+184,sizeof(expected));
        const auto same=[](CallIdentity a,CallIdentity z){return a.index==z.index&&a.serial==z.serial&&a.address==z.address;};
        uint32_t require_owned=0;std::memcpy(&require_owned,raw+2000,4);
        if(require_owned>1||!same(expected[0],ids_[2])||!same(expected[1],ids_[1])||!current(b)||!readiness_save(b,raw)||
           !call_identity(b,query[0])||!named(b,query[0].address,"Default__KismetSystemLibrary","/Script/Engine"))return false;
        uint32_t report[13]={uint32_t(rows_.size()),0,0,0,0,0,0,1,0,0,0,0,0};
        const auto rendered=[&](CallIdentity component,bool& value){
            alignas(16) uint8_t frame[8]{};const float tolerance=.25f;std::memcpy(frame,&tolerance,4);
            if(!e33_engine_profile_call::invoke(b,query[4],component,e33_map_readiness::rendered,frame)||frame[4]>1)return false;
            value=frame[4]!=0;return true;
        };
        for(const auto& row:rows_){
            if(row.destroyed||!call_identity(b,row.actor)||!call_identity(b,row.component)||local_read<uint64_t>(row.component.address+32)!=row.actor.address)return false;
            const auto mesh_field=readiness_field(b,row.component,"StaticMeshComponent","StaticMesh","ObjectProperty",8);
            if(!mesh_field)return false;
            const auto mesh=call_capture(b,local_read<uint64_t>(row.component.address+local_read<int32_t>(mesh_field+0x44)));
            if(!call_identity(b,mesh)||!call_derives(b,local_read<uint64_t>(mesh.address+16),ids_[5].address))return false;
            ++report[1];
            alignas(16) uint8_t frame[464]{};
            if(!e33_engine_profile_call::invoke(b,query[3],row.component,e33_npc_interaction::GetCollisionEnabled,frame))return false;
            if(frame[0]>3)return false;if(frame[0]==1||frame[0]==3)++report[2];
            bool visible=false,hidden=true,actor_hidden=true;
            if(!readiness_bool(b,row.component,"SceneComponent","bVisible",visible)||
               !readiness_bool(b,row.component,"SceneComponent","bHiddenInGame",hidden)||
               !readiness_bool(b,row.actor,"Actor","bHidden",actor_hidden))return false;
            if(visible&&!hidden&&!actor_hidden)++report[3];
            bool recently_rendered=false;if(!rendered(row.component,recently_rendered))return false;
            if(recently_rendered)++report[8];
        }
        const auto streams=readiness_field(b,ids_[2],"World","StreamingLevels","ArrayProperty",16);
        if(!streams||local_read<uint64_t>(streams)!=b+0x6e0de80||local_read<int32_t>(streams+0x44)!=136||
           local_read<uint64_t>(streams+0x38)!=0x144000000002200ULL||(local_read<uint8_t>(streams+0x70)&1))return false;
        const auto inner=local_read<uint64_t>(streams+0x78);
        if(!inner||local_read<uint64_t>(inner+16)!=streams||!exact_name(b,local_read<uint64_t>(inner+8),"ObjectProperty")||
           local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=8||
           !named(b,local_read<uint64_t>(inner+0x70),"LevelStreaming","/Script/Engine")||!call_is_class(b,local_read<uint64_t>(inner+0x70)))return false;
        const auto array=ids_[2].address+136;const auto stream_data=local_read<uint64_t>(array);
        const auto count=local_read<int32_t>(array+8),capacity=local_read<int32_t>(array+12);
        if(count<0||count>4096||capacity<count||capacity>65536||(count&&(!stream_data||(stream_data&7))))return false;
        for(int i=0;i<count;++i){
            const auto level=call_capture(b,local_read<uint64_t>(stream_data+8*i));
            if(!call_identity(b,level)||!call_derives(b,local_read<uint64_t>(level.address+16),local_read<uint64_t>(inner+0x70)))return false;
            alignas(16) uint8_t frame[8]{};
            if(!e33_engine_profile_call::invoke(b,query[5],level,e33_map_readiness::streaming,frame)||frame[0]>1)return false;
            ++report[9];if(frame[0])++report[10];
        }
        clear();if(!call(b,4,ids_[1]))return false;const auto capsule=call_capture(b,pointer());
        if(!call_identity(b,capsule)||local_read<uint64_t>(capsule.address+32)!=ids_[1].address)return false;
        const auto h=readiness_field(b,capsule,"CapsuleComponent","CapsuleHalfHeight","FloatProperty",4);
        const auto r=readiness_field(b,capsule,"CapsuleComponent","CapsuleRadius","FloatProperty",4);
        if(!h||!r)return false;
        clear();if(!call(b,5,capsule))return false;
        double transform[12]{};std::memcpy(transform,args_,96);if(!valid_pose(args_))return false;
        const double radius=local_read<float>(capsule.address+local_read<int32_t>(r+0x44))*std::max(std::abs(transform[8]),std::abs(transform[9]));
        const double height=local_read<float>(capsule.address+local_read<int32_t>(h+0x44))*std::abs(transform[10]);
        e33_map_readiness::Support support{};
        const auto invoke=[&](unsigned stage,uint8_t* frame){return current(b)&&e33_engine_profile_call::invoke(b,query[stage+1],stage?ids_[3]:query[0],e33_engine_profiles::profiles[14+stage],frame);};
        bool render_query_valid=true;
        const auto owned=[&](uint64_t actor,uint64_t component){
            const bool is_owned=std::any_of(rows_.begin(),rows_.end(),[&](const Row& row){return row.actor.address==actor&&row.component.address==component&&call_identity(b,row.actor)&&call_identity(b,row.component);});
            const auto hit_component=call_capture(b,component);bool recent=false;
            if(!call_identity(b,hit_component)||!rendered(hit_component,recent))render_query_valid=false;
            if(recent){++report[11];if(is_owned)++report[12];}return is_owned;
        };
        if(!e33_map_readiness::support(invoke,owned,ids_[1].address,transform+4,radius,height,support)||!render_query_valid||!current(b)||!readiness_save(b,raw))return false;
        report[4]=support.samples;report[5]=support.hits;report[6]=support.owned;
        if(report[0]==report[1])report[7]|=2;
        if(support.hits==5&&(!require_owned||support.owned==5))report[7]|=4;
        if(report[0]==report[3])report[7]|=8;
        // Vanilla floors may use invisible collision proxies. Require render
        // evidence for our visible owned support, not for engine-only proxies.
        if((report[7]&8)&&!report[10]&&report[12]==support.owned)report[7]|=16;
        std::memcpy(raw+4096,report,sizeof(report));std::memcpy(raw+4152,support.heights,sizeof(support.heights));return true;
    }
    template<class Pool> bool spawn(uint64_t b,uint64_t session,Pool& pool,CallIdentity mesh,const uint8_t* pose,Row& result) {
        step_=1;
        if(rows_.size()>=6000 || !current(b) || !valid_pose(pose) || !call_identity(b,mesh) ||
           !call_derives(b,local_read<uint64_t>(mesh.address+16),ids_[5].address))return false;
        clear();put(0,ids_[0].address);put(8,ids_[4].address);std::memcpy(args_+16,pose,96);args_[112]=1;
        step_=2;
        if(!call(b,0,ids_[3]))return false;
        auto actor=call_capture(b,pointer(136));if(!actor.address)return false;
        step_=3;
        rows_.push_back({actor,{},0,false});auto& row=rows_.back();
        TargetStrongReferenceOps ops{b,actor};
        const auto acquired=pool.acquire(ops,session,actor.address,row.lease);
        if(acquired!=StrongLeaseResult::Ok){if(acquired==StrongLeaseResult::Quarantined)quarantined_=true;return false;}
        step_=4;
        clear();if(!call(b,4,actor))return false;row.component=call_capture(b,pointer());
        if(!row.component.address)return false;
        step_=5;
        clear();args_[0]=2;if(!call(b,3,row.component))return false;
        step_=6;
        clear();if(!call(b,4,actor))return false;row.component=call_capture(b,pointer());
        if(!row.component.address)return false;
        clear();put(0,mesh.address);if(!call(b,8,row.component))return false;
        if(!args_[8]){step_=6005;return false;}
        step_=7;
        clear();put(0,actor.address);std::memcpy(args_+16,pose,96);
        if(!call(b,1,ids_[3])||pointer(120)!=actor.address)return false;
        step_=8;
        clear();if(!call(b,4,actor))return false;row.component=call_capture(b,pointer());
        if(!row.component.address)return false;
        step_=9;
        clear();args_[0]=2;if(!call(b,3,row.component))return false;
        step_=10;
        clear();std::memcpy(args_,pose,96);args_[352]=1;
        if(!call(b,6,row.component))return false;
        result=row;return true;
    }
public:
    void quarantine(){quarantined_=true;}
#ifdef E33_RETIRED_WORLD_SESSION
    bool protects(uint64_t token)const{
        if(!owner_||!token)return false;
        if(token==epoch_.token())return true;
        for(const auto&row:rows_)if(row.lease==token)return true;
        for(const auto&asset:assets_)if(asset.lease==token)return true;
        return false;
    }
#endif
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool) {
        if(quarantined_)return 2109;
#ifdef E33_RETIRED_WORLD_SESSION
        if(owner_){
            e33_retired_world::TargetOps proof{b};
            if(!epoch_.established()){
                if(!rows_.empty()||!assets_.empty())return 2109;
                const auto released=epoch_.release(proof,pool,session);if(released)return released;
                epoch_.reset();owner_=0;retiring_=false;return 0;
            }
            const auto result=epoch_.prove(proof);
            if(result==e33_retired_world::Result::Pending)return 407;
            if(result==e33_retired_world::Result::Unknown)return 2109;
            if(result==e33_retired_world::Result::Retired)retiring_=true;
        }
#endif
#ifdef E33_RETIRED_WORLD_SESSION
        if(retiring_){
            const auto released=e33_retired_world::release_reverse(rows_,[&](const Row&row)->uint32_t{
                if(!row.lease)return 0;
                if(!pool.owns_retirement_storage(session,row.lease,row.actor.address))return 2109;
                TargetStrongReferenceOps refs{b,{}};const auto result=pool.release(refs,session,row.lease);
                return result==StrongLeaseResult::Ok?0:result==StrongLeaseResult::Deferred?407:2107;
            });
            if(released)return released;
        }
#endif
        while(!rows_.empty()) {
            auto& row=rows_.back();
            if(!row.destroyed &&
#ifdef E33_RETIRED_WORLD_SESSION
               !retiring_ &&
#endif
               call_identity(b,row.actor)){clear();if(!call(b,2,row.actor))return 2106;row.destroyed=true;}
            TargetStrongReferenceOps ops{b,{-1,0,0}};
            if(row.lease){const auto released=pool.release(ops,session,row.lease);
                if(released!=StrongLeaseResult::Ok)return released==StrongLeaseResult::Deferred?407:2107;}
            rows_.pop_back();
        }
        while(!assets_.empty()) {
            TargetStrongReferenceOps ops{b,{-1,0,0}};
#ifdef E33_RETIRED_WORLD_SESSION
            if(retiring_&&!pool.owns_retirement_storage(session,assets_.back().lease,assets_.back().mesh.address))return 2109;
#endif
            const auto released=pool.release(ops,session,assets_.back().lease);
            if(released!=StrongLeaseResult::Ok)return released==StrongLeaseResult::Deferred?407:2107;
            assets_.pop_back();
        }
#ifdef E33_RETIRED_WORLD_SESSION
        e33_retired_world::TargetOps proof{b};const auto released=epoch_.release(proof,pool,session);
        if(released)return released;
        epoch_.reset();retiring_=false;
#endif
        owner_=0;return 0;
    }
    template<class Pool> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& p) {
        auto* raw=reinterpret_cast<uint8_t*>(&p);const auto op=p.operation;
        if(p.version!=3 || p.error || p.state || !p.owner || (op!=107&&(op<93 || op>
#ifdef E33_RETIRED_WORLD_SESSION
            98
#else
            97
#endif
))){p.error=2100;return;}
        if(quarantined_){p.error=2109;
#ifdef E33_RETIRED_WORLD_SESSION
            if(op==98){p.state=owner_?1:0;const auto count=uint32_t(rows_.size());std::memcpy(raw+3564,&count,4);}
#endif
            return;}
        if(owner_ && owner_!=p.owner){p.error=2101;return;}
#ifdef E33_RETIRED_WORLD_SESSION
        if(op==98){
            if(std::any_of(raw+24,raw+sizeof(p),[](uint8_t c){return c!=0;})){p.error=2100;return;}
            if(owner_&&epoch_.established()){e33_retired_world::TargetOps proof{b};const auto result=epoch_.prove(proof);
                if(result!=e33_retired_world::Result::Retired){p.error=result==e33_retired_world::Result::Pending?407:2109;p.state=1;const auto count=uint32_t(rows_.size());std::memcpy(raw+3564,&count,4);return;}
                retiring_=true;
            }
            p.error=close(b,session,pool);p.state=owner_?1:0;
            const auto count=uint32_t(rows_.size());std::memcpy(raw+3564,&count,4);return;
        }
#endif
        if(op==93) {
            if(owner_||!rows_.empty()){p.error=2102;return;}
            std::memcpy(ids_,raw+88,sizeof(ids_));
            for(auto id:ids_)if(!call_identity(b,id)){p.error=2103;return;}
            if(!named(b,ids_[4].address,"StaticMeshActor","/Script/Engine") || !call_is_class(b,ids_[4].address) ||
               !named(b,ids_[5].address,"StaticMesh","/Script/Engine") || !call_is_class(b,ids_[5].address) || !current(b)){p.error=2103;return;}
#ifdef E33_RETIRED_WORLD_SESSION
            e33_retired_world::TargetOps proof{b};e33_retired_world::Snapshot observed{};
            if(!proof.observe(observed)||!e33_retired_world::same(observed.world,ids_[2])||!proof.controller_world(ids_[0],ids_[2])){p.error=2103;return;}
#endif
            owner_=p.owner;
#ifdef E33_RETIRED_WORLD_SESSION
            const auto anchored=epoch_.capture(proof,pool,session,ids_[0]);
            if(anchored){p.error=anchored;p.state=1;return;}
            ids_[2]=epoch_.world();
#endif
        } else if(op==95) {
            p.error=close(b,session,pool);
        } else if(!owner_){p.error=2102;return;}
        else if(op==107){
            if(std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;})||
               std::any_of(raw+248,raw+2000,[](uint8_t c){return c!=0;})||
               std::any_of(raw+2008,raw+sizeof(p),[](uint8_t c){return c!=0;})||!readiness(b,p)){p.error=2115;return;}
        }
        else if(op==97) {
            const auto* text=reinterpret_cast<const char*>(raw+2000);
            const auto length=strnlen_s(text,512);
            if(!length||length>=512||!current(b)){p.error=2110;return;}
            const std::string path(text,length);
            auto cached=std::find_if(assets_.begin(),assets_.end(),[&](const Asset& a){return a.path==path;});
            CallIdentity mesh{};
            if(cached!=assets_.end())mesh=cached->mesh;
            else {
                if(assets_.size()>=6000||!registry_.ensure(b,ids_[5])){p.error=2110;return;}
                const auto names=registry_.names(path);
                if(!names.first||!names.second){p.error=2111;return;}
                clear();put(8,names.first);put(16,names.second);
                if(!call(b,9,ids_[15])){p.error=2112;return;}
                mesh=call_capture(b,pointer(40));
                if(!call_identity(b,mesh)||!call_derives(b,local_read<uint64_t>(mesh.address+16),ids_[5].address)){p.error=2113;return;}
                assets_.push_back({path,mesh,0});auto& asset=assets_.back();
                TargetStrongReferenceOps ops{b,mesh};
                const auto acquired=pool.acquire(ops,session,mesh.address,asset.lease);
                if(acquired!=StrongLeaseResult::Ok){if(acquired==StrongLeaseResult::Quarantined)quarantined_=true;assets_.pop_back();p.error=2114;return;}
            }
            if(!call_identity(b,mesh)){p.error=2113;return;}
            std::memcpy(raw+4096,&mesh,16);
        }
        else if(op==94) {
            uint32_t count=0;std::memcpy(&count,raw+2000,4);
            if(!count||count>32){p.error=2104;return;}
            // Validate every row before the first spawn in this packet.
            for(uint32_t i=0;i<count;++i){CallIdentity mesh{};const auto* r=raw+4096+128*i;std::memcpy(&mesh,r,16);
                if(!call_identity(b,mesh)||!call_derives(b,local_read<uint64_t>(mesh.address+16),ids_[5].address)||!valid_pose(r+16)){p.error=2104;return;}}
            if(rows_.size()+count>6000){p.error=2104;return;}
            uint32_t done=0;
            const auto started=std::chrono::steady_clock::now();
            for(;done<count;){auto* r=raw+4096+128*done;CallIdentity mesh{};Row result{};std::memcpy(&mesh,r,16);
                if(!spawn(b,session,pool,mesh,r+16,result)){p.error=2105;p.step=step_;break;}
                std::memcpy(r+112,&result.actor,16);++done;
                if(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count()>=4.)break;
            }
            std::memcpy(raw+3560,&done,4);
        } else if(op==96) {
            uint32_t index=0;std::memcpy(&index,raw+2000,4);
            if(index>=rows_.size()||!call_identity(b,rows_[index].actor)||!call_identity(b,rows_[index].component)){p.error=2108;return;}
            clear();if(!call(b,5,rows_[index].component)){p.error=2108;return;}
            std::memcpy(raw+4096,&rows_[index].actor,16);std::memcpy(raw+4112,args_,96);
        }
        const auto count=uint32_t(rows_.size());std::memcpy(raw+3564,&count,4);p.state=owner_?1:0;
    }
};
}
#pragma warning(pop)
