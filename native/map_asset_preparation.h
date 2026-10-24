#pragma once
#include "engine_profiles.h"
#include "static_mesh_registry.h"
#include "stable_identity.h"

// Process-owned static assets only. No actor, pawn, controller or World is
// captured here; all engine dispatch remains on the existing game-thread pump.
namespace e33_map_asset_preparation {
using namespace e33_mesh;
class Owner {
    CallIdentity library_{},function_{},mesh_class_{};
    struct Asset {std::string path;CallIdentity mesh;uint64_t lease=0;};
    std::vector<Asset> assets_;
    e33_static_mesh_registry::Registry registry_;
    uint64_t owner_=0;bool quarantined_=false;
    bool load(uint64_t b,uint64_t package,uint64_t name,CallIdentity& result){
        if(!TargetPodSchemaOps{b}.context())return false;
        auto fn=call_identity(b,function_),object=call_identity(b,library_);
        const auto&p=e33_engine_profiles::profiles[61];
        if(!fn||!object||!named(b,local_read<uint64_t>(fn+32),p.owner,"/Script/Engine")||
           !exact_name(b,fn+24,p.name)||local_read<uint32_t>(fn+0xb0)!=p.flags||
           local_read<uint16_t>(fn+0xb6)!=p.params||local_read<uint16_t>(fn+0xb8)!=p.returned||
           local_read<int32_t>(fn+0x58)!=int(p.extent)||local_read<uint64_t>(fn+0xd8)!=b+p.entry||
           !fields(b,fn,p.fields,p.count)||!call_derives(b,local_read<uint64_t>(object+16),local_read<uint64_t>(fn+32)))return false;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
        if(pe!=b+0x1393330&&pe!=b+0x332bb90)return false;
        alignas(16) uint8_t args[48]{};
        std::memcpy(args+8,&package,8);std::memcpy(args+16,&name,8);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(fn),args);
        uint64_t mesh=0;std::memcpy(&mesh,args+40,8);result=call_capture(b,mesh);
        return call_identity(b,result)&&call_derives(b,local_read<uint64_t>(mesh+16),mesh_class_.address);
    }
public:
    void quarantine(){quarantined_=true;}
    bool protects(uint64_t token)const{
        if(!token)return false;
        for(const auto&asset:assets_)if(asset.lease==token)return true;
        return false;
    }
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool){
        if(quarantined_)return 2169;
        while(!assets_.empty()){
            TargetStrongReferenceOps ops{b,{-1,0,0}};
            const auto result=pool.release(ops,session,assets_.back().lease);
            if(result!=StrongLeaseResult::Ok)return result==StrongLeaseResult::Deferred?407:2167;
            assets_.pop_back();
        }
        owner_=0;library_=function_=mesh_class_={};return 0;
    }
    template<class Pool> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket&p){
        auto*raw=reinterpret_cast<uint8_t*>(&p);
        if(p.version!=3||p.operation<104||p.operation>106||p.error||p.state||!p.owner||
           std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;})){p.error=2160;return;}
        if(quarantined_){p.error=2169;return;}
        if(owner_&&owner_!=p.owner){p.error=2161;return;}
        if(p.operation==104){
            if(owner_||!assets_.empty()||std::any_of(raw+136,raw+sizeof(p),[](uint8_t c){return c!=0;})){p.error=2162;return;}
            CallIdentity ids[3]{};std::memcpy(ids,raw+88,sizeof(ids));
            for(auto id:ids)if(id.serial<=0||!call_identity(b,id)){p.error=2163;return;}
            if(!named(b,ids[2].address,"StaticMesh","/Script/Engine")||!call_is_class(b,ids[2].address)||
               !exact_name(b,ids[0].address+24,"Default__KismetSystemLibrary")||
               !named(b,local_read<uint64_t>(ids[0].address+16),"KismetSystemLibrary","/Script/Engine")||
               !exact_name(b,ids[1].address+24,"LoadAsset_Blocking")||
               !named(b,local_read<uint64_t>(ids[1].address+32),"KismetSystemLibrary","/Script/Engine")){p.error=2163;return;}
            library_=ids[0];function_=ids[1];mesh_class_=ids[2];owner_=p.owner;return;
        }
        if(p.operation==106){
            if(std::any_of(raw+88,raw+sizeof(p),[](uint8_t c){return c!=0;})){p.error=2160;return;}
            p.error=close(b,session,pool);p.state=owner_?1:0;return;
        }
        if(!owner_){p.error=2162;return;}
        const auto*text=reinterpret_cast<const char*>(raw+2000);const auto length=strnlen_s(text,512);
        if(!length||length>=512||std::any_of(raw+88,raw+2000,[](uint8_t c){return c!=0;})||
           std::any_of(raw+2000+length,raw+sizeof(p),[](uint8_t c){return c!=0;})){p.error=2160;return;}
        const std::string path(text,length);
        if(path.rfind("/Game/",0)!=0){p.error=2160;return;}
        auto found=std::find_if(assets_.begin(),assets_.end(),[&](const Asset&a){return a.path==path;});
        CallIdentity mesh{};
        if(found!=assets_.end())mesh=found->mesh;
        else{
            if(assets_.size()>=6000||!registry_.ensure(b,mesh_class_)){p.error=2164;return;}
            const auto names=registry_.names(path);
            if(!names.first||!names.second){p.error=2165;return;}
            if(!load(b,names.first,names.second,mesh)){p.error=2166;return;}
            Asset asset{path,mesh,0};TargetStrongReferenceOps ops{b,mesh};
            const auto result=pool.acquire(ops,session,mesh.address,asset.lease);
            if(result!=StrongLeaseResult::Ok){if(result==StrongLeaseResult::Quarantined)quarantined_=true;p.error=2167;return;}
            if(!stabilize_retained_identity(ops,asset.mesh)){assets_.push_back(asset);quarantined_=true;p.error=2169;return;}
            assets_.push_back(asset);mesh=asset.mesh;
        }
        if(!call_identity(b,mesh)){p.error=2166;return;}
        std::memcpy(raw+4096,&mesh,16);
    }
};
}
