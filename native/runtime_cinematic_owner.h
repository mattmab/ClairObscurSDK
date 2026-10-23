#pragma once
#include "engine_profiles.h"
#include "runtime_cinematic_profile.h"
#include "runtime_cinematic_effects_profile.h"
#include "runtime_cinematic_timing.h"
#include <chrono>
#pragma warning(push)
#pragma warning(disable:4324)

namespace e33_runtime_cinematic {
using namespace e33_mesh;
// Only op70 prepare,71 play,72 close,73 status. The 20-second Lune/Maelle
// demonstration generates all transforms internally; no general pose ABI.
// internally. Uses WorldBuilder's exact function profiles/struct validators;
// never enables its editing, input, picking, or scene persistence machinery.
class Owner {
    static constexpr size_t inputs=57;
    inline static constexpr size_t reused[]={0,1,2,3,4,6,7,9,12,13,16,21,34,47,63};
    StrongLeasePool<96> leases_;
    CallIdentity ids_[inputs]{},camera_{},characters_[8]{},components_[8]{},audio_{},saved_{};
    bool placed_=false;
    CallIdentity effects_[11]{};
    double effect_at_[11]{},last_hit_=-10.;
    unsigned effect_count_=0,last_attacker_=0;
    uint64_t base_=0,owner_=0;
    uint32_t state_=0,error_=0,step_=0,failed_step_=0,reason_=0,poses_=0;
    bool pool_=false,move_ignored_=false,look_ignored_=false,view_armed_=false;
    double origin_[3]{},yaw_=0,elapsed_=0,animation_at_=-1,audio_at_=-1;
    Timing timing_;
    std::chrono::steady_clock::time_point clock_;
    alignas(16) uint8_t args_[512]{};
    void clear(){std::memset(args_,0,sizeof(args_));}
    template<class T> void put(size_t at,const T& value){std::memcpy(args_+at,&value,sizeof(T));}
    template<class T> T get(size_t at=0)const{T result{};std::memcpy(&result,args_+at,sizeof(T));return result;}
    bool valid(const CallIdentity& id)const{return id.address && call_identity(base_,id)==id.address && !(local_read<uint32_t>(id.address+8)&0x40000000);}
    bool same(const CallIdentity& a,const CallIdentity& b)const{return a.index==b.index && a.serial==b.serial && a.address==b.address;}
    const MeshFunction& profile(size_t i)const{return i>=30?fx_functions[i-30]:i==29?mesh_functions[31]:i<15?e33_engine_profiles::profiles[reused[i]]:demo_functions[i-15];}
    CallIdentity function_id(size_t i)const{return ids_[i>=30?56+i-30:21+i];}
    bool schema(size_t i)const{
        const auto fn=call_identity(base_,function_id(i));const auto& p=profile(i);
        if(!fn)return false;
        if(i==30){
            // Validate Niagara object constraints locally; shared mesh codecs
            // and their Engine-only constraint policy remain unchanged.
            auto f=local_read<uint64_t>(fn+0x50);unsigned constraints=0;
            for(unsigned n=0;f && n<16;++n,f=local_read<uint64_t>(f+24)){
                const char* cls=exact_name(base_,f+32,"SystemTemplate")?"NiagaraSystem":exact_name(base_,f+32,"ReturnValue")?"NiagaraComponent":nullptr;
                if(cls){const auto type=local_read<uint64_t>(f+0x70);if(!named(base_,type,cls,"/Script/Niagara") || !call_is_class(base_,type))return false;++constraints;}
            }if(constraints!=2)return false;
        }
        return fn && exact_name(base_,local_read<uint64_t>(fn+16)+24,"Function") &&
            exact_name(base_,fn+24,p.name) && named(base_,local_read<uint64_t>(fn+32),p.owner,i==30?"/Script/Niagara":"/Script/Engine") &&
            local_read<uint32_t>(fn+0xb0)==p.flags && local_read<uint16_t>(fn+0xb6)==p.params &&
            local_read<uint16_t>(fn+0xb8)==p.returned && local_read<int32_t>(fn+0x58)==int(p.extent) &&
            local_read<uint64_t>(fn+0xd8)==base_+p.entry && fields(base_,fn,p.fields,p.count);
    }
    bool call(CallIdentity recipient,size_t i){
        step_=uint32_t(i+1);
        if(!TargetPodSchemaOps{base_}.context() || !valid(recipient) || !schema(i))return false;
        const auto fn=function_id(i).address;
        if(!call_derives(base_,local_read<uint64_t>(recipient.address+16),local_read<uint64_t>(fn+32)))return false;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(recipient.address)+0x268);
        if(pe!=base_+0x1393330 && pe!=base_+0x332bb90)return false;
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(recipient.address),reinterpret_cast<void*>(fn),args_);
        return true;
    }
    bool hold(CallIdentity& id){
        if(!valid(id))return false;
        TargetStrongReferenceOps ops{base_,id};uint64_t token{};
        return leases_.acquire(ops,owner_,id.address,token)==StrongLeaseResult::Ok && stabilize_retained_identity(ops,id);
    }
    uint64_t field(CallIdentity id,const FieldProof& p)const{
        if(!valid(id))return 0;
        auto cls=local_read<uint64_t>(id.address+16);
        for(unsigned class_depth=0;cls && class_depth<128;++class_depth,cls=local_read<uint64_t>(cls+0x40)){
            if(!named(base_,cls,p.owner,"/Script/Engine"))continue;
            auto f=local_read<uint64_t>(cls+0x50);
            for(unsigned n=0;f && n<512;++n,f=local_read<uint64_t>(f+24)){
                if(!exact_name(base_,f+32,p.name))continue;
                return local_read<uint64_t>(f)==base_+p.table && local_read<uint64_t>(f+16)==(cls|1) &&
                    exact_name(base_,local_read<uint64_t>(f+8),p.type) && local_read<uint32_t>(f+0x30)==1 &&
                    local_read<uint32_t>(f+0x34)==p.width && local_read<uint32_t>(f+0x44)==p.offset &&
                    local_read<uint64_t>(f+0x38)==p.flags && (!p.boolean || local_read<uint32_t>(f+0x70)==p.boolean)?id.address+p.offset:0;
            }
            return 0;
        }
        return 0;
    }
    bool current(){
        const auto ref=field(ids_[0],player_controller);
        if(!ref || local_read<uint64_t>(ref)!=ids_[1].address || !valid(ids_[1]) || !valid(ids_[2]))return false;
        clear();return call(ids_[1],11) && get<uint64_t>()==ids_[2].address;
    }
    bool assets()const{
        constexpr const char* packages[]={"/Game/FX/FX_Leo/Fx/Lune/Thunder_Fall/Systems/NS_Impact_Electric1","/Game/FX/FX_Leo/Fx/Maelle/FX_FlowerPetalsBurst","/Game/FX/FX_Leo/Fx/Maelle/FX_MaelleSword","/Game/FX/FX_Leo/Fx/Lune/FX_LuneTrail"};
        constexpr const char* names[]={"NS_Impact_Electric1","FX_FlowerPetalsBurst","FX_MaelleSword","FX_LuneTrail"};
        for(unsigned i=0;i<4;++i)if(!named(base_,ids_[52+i].address,names[i],packages[i]) || !named(base_,local_read<uint64_t>(ids_[52+i].address+16),"NiagaraSystem","/Script/Niagara"))return false;
        if(!named(base_,ids_[51].address,"Default__NiagaraFunctionLibrary","/Script/Niagara"))return false;
        constexpr size_t mesh_slots[]={7,12,13,14,16,17,18,19};
        for(size_t i=0;i<8;++i){const auto& id=ids_[mesh_slots[i]];
            if(!named(base_,id.address,character_names[i],character_packages[i]) ||
               !named(base_,local_read<uint64_t>(id.address+16),"SkeletalMesh","/Script/Engine"))return false;}
        if(!named(base_,ids_[8].address,animation_name,animation_package) ||
           !named(base_,ids_[15].address,maelle_animation_name,maelle_animation_package) ||
           !named(base_,ids_[20].address,target_animation_name,target_animation_package) ||
           !named(base_,ids_[9].address,sound_name,sound_package) ||
           !named(base_,local_read<uint64_t>(ids_[8].address+16),"AnimSequence","/Script/Engine") ||
           !named(base_,local_read<uint64_t>(ids_[15].address+16),"AnimSequence","/Script/Engine") ||
           !named(base_,local_read<uint64_t>(ids_[20].address+16),"AnimSequence","/Script/Engine") ||
           !named(base_,local_read<uint64_t>(ids_[9].address+16),"SoundWave","/Script/Engine"))return false;
        constexpr size_t bodies[]={7,14,18},animations[]={8,15,20};
        for(unsigned i=0;i<3;++i){
        const auto mesh_ref=field(ids_[bodies[i]],mesh_skeleton),anim_ref=field(ids_[animations[i]],animation_skeleton);
        const auto notify=field(ids_[animations[i]],notifies),root=field(ids_[animations[i]],root_motion);
        if(!(mesh_ref && anim_ref && notify && root && local_read<uint64_t>(mesh_ref) &&
            local_read<uint64_t>(mesh_ref)==local_read<uint64_t>(anim_ref) &&
            local_read<int32_t>(notify+8)==0 && local_read<int32_t>(notify+12)>=0 && !local_read<uint8_t>(root)))return false;
        }return true;
    }
    bool spawn(CallIdentity cls,CallIdentity& actor){
        clear();put(0,ids_[1].address);put(8,cls.address);transform(args_+16,origin_);args_[112]=1;
        if(!call(ids_[3],0))return false;
        actor=call_capture(base_,get<uint64_t>(136));
        if(!actor.address || !hold(actor))return false;
        clear();if(!call(actor,13))return false; // collision off before FinishSpawning
        clear();put(0,actor.address);transform(args_+16,origin_);
        return call(ids_[3],1) && get<uint64_t>(120)==actor.address;
    }
    bool pose(CallIdentity actor,const double* position,const double* rotation){
        clear();std::memcpy(args_,position,24);std::memcpy(args_+24,rotation,24);
        if(!call(actor,14))return false;
        if(args_[48])return true; // WorldBuilder K2_TeleportTo profile
        // Teleport may report false for an epsilon-sized no-op. Accept only a
        // read-back proving that the native actor is already at the target.
        clear();if(!call(actor,3))return false;
        for(unsigned i=0;i<3;++i)if(std::abs(get<double>(8*i)-position[i])>.01)return false;
        clear();if(!call(actor,4))return false;
        for(unsigned i=0;i<3;++i)if(std::abs(std::remainder(get<double>(8*i)-rotation[i],360.))>.001)return false;
        return true;
    }
    uint64_t bone_name(CallIdentity component,const char* requested){
        clear();if(!call(component,27))return 0;const auto count=get<int32_t>();
        if(count<1 || count>1024)return 0;
        for(int32_t i=0;i<count;++i){clear();put(0,i);if(!call(component,28))return 0;
            const auto name=get<uint64_t>(4);char text[64]{};
            if(!skin_name(base_,name,text))return 0;
            if(!_stricmp(text,requested))return name;
        }return 0;
    }
    bool attach(CallIdentity child,CallIdentity parent,const char* socket){
        const auto name=socket?bone_name(parent,socket):0;if(socket && !name)return false;
        clear();put(0,parent.address);put(8,name);args_[16]=args_[17]=args_[18]=2;
        return call(child,26) && args_[20];
    }
    bool effect(unsigned asset,const double* position,double scale,double seconds){
        if(effect_count_>=11)return false;
        clear();put(0,ids_[1].address);put(8,ids_[52+asset].address);
        std::memcpy(args_+16,position,24);put(48,yaw_);
        for(unsigned axis=0;axis<3;++axis)put(64+8*axis,scale);
        args_[89]=1; // activate, no pooling/auto-destroy/pre-cull: private lifetime
        if(!call(ids_[51],30))return false;
        auto& component=effects_[effect_count_];component=call_capture(base_,get<uint64_t>(96));
        if(!component.address || !named(base_,local_read<uint64_t>(component.address+16),"NiagaraComponent","/Script/Niagara") || !hold(component))return false;
        effect_at_[effect_count_++]=seconds;return true;
    }
    bool expire_effects(double seconds){
        // First two are attached attack trails. Impact bursts have a bounded
        // lifetime even if the source system itself loops indefinitely.
        for(unsigned i=2;i<effect_count_;++i)if(effects_[i].address && seconds-effect_at_[i]>.9){
            if(valid(effects_[i])){clear();put(0,effects_[i].address);if(!call(effects_[i],22))return false;}
            effects_[i]={};
        }return true;
    }
    bool advance(double seconds){
        const double rad=3.141592653589793/180.,u=Timing::movement(seconds);
        const double forward[]={std::cos(yaw_*rad),std::sin(yaw_*rad)};
        const double side[]={-forward[1],forward[0]};
        double point[]={origin_[0],origin_[1],origin_[2]};
        if(!placed_){
            for(unsigned i=0;i<7;++i){if(i==2)continue; // strand hair follows the head socket
                const double offset=i<3?-110.:i<6?110.:0.,distance=i==6?170.:0.;
                const double actor_point[]={point[0]+side[0]*offset+forward[0]*distance,
                    point[1]+side[1]*offset+forward[1]*distance,point[2]};
                const double facing=i==6?yaw_+180.:std::atan2(forward[1]*170.-side[1]*offset,forward[0]*170.-side[0]*offset)/rad;
                const double character_rotation[]={0.,facing-90.,0.};
                if(!pose(characters_[i],actor_point,character_rotation)){step_+=1000;return false;}
            }placed_=true;
        }
        const double angle=(yaw_+180.)*rad+u*2.*3.141592653589793;
        double camera[]={point[0]+forward[0]*70.+std::cos(angle)*500.,
            point[1]+forward[1]*70.+std::sin(angle)*500.,point[2]+165.+45.*std::sin(u*3.141592653589793)};
        const double delta[]={point[0]+forward[0]*70.-camera[0],point[1]+forward[1]*70.-camera[1],point[2]+100.-camera[2]};
        const double rotation[]={std::atan2(delta[2],std::hypot(delta[0],delta[1]))/rad,
            std::atan2(delta[1],delta[0])/rad,0.};
        if(!pose(camera_,camera,rotation)){step_+=2000;return false;}
        ++poses_;
        if(timing_.animation_due(seconds)){
            constexpr size_t animation_slots[]={8,15,20},body_slots[]={0,3,6};
            for(unsigned i=0;i<3;++i){clear();put(0,ids_[animation_slots[i]].address);args_[8]=1;if(!call(components_[body_slots[i]],17))return false;}
            timing_.animation=true;animation_at_=seconds;
            if(!effect(3,point,.5,seconds) || !attach(effects_[0],components_[0],"foot_r"))return false;
            if(!effect(2,point,1.,seconds) || !attach(effects_[1],components_[7],nullptr))return false;
        }
        if(timing_.audio_due(seconds)){
            clear();if(!call(audio_,20))return false;
            const auto cue=timing_.audio_count;last_attacker_=(cue==1 || cue==3 || cue==6)?1U:0U;
            const double impact[]={point[0]+forward[0]*170.,point[1]+forward[1]*170.,point[2]+85.};
            if(!effect(last_attacker_,impact,last_attacker_?.8:.65,seconds))return false;
            last_hit_=seconds;
            if(!timing_.audio)audio_at_=seconds;
            timing_.audio_fired();
        }
        const double age=seconds-last_hit_,pulse=age>=0. && age<.55?std::sin(age/.55*3.141592653589793):0.;
        const double direction=last_attacker_?1.:-1.;
        const double target_point[]={point[0]+forward[0]*(170.+28.*pulse)+side[0]*direction*12.*pulse,
            point[1]+forward[1]*(170.+28.*pulse)+side[1]*direction*12.*pulse,point[2]+10.*pulse};
        const double reaction[]={12.*pulse,yaw_+90.,direction*9.*pulse};
        if(!pose(characters_[6],target_point,reaction) || !expire_effects(seconds))return false;
        return true;
    }
