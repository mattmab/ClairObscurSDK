#pragma once
#include "engine_profiles.h"
#include "map_loading_overlay.h"

// Armed at title, evaluated on the existing game-thread message pump. No
// Python discovery or menu construction is on the first-pawn protection path.
namespace e33_map_load_gate {
using namespace e33_mesh;
class Owner {
    uint64_t owner_=0;CallIdentity player_{},gi_{},function_{};
    CallIdentity world_{},pawn_{},movement_{},completed_pawn_{},completed_world_{};
    uint8_t mode_=0,custom_=0;bool held_=false,failed_=false;
    std::vector<std::pair<std::string,std::string>> worlds_;
    e33_map_loading_overlay::Cover cover_;
    ULONGLONG cover_started_=0;
    bool transition_=false;
    CallIdentity departing_world_{},departing_pawn_{};
    bool cover(uint64_t b,bool show){
        if(!cover_.configured())return true;
        if(show){if(!cover_started_)cover_started_=GetTickCount64();return cover_.show(b);}
        cover_started_=0;return cover_.hide(b);
    }
    bool same(CallIdentity a,CallIdentity c)const{return a.index==c.index&&a.serial==c.serial&&a.address==c.address;}
    bool set(uint64_t b,uint8_t mode,uint8_t custom){
        if(!TargetPodSchemaOps{b}.context())return false;
        const auto fn=call_identity(b,function_),object=call_identity(b,movement_);
        const auto&p=e33_engine_profiles::profiles[10];
        if(!fn||!object||!named(b,local_read<uint64_t>(fn+32),p.owner,"/Script/Engine")||
           !exact_name(b,fn+24,p.name)||local_read<uint32_t>(fn+0xb0)!=p.flags||
           local_read<uint16_t>(fn+0xb6)!=p.params||local_read<uint16_t>(fn+0xb8)!=p.returned||
           local_read<int32_t>(fn+0x58)!=int(p.extent)||local_read<uint64_t>(fn+0xd8)!=b+p.entry||
           !fields(b,fn,p.fields,p.count)||!call_derives(b,local_read<uint64_t>(object+16),local_read<uint64_t>(fn+32)))return false;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
        if(pe!=b+0x1393330&&pe!=b+0x332bb90)return false;
        uint8_t args[2]={mode,custom};
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(fn),args);
        return true;
    }
    bool binding(uint64_t b,CallIdentity&world,CallIdentity&pawn){
        if(!TargetPodSchemaOps{b}.context()||!call_identity(b,player_)||!call_identity(b,gi_))return false;
        const auto pc=zone_ref(b,player_.address,"PlayerController");
        if(!call_capture(b,pc).address||(local_read<uint32_t>(pc+8)&0x40018030U))return false;
        auto outer=pc;unsigned n=0;
        while(outer&&n++<32&&!named(b,local_read<uint64_t>(outer+16),"World","/Script/Engine"))outer=local_read<uint64_t>(outer+32);
        if(!outer||n>=32||zone_ref(b,outer,"OwningGameInstance")!=gi_.address)return false;
        world=call_capture(b,outer);pawn=call_capture(b,zone_ref(b,pc,"Pawn"));
        const auto viewport=zone_ref(b,player_.address,"ViewportClient");
        if(!viewport||zone_ref(b,viewport,"World")!=outer)return false;
        if(!world.address||!pawn.address||(local_read<uint32_t>(pawn.address+8)&0x40018030U))return false;
        const auto cls=local_read<uint64_t>(pawn.address+16);
        if(!exact_name(b,cls+24,"BP_jRPG_Character_World_C")&&
           !exact_name(b,cls+24,"BP_jRPG_Character_WorldMap_pawn_C"))return false;
        auto pawn_outer=pawn.address;
        for(unsigned i=0;pawn_outer&&i<32;++i,pawn_outer=local_read<uint64_t>(pawn_outer+32))
            if(pawn_outer==world.address)return true;
        return false;
    }
    bool selected(uint64_t b,CallIdentity world){
        const auto package=local_read<uint64_t>(world.address+32);
        for(const auto&row:worlds_)if(exact_name(b,world.address+24,row.second.c_str())&&exact_name(b,package+24,row.first.c_str()))return true;
        return false;
    }
public:
    bool active()const{return owner_!=0;}
    void quarantine(){failed_=true;}
    uint32_t release(uint64_t b){
        if(!held_)return 0;
        CallIdentity world{},pawn{};
        if(!binding(b,world,pawn)){
            if((world.address&&!same(world,world_))||(pawn.address&&!same(pawn,pawn_))){completed_pawn_=pawn_;completed_world_=world_;held_=false;return 0;}
            if(!call_identity(b,world_)||!call_identity(b,pawn_)||!call_identity(b,movement_)){
                completed_pawn_=pawn_;completed_world_=world_;held_=false;return 0;
            }
            return 407;
        }
        if(same(world,world_)&&same(pawn,pawn_)){
            if(!call_identity(b,movement_)){completed_pawn_=pawn_;completed_world_=world_;held_=false;return 0;}
            const auto mode=picto_field(b,movement_.address,"MovementMode","ByteProperty",513,1);
            if(!mode)return 2142;
            // Restore only the mode we own; another gameplay system may have
            // deliberately changed movement in the meantime.
            if(!local_read<uint8_t>(mode)&&!set(b,mode_,custom_))return 2142;
        }
        completed_pawn_=pawn_;completed_world_=world_;held_=false;return 0;
    }
    uint32_t close(uint64_t b){
        const auto error=release(b);if(error)return error;
        if(!cover_.detach(b))return 2144;
        cover_started_=0;transition_=false;
        owner_=0;worlds_.clear();player_=gi_=function_=world_=pawn_=movement_=completed_pawn_=completed_world_={};failed_=false;return 0;
    }
    template<class Pool> void poll(uint64_t b,uint64_t session,Pool&pool){
        if(!owner_||!TargetPodSchemaOps{b}.context())return;
        if(failed_){release(b);cover(b,false);return;}
        // SaveManager's load flag is observed before destination possession.
        // Both flags have exact reflected field contracts on this game build.
        const auto manager=zone_ref(b,gi_.address,"SaveManager");
        const auto loading=manager?picto_field(b,manager,"LoadIsInProgress","BoolProperty",169,1):0;
        const auto changing=picto_field(b,gi_.address,"IsChangingMap","BoolProperty",464,1);
        const auto loaded=picto_field(b,gi_.address,"SaveLoaded","BoolProperty",2680,1);
        const bool busy=loading&&changing&&(local_read<uint8_t>(loading)||local_read<uint8_t>(changing));
        if(busy){
            if(!transition_){binding(b,departing_world_,departing_pawn_);transition_=true;}
            if(!cover(b,true)){failed_=true;return;}
        }
        // Recovery deadline, never a readiness timer. A lost controller or
        // failed Python host must not leave an opaque screen indefinitely.
        if(cover_started_&&GetTickCount64()-cover_started_>60000){
            release(b);cover(b,false);failed_=true;return;
        }
        CallIdentity world{},pawn{};const bool bound=binding(b,world,pawn);
        const bool title=world.address&&exact_name(b,world.address+24,"Level_MainMenu");
        if(!busy&&title&&loaded&&!local_read<uint8_t>(loaded)){
            transition_=false;if(!cover(b,false))failed_=true;return;
        }
        if(!bound)return;
        if(transition_&&same(world,departing_world_)&&same(pawn,departing_pawn_))return;
        if(transition_&&same(world,completed_world_))completed_world_=completed_pawn_={};
        if(!busy&&(!selected(b,world)||same(world,completed_world_))){
            transition_=false;if(!cover(b,false))failed_=true;
        }
        if(held_){
            if(!same(world,world_)||!same(pawn,pawn_)){
                // Different exact possession: revoke the old journal without
                // executing a callback on its departing world.
                completed_pawn_=pawn_;held_=false;
            }else{
                if(!selected(b,world)){if(release(b))failed_=true;return;}
                if(!call_identity(b,movement_)){completed_pawn_=pawn_;held_=false;return;}
                const auto mode=picto_field(b,movement_.address,"MovementMode","ByteProperty",513,1);
                if(mode&&local_read<uint8_t>(mode)&&!set(b,0,0))failed_=true;
                return;
            }
        }
        // Collision belongs to the world visit, so ordinary character changes
        // after placement must not acquire another loading hold.
        if(same(world,completed_world_)||same(pawn,completed_pawn_)||!selected(b,world))return;
        if(!cover(b,true)){failed_=true;return;}
        const auto move=zone_ref(b,pawn.address,"CharacterMovement");
        auto identity=call_capture(b,move);if(!identity.address)return;
        const auto mode=picto_field(b,move,"MovementMode","ByteProperty",513,1);
        const auto custom=picto_field(b,move,"CustomMovementMode","ByteProperty",514,1);
        if(!mode||!custom)return;
        const auto value=local_read<uint8_t>(mode);if(!value||value>6)return;
        // Allocate stable serials under temporary same-callback leases. The
        // guard leaves actor lifetime with the game and cannot retain a world.
        CallIdentity stable[3]={world,pawn,identity};
        for(auto&id:stable){
            if(id.serial>0)continue;
            TargetStrongReferenceOps refs{b,id};uint64_t token=0;
            if(pool.acquire(refs,session,id.address,token)!=StrongLeaseResult::Ok){failed_=true;return;}
            const bool ready=stabilize_retained_identity(refs,id);
            const auto released=pool.release(refs,session,token);
            if(!ready||released!=StrongLeaseResult::Ok){failed_=true;return;}
        }
        world_=stable[0];pawn_=stable[1];movement_=stable[2];mode_=value;custom_=local_read<uint8_t>(custom);
        if(!set(b,0,0)){failed_=true;return;}
        held_=true;
    }
    void command(uint64_t b,MeshPacket&p){
        auto*raw=reinterpret_cast<uint8_t*>(&p);const auto op=p.operation;
        if(p.version!=3||p.error||p.state||!p.owner||op<99||op>103){p.error=2140;return;}
        if(owner_&&p.owner!=owner_){p.error=2141;return;}
        if(op==99){
            CallIdentity ids[3]{};std::memcpy(ids,raw+88,sizeof(ids));
            if(owner_&&(!same(ids[0],player_)||!same(ids[1],gi_)||!same(ids[2],function_))){p.error=2141;return;}
            const auto count=local_read<uint32_t>(reinterpret_cast<uint64_t>(raw+2000));
            if(!count||count>32||!call_identity(b,ids[0])||!call_identity(b,ids[1])||!call_identity(b,ids[2])||
               !named(b,local_read<uint64_t>(ids[0].address+16),"LocalPlayer","/Script/Engine")){
                p.error=2140;return;
            }
            for(const auto&id:ids)if(id.serial<=0){p.error=2140;return;}
            std::vector<std::pair<std::string,std::string>> paths;
            for(unsigned i=0;i<count;++i){
                const auto*text=reinterpret_cast<const char*>(raw+4096+i*512);const auto length=strnlen_s(text,512);
                if(!length||length>=512){p.error=2140;return;}
                std::string path(text,length);const auto dot=path.rfind('.');
                if(path.rfind("/Game/",0)!=0||dot==std::string::npos||dot+1==path.size()||
                   path.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_/.")!=std::string::npos){p.error=2140;return;}
                paths.emplace_back(path.substr(0,dot),path.substr(dot+1));
            }
            owner_=p.owner;player_=ids[0];gi_=ids[1];function_=ids[2];worlds_=std::move(paths);
        }else if(!owner_){p.error=2141;return;}
        else if(op==100){
            CallIdentity expected[2]{};std::memcpy(expected,raw+88,sizeof(expected));
            if(!held_&&transition_){p.error=2143;return;}
            if(held_&&(!same(expected[0],world_)||!same(expected[1],pawn_))){p.error=2143;return;}
            p.error=release(b);
            if(!p.error&&!cover(b,false))p.error=2144;
            if(!p.error)transition_=false;
        }else if(op==102)p.error=close(b);
        else if(op==103){
            CallIdentity ids[5]{};std::memcpy(ids,raw+88,sizeof(ids));
            if(!cover_.configure(b,ids))p.error=2144;
        }
        if(op==101){
            std::memcpy(raw+4096,&world_,16);std::memcpy(raw+4112,&pawn_,16);
            std::memcpy(raw+4128,&movement_,16);raw[4144]=mode_;raw[4145]=custom_;
        }
        p.state=failed_?4:held_?2:owner_?1:0;
    }
};
}
