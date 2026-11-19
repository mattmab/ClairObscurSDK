#pragma once
#include "engine_profiles.h"
#include "map_loading_overlay.h"
#include "map_loading_priority_target.h"

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
    ULONGLONG hold_started_=0,hold_elapsed_=0;uint64_t hold_sequence_=0;
    e33_map_loading_priority::Target priority_target_;
    e33_map_loading_priority::Journal priority_;
    uint32_t priority_error_=0;
    void finish_hold(){if(held_&&hold_started_)hold_elapsed_=GetTickCount64()-hold_started_;held_=false;}
    CallIdentity departing_world_{},departing_pawn_{};
    bool cinematic(uint64_t b)const{
        if(!call_identity(b,player_))return false;
        const auto pc=zone_ref(b,player_.address,"PlayerController");
        if(!call_capture(b,pc).address)return false;
        const auto system=zone_ref(b,pc,"BP_CinematicSystem");
        if(!call_capture(b,system).address||local_read<uint64_t>(system+32)!=pc||
           !named(b,local_read<uint64_t>(system+16),"BP_CinematicSystem_C","/Game/Gameplay/CinematicSystem/BP_CinematicSystem"))return false;
        // These are the game's actual cinematic lifecycle flags. A paused or
        // skipping cinematic and its camera/input transitions still own the view.
        const char*names[]={"IsPlayingCinematic","CinematicPaused","IsSkippingCinematic","SequenceStarted","HasInputLockFromPreCinematic","IsInTransition"};
        const int offsets[]={568,569,584,664,665,848};
        for(unsigned i=0;i<6;++i){
            const auto field=picto_field(b,system,names[i],"BoolProperty",offsets[i],1);
            if(field&&local_read<uint8_t>(field))return true;
        }
        return false;
    }
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
    struct PriorityOps {
        Owner& gate;uint64_t base;
        bool held(const e33_map_loading_priority::Binding& binding){
            return binding.owner==gate.owner_&&binding.hold==gate.hold_sequence_&&
                gate.same(e33_map_loading_priority::call_id(binding.world),gate.world_)&&gate.handoff_ready(base);
        }
        bool inspect_held(e33_map_loading_priority::Observation& out){
            return held(gate.priority_target_.binding())&&gate.priority_target_.inspect(base,out);
        }
        e33_map_loading_priority::Proof inspect_owned(const e33_map_loading_priority::Binding& binding,
                e33_map_loading_priority::Observation& out){return gate.priority_target_.inspect_owned(base,binding,out);}
        e33_map_loading_priority::Dispatch set_original(const e33_map_loading_priority::Observation& before,
                bool value,bool require_held){
            if(require_held&&!held(before.binding))return e33_map_loading_priority::Dispatch::NotDispatched;
            return gate.priority_target_.set_original(base,before,value);
        }
    };
    uint32_t priority_result(e33_map_loading_priority::Result result){
        using e33_map_loading_priority::Result;
        priority_error_=result==Result::Ok?0:result==Result::Pending?407:result==Result::Unknown?2146:2145;
        return priority_error_;
    }
    uint32_t priority_release(uint64_t b){
        if(!priority_target_.configured()||!priority_.active())return 0;
        PriorityOps ops{*this,b};return priority_result(priority_.close(ops));
    }
    template<class Pool> void priority_begin(uint64_t b,uint64_t session,Pool& pool){
        if(!priority_target_.configured()||priority_.active())return;
        priority_error_=0;
        if(!priority_target_.prepare(b,session,pool,owner_,hold_sequence_,player_,world_)){
            priority_error_=2145;return;
        }
        PriorityOps ops{*this,b};priority_result(priority_.begin(ops));
    }
