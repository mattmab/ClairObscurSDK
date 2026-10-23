#pragma once
#include "engine_profiles.h"
#include <chrono>
#include "static_mesh_registry.h"
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
        if(pool.acquire(ops,session,actor.address,row.lease)!=StrongLeaseResult::Ok)return false;
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
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool) {
        if(quarantined_)return 2109;
        while(!rows_.empty()) {
            auto& row=rows_.back();
            if(!row.destroyed && call_identity(b,row.actor)){clear();if(!call(b,2,row.actor))return 2106;row.destroyed=true;}
            TargetStrongReferenceOps ops{b,{-1,0,0}};
            if(row.lease && pool.release(ops,session,row.lease)!=StrongLeaseResult::Ok)return 2107;
            rows_.pop_back();
        }
        while(!assets_.empty()) {
            TargetStrongReferenceOps ops{b,{-1,0,0}};
            if(pool.release(ops,session,assets_.back().lease)!=StrongLeaseResult::Ok)return 2107;
            assets_.pop_back();
        }
        owner_=0;return 0;
    }
    template<class Pool> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& p) {
        auto* raw=reinterpret_cast<uint8_t*>(&p);const auto op=p.operation;
        if(p.version!=3 || p.error || p.state || !p.owner || op<93 || op>97){p.error=2100;return;}
        if(quarantined_){p.error=2109;return;}
        if(owner_ && owner_!=p.owner){p.error=2101;return;}
        if(op==93) {
            if(owner_||!rows_.empty()){p.error=2102;return;}
            std::memcpy(ids_,raw+88,sizeof(ids_));
            for(auto id:ids_)if(!call_identity(b,id)){p.error=2103;return;}
            if(!named(b,ids_[4].address,"StaticMeshActor","/Script/Engine") || !call_is_class(b,ids_[4].address) ||
               !named(b,ids_[5].address,"StaticMesh","/Script/Engine") || !call_is_class(b,ids_[5].address) || !current(b)){p.error=2103;return;}
            owner_=p.owner;
        } else if(op==95) {
            p.error=close(b,session,pool);
        } else if(!owner_){p.error=2102;return;}
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
                if(pool.acquire(ops,session,mesh.address,asset.lease)!=StrongLeaseResult::Ok){assets_.pop_back();p.error=2114;return;}
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
