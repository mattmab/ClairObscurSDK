#pragma once
#include "free_aim_region.h"
#include "validated_engine_profile_call.h"
#include <algorithm>

// Read-only collision query. No projectile, damage callback, RNG, buff, or
// gameplay setter is invoked. HitResult stays in native stack storage.
template<class Pool> struct TargetFreeAimRegion {
    uint64_t base,session;Pool& leases;
    uint64_t field(uint64_t cls,const char* owner,const char* name,const char* type,int width,int expected=-1)const{
        for(unsigned ancestry_step=0;cls&&ancestry_step<32;++ancestry_step,cls=local_read<uint64_t>(cls+0x40)){
            if(!call_capture(base,cls).address)return 0;
            if(owner&&!exact_name(base,cls+24,owner))continue;
            auto f=local_read<uint64_t>(cls+0x50);
            for(unsigned n=0;f&&n<2048;++n,f=local_read<uint64_t>(f+24)){
                if(!exact_name(base,f+32,name))continue;
                const auto offset=local_read<int32_t>(f+0x44);
                return local_read<uint64_t>(f+16)==(cls|1)&&
                    exact_name(base,local_read<uint64_t>(f+8),type)&&local_read<int32_t>(f+0x30)==1&&
                    local_read<int32_t>(f+0x34)==width&&offset>=40&&offset<=65536-width&&
                    (expected<0||offset==expected)?f:0;
            }
        }
        return 0;
    }
    uint64_t object_property(uint64_t object,const char* owner,const char* name,int offset=-1)const{
        if(!call_capture(base,object).address)return 0;
        auto f=field(local_read<uint64_t>(object+16),owner,name,"ObjectProperty",8,offset);
        return f?local_read<uint64_t>(object+local_read<int32_t>(f+0x44)):0;
    }
    bool party(uint64_t manager,const char* name,int offset,std::vector<uint64_t>& ignored)const{
        auto f=field(local_read<uint64_t>(manager+16),"AC_jRPG_BattleManager_C",name,"ArrayProperty",16,offset);
        if(!f)return false;
        const auto inner=local_read<uint64_t>(f+0x78);
        if(!inner||local_read<uint64_t>(inner+16)!=f||!exact_name(base,local_read<uint64_t>(inner+8),"ObjectProperty")||
           local_read<int32_t>(inner+0x34)!=8)return false;
        struct Array{uint64_t data;int32_t count,capacity;};
        const auto a=local_read<Array>(manager+offset);
        if(a.count<0||a.count>32||a.capacity<a.count||a.capacity>64||(a.count&&!a.data))return false;
        for(int32_t i=0;i<a.count;++i){
            const auto actor=local_read<uint64_t>(a.data+uint64_t(i)*8);
            if(!call_capture(base,actor).address)return false;
            if(std::find(ignored.begin(),ignored.end(),actor)==ignored.end())ignored.push_back(actor);
        }
        return ignored.size()<=32;
    }
    bool invoke(const e33_aim_region::Packet& p,unsigned definition,unsigned profile,uint64_t recipient,void* args)const{
        return e33_engine_profile_call::invoke(base,p.definitions[definition],call_capture(base,recipient),
            e33_engine_profiles::profiles[profile],args);
    }
    void run(e33_aim_region::Packet& p)const{
        using namespace e33_aim_region;
        if(!valid(p)||!TargetPodSchemaOps{base}.context()||!leases.owns_object(session,p.token,p.manager.address)){
            p.error=rejected;return;
        }
        const auto manager=call_identity(base,p.manager),source=call_identity(base,p.source);
        if(!manager||!source||!e33_mesh::named(base,local_read<uint64_t>(manager+16),"AC_jRPG_BattleManager_C",
           "/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
           object_property(manager,"AC_jRPG_BattleManager_C","CurrentCharacter",176)!=source){p.error=unavailable;return;}
        const auto controller=local_read<uint64_t>(manager+32);
        const auto camera=object_property(controller,"PlayerController","PlayerCameraManager");
        const auto system=call_identity(base,p.definitions[0]);
        const auto part_class=call_identity(base,p.definitions[5]);
        if(!camera||!system||!part_class||
           !e33_mesh::named(base,system,"Default__KismetSystemLibrary","/Script/Engine")||
           !e33_mesh::named(base,part_class,"BP_FreeAimTargetPart_C","/Game/Gameplay/FreeAim/BP_FreeAimTargetPart")){
            p.error=rejected;return;
        }
        std::vector<uint64_t> ignored;
        if(!party(manager,"PlayerCharacters",184,ignored)||!party(manager,"DeadPlayerCharacters",336,ignored)){
            p.error=unavailable;return;
        }
        const auto hit_field=field(local_read<uint64_t>(manager+16),"AC_jRPG_BattleManager_C","LastMouseHitLocation","StructProperty",24);
        if(!hit_field||!e33_mesh::named(base,local_read<uint64_t>(hit_field+0x70),"Vector","/Script/CoreUObject")){
            p.error=unavailable;return;
        }
        double position[3]{},aim_point[3]{},start[3]{},end[3]{};
        std::memcpy(aim_point,reinterpret_cast<void*>(manager+local_read<int32_t>(hit_field+0x44)),24);
        // The engine's current hover endpoint is authoritative. Reconstructing
        // a direction from camera rotation can disagree with the rendered aim.
        if(!invoke(p,1,12,camera,position)||!toward(position,aim_point,start,end)){
            p.error=unavailable;return;
        }
        alignas(16) uint8_t args[464]{};
        bool found=false;
        for(unsigned attempt=0;attempt<2&&!found;++attempt){
            std::memset(args,0,sizeof(args));std::memcpy(args,&manager,8);
            std::memcpy(args+8,start,24);std::memcpy(args+32,end,24);
            args[56]=attempt?0:5;args[57]=attempt?0:1;args[336]=1;
            e33_surface_query::IgnoredActors actors{ignored.data(),int32_t(ignored.size()),int32_t(ignored.size())};
            std::memcpy(args+64,&actors,16);
            if(!invoke(p,3,14,system,args)){p.error=unavailable;return;}
            found=args[376]!=0;
        }
        if(!found){p.state=1;return;}
        uint8_t hit[248];std::memcpy(hit,args+88,248);std::memset(args,0,sizeof(args));std::memcpy(args,hit,248);
        // BreakHitResult is a GameplayStatics static function; its separately
        // observed class default is checked before dispatch.
        const auto break_default=call_identity(base,p.definitions[6]);
        if(!break_default||!e33_mesh::named(base,break_default,"Default__GameplayStatics","/Script/Engine")){
            p.error=unavailable;return;
        }
        if(!invoke(p,4,15,break_default,args)){p.error=unavailable;return;}
        if(!args[248]||args[249]){p.state=1;return;}
        const auto actor=local_read<uint64_t>(reinterpret_cast<uint64_t>(args)+368);
        auto component=local_read<uint64_t>(reinterpret_cast<uint64_t>(args)+376);
        if(!actor||!component||!call_capture(base,actor).address||!call_capture(base,component).address){p.error=unavailable;return;}
        p.actor=call_capture(base,actor);p.component=call_capture(base,component);
        p.multiplier=1.;p.hit=1;
        uint64_t visited[32]{};
        for(unsigned parent_step=0;component&&parent_step<32;++parent_step){
            if(!call_capture(base,component).address){p.error=unavailable;return;}
            for(unsigned i=0;i<parent_step;++i)if(visited[i]==component){p.error=unavailable;return;}
            visited[parent_step]=component;
            if(call_derives(base,local_read<uint64_t>(component+16),part_class)){
                const auto cls=local_read<uint64_t>(component+16);
                if(!field(cls,"BP_FreeAimTargetPart_C","DamageMultiplier","DoubleProperty",8,664)||
                   !field(cls,"BP_FreeAimTargetPart_C","BaseDamage","DoubleProperty",8,656)||
                   !field(cls,"BP_FreeAimTargetPart_C","BodyPartType","ByteProperty",1,584)){
                    p.error=unavailable;return;
                }
                p.multiplier=local_read<double>(component+664);p.base_damage=local_read<double>(component+656);
                p.body_part=local_read<uint8_t>(component+584);p.part=call_capture(base,component);
                if(!std::isfinite(p.multiplier)||p.multiplier<0||p.multiplier>1.e6||
                   !std::isfinite(p.base_damage)||p.base_damage<0||p.body_part>4){p.error=unavailable;return;}
                break;
            }
            component=object_property(component,"SceneComponent","AttachParent",176);
        }
        p.state=1;
    }
};