public:
    bool active()const{return owner_!=0;}
    bool handoff_ready(uint64_t b){
        if(!owner_||!held_||failed_||cinematic(b))return false;
        CallIdentity world{},pawn{};
        if(!binding(b,world,pawn)||!same(world,world_)||!same(pawn,pawn_)||!call_identity(b,movement_))return false;
        if(zone_ref(b,pawn.address,"CharacterMovement")!=movement_.address)return false;
        const auto mode=picto_field(b,movement_.address,"MovementMode","ByteProperty",513,1);
        return mode&&!local_read<uint8_t>(mode);
    }
    void quarantine(){failed_=true;if(priority_.unknown())priority_error_=2146;}
    uint32_t release(uint64_t b){
        struct Ops {
            Owner& gate;uint64_t base;
            void release_priority(){gate.priority_release(base);}
            uint32_t release_movement(){return gate.release_movement(base);}
        } ops{*this,b};
        return e33_map_loading_priority::release_guard(ops);
    }
    uint32_t release_movement(uint64_t b){
        if(!held_)return 0;
        CallIdentity world{},pawn{};
        if(!binding(b,world,pawn)){
            if((world.address&&!same(world,world_))||(pawn.address&&!same(pawn,pawn_))){completed_pawn_=pawn_;completed_world_=world_;finish_hold();return 0;}
            if(!call_identity(b,world_)||!call_identity(b,pawn_)||!call_identity(b,movement_)){
                completed_pawn_=pawn_;completed_world_=world_;finish_hold();return 0;
            }
            return 407;
        }
        if(same(world,world_)&&same(pawn,pawn_)){
            if(!call_identity(b,movement_)){completed_pawn_=pawn_;completed_world_=world_;finish_hold();return 0;}
            const auto mode=picto_field(b,movement_.address,"MovementMode","ByteProperty",513,1);
            if(!mode)return 2142;
            // Restore only the mode we own; another gameplay system may have
            // deliberately changed movement in the meantime.
            if(!local_read<uint8_t>(mode)&&!set(b,mode_,custom_))return 2142;
        }
        completed_pawn_=pawn_;completed_world_=world_;finish_hold();return 0;
    }
    uint32_t close(uint64_t b){
        const auto error=release(b);if(error)return error;
        if(!cover_.detach(b))return 2144;
        cover_started_=0;transition_=false;
        // Movement and presentation have been restored independently. A
        // retained uncertain priority journal must still prevent owner/lease
        // teardown; do not replay its original setter to force cleanup.
        if(priority_.active())return priority_error_?priority_error_:407;
        priority_target_.clear();priority_=e33_map_loading_priority::Journal{};priority_error_=0;
        owner_=0;worlds_.clear();player_=gi_=function_=world_=pawn_=movement_=completed_pawn_=completed_world_={};failed_=false;return 0;
    }
    template<class Pool> void poll(uint64_t b,uint64_t session,Pool&pool){
        if(!owner_||!TargetPodSchemaOps{b}.context())return;
        if(priority_.active()){
            PriorityOps ops{*this,b};priority_result(priority_.poll(ops));
        }
        if(failed_){release(b);cover(b,false);return;}
        // Cinematic ownership takes precedence over save/map loading flags.
        // Yield any hold we acquired before its pre-roll, but don't mark this
        // world complete: collision protection can resume after the cinematic.
        if(cinematic(b)){
            if(held_){if(release(b)){failed_=true;return;}completed_pawn_=completed_world_={};}
            if(!cover(b,false))failed_=true;
            return;
        }
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
                completed_pawn_=pawn_;finish_hold();
            }else{
                if(!selected(b,world)){if(release(b))failed_=true;return;}
                if(!call_identity(b,movement_)){completed_pawn_=pawn_;finish_hold();return;}
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
        hold_started_=GetTickCount64();hold_elapsed_=0;++hold_sequence_;held_=true;
        priority_begin(b,session,pool);
    }
    void command(uint64_t b,MeshPacket&p){
        auto*raw=reinterpret_cast<uint8_t*>(&p);const auto op=p.operation;
        if(p.version!=3||p.error||p.state||!p.owner||!((op>=99&&op<=103)||op==267)){p.error=2140;return;}
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
            // A cinematic/arrival may have yielded movement while transition_
            // remains set. The exact fresh binding/selected-world proof below
            // still qualifies readiness; no held movement is restored here.
            if(held_&&(!same(expected[0],world_)||!same(expected[1],pawn_))){p.error=2143;return;}
            if(!held_){
                // Readiness may arrive while a cinematic owns movement. Keep
                // its exact visit ACK so cinematic completion cannot acquire
                // a second hold for an already prepared scene.
                CallIdentity current_world{},current_pawn{};
                if(!binding(b,current_world,current_pawn)||!same(expected[0],current_world)||
                   !same(expected[1],current_pawn)||!selected(b,current_world)){p.error=2143;return;}
                completed_world_=current_world;completed_pawn_=current_pawn;
            }
            p.error=release(b);
            if(!p.error&&!cover(b,false))p.error=2144;
            if(!p.error)transition_=false;
        }else if(op==102)p.error=close(b);
        else if(op==103){
            CallIdentity ids[5]{};std::memcpy(ids,raw+88,sizeof(ids));
            if(!cover_.configure(b,ids))p.error=2144;
        }else if(op==267){
            for(size_t i=24;i<sizeof(p);++i)if((i<88||i>=120)&&raw[i]){p.error=2145;return;}
            CallIdentity ids[2]{};std::memcpy(ids,raw+88,sizeof(ids));
            if(held_||priority_.active()||!priority_target_.configure(b,ids))p.error=2145;
        }
        if(op==101){
            std::memcpy(raw+4096,&world_,16);std::memcpy(raw+4112,&pawn_,16);
            std::memcpy(raw+4128,&movement_,16);raw[4144]=mode_;raw[4145]=custom_;
#if E33_RUNTIME_CINEMATIC_VERSION>=293
            const uint64_t timing[3]={hold_started_,held_?GetTickCount64()-hold_started_:hold_elapsed_,hold_sequence_};
            std::memcpy(raw+4160,timing,sizeof(timing));
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=316
            const uint32_t priority[5]={uint32_t(priority_.state()),priority_error_,uint32_t(priority_.enable_returned()),
                uint32_t(priority_.restore_returned()),uint32_t(priority_.retired())};
            std::memcpy(raw+4184,priority,sizeof(priority));
#endif
        }
        p.state=failed_?4:held_?2:owner_?1:0;
    }
};
}