public:
    bool active()const{return pool_;}
    void quarantine(){error_=2015;state_=3;}
    uint32_t close(uint32_t reason=0){
        if(!pool_)return 0;
        for(auto& component:effects_){if(component.address && valid(component)){clear();put(0,component.address);if(!call(component,22))return 2010;}component={};}
        if(!TargetPodSchemaOps{base_}.context())return 407;
        state_=3;reason_=reason;
        if(audio_.address){if(valid(audio_)){clear();if(!call(audio_,21))return 2010;clear();put(0,audio_.address);if(!call(audio_,22))return 2010;}audio_={};}
        if(view_armed_ && current()){
            clear();if(!call(ids_[1],6))return 2011;
            if(get<uint64_t>()==camera_.address && valid(saved_)){
                clear();put(0,saved_.address);if(!call(ids_[1],5))return 2011;
            }
        }
        view_armed_=false;
        if(look_ignored_){if(valid(ids_[1])){clear();if(!call(ids_[1],23))return 2012;}look_ignored_=false;}
        if(move_ignored_){if(valid(ids_[1])){clear();if(!call(ids_[1],7))return 2012;}move_ignored_=false;}
        for(auto& id:characters_){if(id.address && valid(id)){clear();if(!call(id,2))return 2013;}id={};}
        for(auto* id:{&camera_}){
            if(id->address && valid(*id)){clear();if(!call(*id,2))return 2013;}
            *id={};
        }
        TargetStrongReferenceOps ops{base_,{}};
        const auto result=leases_.close(ops,owner_);
        if(result==StrongLeaseResult::Deferred)return 407;
        if(result!=StrongLeaseResult::Ok)return 2014;
        pool_=false;for(auto& id:components_)id={};state_=reason==0?4:reason==1?5:6;return 0;
    }
    void poll(){
        if(!pool_)return;
        if(state_==3){if(error_==407)error_=close(reason_);return;}
        if(!TargetPodSchemaOps{base_}.context())return;
        elapsed_=std::chrono::duration<double>(std::chrono::steady_clock::now()-clock_).count();
        if(!current()){error_=close(1);return;}
        if(state_==1){if(elapsed_>15.)error_=close(1);return;}
        if(Timing::finished(elapsed_)){error_=close();return;}
        clear();put(0,ids_[1].address);if(!call(ids_[3],12) || args_[8]){error_=close(1);return;}
        if(!advance(elapsed_)){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
    }
    void command(uint64_t base,MeshPacket& packet,bool conflict){
        const auto op=packet.operation;
        if(packet.version!=3 || op<70 || op>73 || !packet.owner || packet.error || packet.state){packet.error=2000;return;}
        auto* raw=reinterpret_cast<uint8_t*>(&packet);
        if(std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) ||
           std::any_of(raw+(op==70?88+16*inputs:88),raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2000;return;}
        if(pool_ && owner_!=packet.owner){packet.error=2001;return;}
        if(op==70){
            if(pool_ || conflict){packet.error=2001;return;}
            base_=base;owner_=packet.owner;error_=0;failed_step_=0;reason_=0;poses_=0;elapsed_=0;animation_at_=audio_at_=-1;timing_={};placed_=false;effect_count_=0;last_hit_=-10.;last_attacker_=0;
            std::memcpy(ids_,raw+88,sizeof(ids_));
            if(!TargetPodSchemaOps{base_}.context()){packet.error=407;return;}
            for(const auto& id:ids_)if(!valid(id)){packet.error=2002;return;}
            for(size_t i=0;i<31;++i)if(!schema(i)){packet.error=2003;packet.step=uint32_t(i+1);return;}
            if(!named(base_,ids_[4].address,"CameraActor","/Script/Engine") ||
               !named(base_,ids_[5].address,"SkeletalMeshActor","/Script/Engine") ||
               !named(base_,ids_[6].address,"SkeletalMeshComponent","/Script/Engine") ||
               !named(base_,ids_[11].address,"CameraComponent","/Script/Engine") || !current() || !assets()){packet.error=2004;return;}
            if(leases_.begin(owner_)!=StrongLeaseResult::Ok){packet.error=2005;return;}
            pool_=true;state_=1;clock_=std::chrono::steady_clock::now();
            bool ok=true;for(auto& id:ids_)if(!hold(id)){ok=false;break;}
            if(ok){clear();ok=call(ids_[1],6);saved_=call_capture(base_,get<uint64_t>());ok=ok && hold(saved_);}
            if(ok){clear();ok=call(ids_[2],3);std::memcpy(origin_,args_,24);}
            if(ok){clear();ok=call(ids_[2],4);yaw_=get<double>(8);const double rad=yaw_*3.141592653589793/180.;origin_[0]+=std::cos(rad)*300.;origin_[1]+=std::sin(rad)*300.;
                for(auto v:origin_)ok=ok && std::isfinite(v) && std::abs(v)<1.e8;ok=ok && std::isfinite(yaw_);}
            constexpr size_t mesh_slots[]={7,12,13,14,16,17,18,19};
            for(unsigned i=0;ok && i<8;++i){
                ok=spawn(ids_[5],characters_[i]);
                if(ok){clear();put(0,ids_[6].address);ok=call(characters_[i],15);components_[i]=call_capture(base_,get<uint64_t>(8));ok=ok && hold(components_[i]);}
                if(ok){clear();put(0,ids_[mesh_slots[i]].address);ok=call(components_[i],16);}
                if(ok){clear();args_[0]=2;ok=call(components_[i],10);}
                if(ok && (i==1 || i==4 || i==5)){clear();put(0,components_[i<3?0:3].address);args_[8]=1;ok=call(components_[i],25);}
            }
            if(ok)ok=attach(components_[2],components_[1],"Head");
            if(ok){
                // Observed on the live, game-assembled Hair_Lune_2_skl on
                // BP_GameMenu_Lune (runtime-cinematic-live-default-lune evidence).
                // Reuse the existing native mesh relative-transform contract.
                clear();
                constexpr double q=0.7071067811865475244;
                put(8,q);put(24,q); // UE pitch -90 quaternion (0,+sqrt(.5),0,+sqrt(.5))
                put(32,17.65);put(40,2.83);
                for(unsigned axis=0;axis<3;++axis)put(64+8*axis,1.055);
                args_[352]=1; // teleport, no sweep
                ok=call(components_[2],29);
            }
            if(ok)ok=attach(components_[7],components_[3],"weapon_r");
            if(ok){
                // Native live BP_WeaponSkin_Maelle_Base uses weapon_r and
                // relative rotation (pitch=0,yaw=180,roll=-180), i.e. Y=1.
                clear();put(8,1.);
                for(unsigned axis=0;axis<3;++axis)put(64+8*axis,1.);
                args_[352]=1;ok=call(components_[7],29);
            }
            if(ok)ok=spawn(ids_[4],camera_);
            if(ok){clear();put(0,ids_[11].address);ok=call(camera_,15);const auto cc=call_capture(base_,get<uint64_t>(8));if(ok){clear();put(0,50.f);ok=call(cc,24);}}
            if(ok){clear();put(0,ids_[1].address);put(8,ids_[9].address);put(16,.35f);put(20,1.f);ok=call(ids_[3],19);audio_=call_capture(base_,get<uint64_t>(48));ok=ok && hold(audio_);}
            if(!ok){failed_step_=step_;error_=2006;const auto e=close(2);if(e)error_=e;}
        }else if(op==71){
            if(!pool_ || state_!=1 || !current() || conflict){packet.error=2007;return;}
            clear();put(0,ids_[1].address);if(!call(ids_[3],12) || args_[8]){packet.error=2007;return;}
            bool ok=advance(0.);
            if(ok){clear();args_[0]=1;ok=call(ids_[1],7);move_ignored_=ok;}
            if(ok){clear();args_[0]=1;ok=call(ids_[1],23);look_ignored_=ok;}
            if(ok){clear();put(0,camera_.address);view_armed_=true;ok=call(ids_[1],5);}
            if(ok){state_=2;clock_=std::chrono::steady_clock::now();}
            else{failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }else if(op==72){error_=close(1);}
        else poll();
        packet.error=error_;packet.state=state_;packet.actor=camera_;packet.component=components_[0];
        packet.position[0]=elapsed_;packet.position[1]=animation_at_;packet.position[2]=audio_at_;
        packet.step=failed_step_?failed_step_:step_;packet.sections=(timing_.animation?1U:0U)|(timing_.audio?2U:0U)|(poses_?4U:0U)|(timing_.audio_count<<8)|(effect_count_<<16);
        packet.section_id=leases_.active();packet.reserved=poses_;
    }
};
}
#pragma warning(pop)
