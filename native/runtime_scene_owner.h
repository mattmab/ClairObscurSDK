#pragma once
#include "engine_profiles.h"
#include "runtime_cinematic_profile.h"
#include "runtime_cinematic_effects_profile.h"
#include "runtime_cinematic_timing.h"
#include <chrono>
#include <utility>
#include "runtime_scene_plan.h"
#include "runtime_scene_input.h"
#include "runtime_scene_timeline.h"
#include "runtime_scene_registry.h"
#include "music_audio_profile.h"
#include "original_audio_pause.h"
#include "enemy_arena_engine_binding.h"
#include "npc_current_context_guard.h"
#include "npc_grounded_preview.h"
#include "validated_engine_profile_call.h"
#include "volume_query_profile.h"
#pragma warning(push)
#pragma warning(disable:4324)

namespace e33_runtime_scene {
using namespace e33_runtime_cinematic;
using namespace e33_mesh;
// Bounded six-instance scene owner; exact mesh profiles, no reflection codec expansion.
class Owner {
    static constexpr size_t inputs=134;
    inline static constexpr size_t reused[]={0,1,2,3,4,6,7,9,12,13,16,21,34,47,63};
    StrongLeasePool<512> leases_;
    StrongLeasePool<8> preview_leases_;
    StrongLeasePool<4> cue_leases_[23];
    OriginalAudioPause music_pause_;
#ifdef E33_RETIRED_WORLD_SESSION
    e33_retired_world::Anchor retired_anchor_;
    bool retired_cleanup_=false;
#endif
    CallIdentity sounds_[23]{},preview_sound_{};bool preview_active_=false;double preview_limit_=5.;
    std::chrono::steady_clock::time_point preview_clock_;
    CallIdentity audio_component(unsigned i)const{return i>=9 && sounds_[i-9].address?sounds_[i-9]:audio_;}
    StrongLeasePool<128> loading_leases_;
    AssetCatalog catalogs_[5];
    bool loading_=false;
    CallIdentity ids_[inputs]{},camera_{},characters_[36]{},components_[36]{},audio_{},saved_{};
    bool placed_=false,configured_=false,visual_staging_=false;
    uint64_t primary_lease_=0,visual_arena_leases_[5]{};
    CallIdentity visual_world_{},visual_arena_ids_[5]{};
    bool visual_arena_requested_=false;
    e33_enemy_spawn::EngineArenaBinding visual_arena_binding_{};
    e33_enemy_spawn::ArenaBindingState visual_arena_state_{};
    e33_npc_presentation::GroundedPreview visual_ground_{};
    e33_npc_presentation::PreviewPlacementResult visual_ground_result_=e33_npc_presentation::PreviewPlacementResult::Rejected;
    bool visual_ground_requested_=false;double visual_ground_scale_[3]{};unsigned visual_ground_candidates_=0;
    Plan plan_;
    bool animation_done_[6]{},audio_done_[32]{},impact_done_[9]{},recoil_done_[9]{},trail_done_[2]{};
    int active_animation_[6]{-1,-1,-1,-1,-1,-1};
    const CallIdentity& animation_id(unsigned event)const{return ids_[event<6?63+event*7:109+event-6];}
    unsigned selected_=0;
    double editor_fov_=90.;
    bool snapped_view_=false;
    bool photo_mode_=false;
    CallIdentity photo_rotation_{},photo_camera_{},photo_tick_{},photo_enable_tick_{};
    CallIdentity timeline_widget_{},timeline_add_{},photo_hud_{};uint32_t timeline_flags_=0;
    bool scene_cursor_owned_=false,scene_cursor_saved_=false;
    int photo_audition_=-1;unsigned photo_audition_slot_=0;double photo_age_=0.;
    bool editor_input_=true,mouse_valid_=false,left_down_=false,camera_selected_=false;
    POINT mouse_{};
    double grab_depth_=0,grab_offset_[3]{};int hovered_=-1,glowing_=-1;
    CallIdentity original_materials_[6][32]{};int material_count_[6]{};
    double editor_time_=0;
    TimelineDrag timeline_drag_;
    bool timeline_press_=false,timeline_message_down_=false;
    POINT timeline_press_point_{};RECT timeline_press_area_{};
    std::chrono::steady_clock::time_point editor_clock_;
    CallIdentity shot_{},guides_[9]{},guide_components_[9]{};
    CallIdentity effects_[11]{};
    double effect_at_[11]{},effect_life_[11]{},last_hit_=-10.;
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
    const MeshFunction& profile(size_t i)const{
        static const MeshField position_fields[]={{"InPos","FloatProperty",0,4,6755469234274944ULL,0x6e11560ULL,"","",0,"",0U,""},{"bFireNotifies","BoolProperty",4,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
        static const MeshFunction position_profile={"SkeletalMeshComponent","SetPosition",67240963,5,8,65535,0x3600180,position_fields,2};
        static const MeshField volume_fields[]={{"NewVolumeMultiplier","FloatProperty",0,4,6755469234274944ULL,0x6e11560ULL,"","",0,"",0U,""}};
        static const MeshFunction volume_profile={"AudioComponent","SetVolumeMultiplier",67240963,4,4,65535,0x353c420,volume_fields,1};
        static const MeshField paused_fields[]={{"bTickableWhenPaused","BoolProperty",0,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
        static const MeshField enabled_fields[]={{"bEnabled","BoolProperty",0,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
        static const MeshFunction paused_profile={"ActorComponent","SetTickableWhenPaused",67240963,1,1,65535,0x353c200,paused_fields,1};
        static const MeshFunction enabled_profile={"ActorComponent","SetComponentTickEnabled",67240962,1,1,65535,0x353b0b0,enabled_fields,1};
        static const MeshField viewport_fields[]={{"ZOrder","IntProperty",0,4,6759867280786048ULL,0x6e10a98ULL,"","",0,"",0U,""}};
        static const MeshFunction viewport_profile={"UserWidget","AddToViewport",67240971,4,4,65535,0x31355b0,viewport_fields,1};
        if(i==41)return viewport_profile;
        if(i==40)return enabled_profile;
        if(i==39)return paused_profile;
        if(i==38)return e33_engine_profiles::profiles[23];
        if(i==37)return volume_profile;
        return i>=33?e33_engine_profiles::profiles[i==33?35:i==34?36:i==35?38:62]:i==32?e33_engine_profiles::profiles[46]:i==31?position_profile:i>=30?fx_functions[i-30]:i==29?mesh_functions[31]:i<15?e33_engine_profiles::profiles[reused[i]]:demo_functions[i-15];
    }
    CallIdentity function_id(size_t i)const{return i==41?timeline_add_:i==40?photo_enable_tick_:i==39?photo_tick_:i==38?photo_rotation_:ids_[i==37?133:i>=33?105+i-33:i==32?103:i==31?99:i>=30?56+i-30:21+i];}
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
            exact_name(base_,fn+24,p.name) && named(base_,local_read<uint64_t>(fn+32),p.owner,i==41?"/Script/UMG":i==30?"/Script/Niagara":"/Script/Engine") &&
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
        const auto result=leases_.acquire(ops,owner_,id.address,token);
        if(&id==&characters_[0])primary_lease_=token;
        return result==StrongLeaseResult::Ok && stabilize_retained_identity(ops,id);
    }
    uint64_t field(CallIdentity id,const FieldProof& p)const{
        if(!valid(id))return 0;
        auto cls=local_read<uint64_t>(id.address+16);
        for(unsigned class_depth=0;cls && class_depth<128;++class_depth,cls=local_read<uint64_t>(cls+0x40)){
            if(!named(base_,cls,p.owner,std::strcmp(p.owner,"Widget")==0?"/Script/UMG":std::strcmp(p.owner,"WBP_PhotoModeHUD_C")==0?"/Game/UI/Widgets/PhotoMode/WBP_PhotoModeHUD":"/Script/Engine"))continue;
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
    bool palette_named(uint64_t object,const char* name,const char* package)const{
        if(!call_capture(base_,object).address || !candidate_name(base_,object+24,name))return false;
        const auto outer=local_read<uint64_t>(object+32);
        return call_capture(base_,outer).address && candidate_name(base_,outer+24,package);
    }
    bool assets(){
        failed_step_=4000;
        constexpr const char* packages[]={"/Game/FX/FX_Leo/Fx/Lune/Thunder_Fall/Systems/NS_Impact_Electric1","/Game/FX/FX_Leo/Fx/Maelle/FX_FlowerPetalsBurst","/Game/FX/FX_Leo/Fx/Maelle/FX_MaelleSword","/Game/FX/FX_Leo/Fx/Lune/FX_LuneTrail"};
        constexpr const char* names[]={"NS_Impact_Electric1","FX_FlowerPetalsBurst","FX_MaelleSword","FX_LuneTrail"};
        for(unsigned i=0;i<4;++i)if(!named(base_,ids_[52+i].address,names[i],packages[i]) || !named(base_,local_read<uint64_t>(ids_[52+i].address+16),"NiagaraSystem","/Script/Niagara"))return false;
        if(!named(base_,ids_[51].address,"Default__NiagaraFunctionLibrary","/Script/Niagara"))return false;
        constexpr size_t mesh_slots[]={7,12,13,14,16,17,18,19};
        for(size_t i=0;i<8;++i){failed_step_=4100+uint32_t(i);const auto& id=ids_[mesh_slots[i]];
            if(!named(base_,id.address,character_names[i],character_packages[i]) ||
               !named(base_,local_read<uint64_t>(id.address+16),"SkeletalMesh","/Script/Engine"))return false;}
        failed_step_=4200;
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
        failed_step_=4300+i;
        const auto mesh_ref=field(ids_[bodies[i]],mesh_skeleton),anim_ref=field(ids_[animations[i]],animation_skeleton);
        const auto notify=field(ids_[animations[i]],notifies),root=field(ids_[animations[i]],root_motion);
        if(!(mesh_ref && anim_ref && notify && root && local_read<uint64_t>(mesh_ref) &&
            local_read<uint64_t>(mesh_ref)==local_read<uint64_t>(anim_ref) &&
            local_read<int32_t>(notify+8)==0 && local_read<int32_t>(notify+12)>=0 && !local_read<uint8_t>(root)))return false;
        }
        constexpr FieldProof additive={"AnimSequence","AdditiveAnimType","ByteProperty",328,1,6756568745902593ULL,0x6e10420ULL,0U};
        for(unsigned slot=0;slot<unsigned(plan_.count);++slot){
            const unsigned role=unsigned(plan_.roles[slot]);
            for(unsigned part=0;part<6;++part){
                failed_step_=4400+slot*10+part;
                const auto& p=scene_parts[role][part];if(!p.name[0])continue;
                const auto& id=ids_[57+slot*7+part];
                if(!palette_named(id.address,p.name,p.package) || !named(base_,local_read<uint64_t>(id.address+16),"SkeletalMesh","/Script/Engine"))return false;
            }
            if(plan_.clips[slot]<0.)continue;
            failed_step_=4500+slot;
            const auto& clip=scene_clips[unsigned(plan_.clips[slot])];const auto& id=ids_[63+slot*7];
            if(!palette_named(id.address,clip.name,clip.package) || !named(base_,local_read<uint64_t>(id.address+16),"AnimSequence","/Script/Engine"))return false;
            failed_step_=4600+slot;
            const auto mesh_ref=field(ids_[57+slot*7],mesh_skeleton),anim_ref=field(id,animation_skeleton),notify=field(id,notifies),root=field(id,root_motion),add=field(id,additive);
            if(!(mesh_ref && anim_ref && notify && root && add && local_read<uint64_t>(mesh_ref) && local_read<uint64_t>(mesh_ref)==local_read<uint64_t>(anim_ref) && local_read<int32_t>(notify+8)==0 && local_read<int32_t>(notify+12)>=0 && !local_read<uint8_t>(root) && !local_read<uint8_t>(add)))return false;
        }
        for(unsigned i=0;i<unsigned(plan_.extra_count);++i){
            if(plan_.extra[i][2]<0.)continue;
            const unsigned slot=unsigned(plan_.extra[i][0]);const auto& id=ids_[109+i];const auto& clip=scene_clips[unsigned(plan_.extra[i][2])];failed_step_=4700+i;
            if(!palette_named(id.address,clip.name,clip.package) || !named(base_,local_read<uint64_t>(id.address+16),"AnimSequence","/Script/Engine"))return false;
            const auto mesh_ref=field(ids_[57+slot*7],mesh_skeleton),anim_ref=field(id,animation_skeleton),notify=field(id,notifies),root=field(id,root_motion),add=field(id,additive);
            if(!(mesh_ref && anim_ref && notify && root && add && local_read<uint64_t>(mesh_ref) && local_read<uint64_t>(mesh_ref)==local_read<uint64_t>(anim_ref) && local_read<int32_t>(notify+8)==0 && local_read<int32_t>(notify+12)>=0 && !local_read<uint8_t>(root) && !local_read<uint8_t>(add)))return false;
        }failed_step_=0;return true;
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
    bool effect(unsigned asset,const double* position,double scale,double seconds,double lifetime=.9){
        if(effect_count_>=11)return false;
        clear();put(0,ids_[1].address);put(8,ids_[52+asset].address);
        std::memcpy(args_+16,position,24);put(48,yaw_);
        for(unsigned axis=0;axis<3;++axis)put(64+8*axis,scale);
        args_[89]=1; // activate, no pooling/auto-destroy/pre-cull: private lifetime
        if(!call(ids_[51],30))return false;
        auto& component=effects_[effect_count_];component=call_capture(base_,get<uint64_t>(96));
        if(!component.address || !named(base_,local_read<uint64_t>(component.address+16),"NiagaraComponent","/Script/Niagara") || !hold(component))return false;
        effect_at_[effect_count_]=seconds;effect_life_[effect_count_++]=lifetime;return true;
    }
    bool expire_effects(double seconds){
        // First two are attached attack trails. Impact bursts have a bounded
        // lifetime even if the source system itself loops indefinitely.
        for(unsigned i=0;i<effect_count_;++i)if(effects_[i].address && seconds-effect_at_[i]>=effect_life_[i]){
            if(valid(effects_[i])){clear();put(0,effects_[i].address);if(!call(effects_[i],22))return false;}
            effects_[i]={};
        }return true;
    }
    bool advance(double seconds){
        const double rad=3.141592653589793/180.,u=std::clamp((seconds-plan_.camera[4])/(plan_.camera[5]-plan_.camera[4]),0.,1.);
        const double forward[]={std::cos(yaw_*rad),std::sin(yaw_*rad)};
        const double side[]={-forward[1],forward[0]};
        double point[]={origin_[0],origin_[1],origin_[2]};
        if(!placed_){
            for(unsigned i=0;i<unsigned(plan_.count)*6;++i){if(!characters_[i].address || scene_parts[unsigned(plan_.roles[i/6])][i%6].mode>=2)continue;
                const auto& pose_data=plan_.poses[i/6];
                const double actor_point[]={point[0]+forward[0]*pose_data[0]+side[0]*pose_data[1],
                    point[1]+forward[1]*pose_data[0]+side[1]*pose_data[1],point[2]+pose_data[2]};
                const double character_rotation[]={pose_data[3],yaw_+pose_data[4],pose_data[5]};
                if(!pose(characters_[i],actor_point,character_rotation)){step_+=1000;return false;}
            }placed_=true;
        }
        if(!visual_staging_){
        const double angle=(yaw_+180.)*rad+u*2.*3.141592653589793;
        double camera[]={point[0]+forward[0]*plan_.camera[1]+std::cos(angle)*plan_.camera[0],
            point[1]+forward[1]*plan_.camera[1]+std::sin(angle)*plan_.camera[0],point[2]+plan_.camera[2]+plan_.camera[3]*std::sin(u*3.141592653589793)};
        const double delta[]={point[0]+forward[0]*plan_.camera[1]-camera[0],point[1]+forward[1]*plan_.camera[1]-camera[1],point[2]+100.-camera[2]};
        const double rotation[]={std::atan2(delta[2],std::hypot(delta[0],delta[1]))/rad,
            std::atan2(delta[1],delta[0])/rad,0.};
        double shot[7]{};
        if(plan_.camera_pose(seconds,shot)){
            camera[0]=point[0]+forward[0]*shot[0]+side[0]*shot[1];camera[1]=point[1]+forward[1]*shot[0]+side[1]*shot[1];camera[2]=point[2]+shot[2];
            double angles[]={shot[3],yaw_+shot[4],shot[5]};
            if(!pose(camera_,camera,angles))return false;
            clear();put(0,ids_[11].address);if(!call(camera_,15))return false;const auto cc=call_capture(base_,get<uint64_t>(8));clear();put(0,float(shot[6]));if(!call(cc,24))return false;
        }else if(!pose(camera_,camera,rotation)){step_+=2000;return false;}
        ++poses_;
        }
        for(unsigned i=0;i<unsigned(plan_.count);++i){
            const auto event=plan_.active_animation(i,seconds);
            if(!mask_animation_scale(i,event))return false;
            if(seconds<plan_.start(event) || active_animation_[i]==int(event))continue;
            clear();if(plan_.clip(event)<0.){if(!call(components_[i*6],18))return false;}
            else{put(0,animation_id(event).address);args_[8]=uint8_t(plan_.loop(event));if(!call(components_[i*6],17))return false;}
            active_animation_[i]=int(event);animation_done_[i]=true;if(!timing_.animation)animation_at_=seconds;timing_.animation=true;
        }
        for(unsigned i=0;i<2;++i)if(plan_.trail[i]>=0. && !trail_done_[i] && seconds>=plan_.trail[i]){
            if(!effect(i?2:3,point,i?1.:.5,seconds,19.))return false;
            if(!attach(effects_[effect_count_-1],components_[unsigned(plan_.bindings[i])*6+(i?3:0)],i?nullptr:"foot_r"))return false;
            trail_done_[i]=true;
        }
        const unsigned target_slot=plan_.bindings[2]>=0.?unsigned(plan_.bindings[2]):0U;
        const auto& target_pose=plan_.poses[target_slot];
        const double baseline[]={point[0]+forward[0]*target_pose[0]+side[0]*target_pose[1],
            point[1]+forward[1]*target_pose[0]+side[1]*target_pose[1],point[2]+target_pose[2]};
        for(unsigned i=0;i<9;++i){
            const unsigned attacker=(i==1 || i==3 || i==6)?1U:0U;
            if(plan_.impact[i]>=0. && !impact_done_[i] && seconds>=plan_.impact[i]){
                const double impact[]={baseline[0],baseline[1],baseline[2]+85.*target_pose[8]};
                if(!effect(attacker,impact,attacker?.8:.65,seconds))return false;
                impact_done_[i]=true;
            }
            if(plan_.recoil[i]>=0. && !recoil_done_[i] && seconds>=plan_.recoil[i]){
                last_attacker_=attacker;last_hit_=seconds;recoil_done_[i]=true;
            }
        }
        for(unsigned i=0;i<32;++i)if(plan_.audio[i]>=0. && !audio_done_[i] && seconds>=plan_.audio[i]){
            if(!gain(i))return false;clear();if(!call(audio_component(i),20))return false;
            audio_done_[i]=true;if(!timing_.audio)audio_at_=seconds;timing_.audio_fired();
        }
        // Preserve the experimental v12 recoil exactly; refinement is deferred.
        const double age=seconds-last_hit_,pulse=age>=0. && age<.55?std::sin(age/.55*3.141592653589793):0.;
        const double direction=last_attacker_?1.:-1.;
        const double target_point[]={baseline[0]+forward[0]*28.*pulse+side[0]*direction*12.*pulse,
            baseline[1]+forward[1]*28.*pulse+side[1]*direction*12.*pulse,baseline[2]+10.*pulse};
        const double reaction[]={target_pose[3]+12.*pulse,yaw_+target_pose[4],target_pose[5]+direction*9.*pulse};
        if(plan_.bindings[2]>=0. && !pose(characters_[target_slot*6],target_point,reaction))return false;
        if(!expire_effects(seconds))return false;
        return true;
    }
    bool stop_preview(){
        if(!preview_active_)return true;
        if(preview_sound_.address && valid(preview_sound_)){clear();if(!call(preview_sound_,21))return false;clear();put(0,preview_sound_.address);if(!call(preview_sound_,22))return false;}
        preview_sound_={};TargetStrongReferenceOps ops{base_,{}};
        if(preview_leases_.close(ops,owner_)!=StrongLeaseResult::Ok)return false;
        preview_active_=false;return true;
    }
    bool clear_cue(unsigned slot){
        auto& sound=sounds_[slot];
        if(sound.address && valid(sound)){clear();if(!call(sound,21))return false;clear();put(0,sound.address);if(!call(sound,22))return false;}
        sound={};TargetStrongReferenceOps ops{base_,{}};
        return !cue_leases_[slot].owns(owner_) || cue_leases_[slot].close(ops,owner_)==StrongLeaseResult::Ok;
    }
    bool gain(unsigned slot){clear();put(0,float(plan_.gains[slot]));return call(audio_component(slot),37);}
    bool create_audio(CallIdentity source,CallIdentity& result,bool preview,int slot=-1){
        auto retain=[&](CallIdentity& id){if(!preview && slot<0)return hold(id);TargetStrongReferenceOps ops{base_,id};uint64_t token=0;return valid(id) && (preview?preview_leases_.acquire(ops,owner_,id.address,token):cue_leases_[unsigned(slot)].acquire(ops,owner_,id.address,token))==StrongLeaseResult::Ok && stabilize_retained_identity(ops,id);};
        if(!retain(source))return false;
        clear();put(0,ids_[1].address);put(8,source.address);put(16,preview?.2f:.35f);put(20,1.f);
        if(!call(ids_[3],19))return false;
        result=call_capture(base_,get<uint64_t>(48));return result.address && retain(result);
    }
    bool editor_place(){
        const double rad=3.141592653589793/180.,f[]={std::cos(yaw_*rad),std::sin(yaw_*rad)},r[]={-f[1],f[0]};
        for(unsigned slot=0;slot<unsigned(plan_.count);++slot){const auto& v=plan_.poses[slot];
            const double pos[]={origin_[0]+f[0]*v[0]+r[0]*v[1],origin_[1]+f[1]*v[0]+r[1]*v[1],origin_[2]+v[2]},rot[]={v[3],yaw_+v[4],v[5]};
            for(unsigned part=0;part<6;++part){const unsigned i=slot*6+part;const auto& p=scene_parts[unsigned(plan_.roles[slot])][part];
                if(!characters_[i].address || p.mode>=2)continue;
                clear();std::memcpy(args_,p.quaternion,32);std::memcpy(args_+32,p.position,24);for(unsigned axis=0;axis<3;++axis)put(64+8*axis,p.scale[axis]*v[6+axis]);args_[352]=1;
                if(!call(components_[i],29) || !pose(characters_[i],pos,rot))return false;
            }
        }
        for(unsigned slot=0;slot<unsigned(plan_.count);++slot)if(!mask_animation_scale(slot,plan_.active_animation(slot,editor_time_)))return false;
        placed_=true;return true;
    }
    bool mask_animation_scale(unsigned slot,unsigned event){
        const auto role=unsigned(plan_.roles[slot]);const auto& part=scene_parts[role][0];
        if(std::strcmp(part.name,"Face_Anger"))return true;
        const auto clip=plan_.clip(event);const double scale=clip<0?1.:scene_clips[unsigned(clip)].preview_scale;
        double position[3]{},rotation[3]{};
        clear();if(!call(characters_[slot*6],3))return false;std::memcpy(position,args_,24);
        clear();if(!call(characters_[slot*6],4))return false;std::memcpy(rotation,args_,24);
        clear();std::memcpy(args_,part.quaternion,32);std::memcpy(args_+32,part.position,24);
        for(unsigned axis=0;axis<3;++axis)put(64+8*axis,part.scale[axis]*plan_.poses[slot][6+axis]*scale);
        args_[352]=1;return call(components_[slot*6],29) && pose(characters_[slot*6],position,rotation);
    }
    bool editor_seek(double seconds,bool running=false){
        if(!std::isfinite(seconds) || seconds<0. || seconds>plan_.duration)return false;
        photo_audition_=-1;editor_time_=seconds;
        constexpr FieldProof length_field={"AnimSequenceBase","SequenceLength","FloatProperty",144,4,11268964466426389ULL,0x6e11560ULL,0U};
        for(unsigned i=0;i<unsigned(plan_.count);++i){
            const unsigned event=plan_.active_animation(i,seconds);
            if(!mask_animation_scale(i,event))return false;
            if(plan_.clip(event)<0.){clear();if(!call(components_[i*6],17))return false;clear();if(!call(components_[i*6],18))return false;continue;}
            const auto length_at=field(animation_id(event),length_field);if(!length_at)return false;
            const double length=local_read<float>(length_at);if(!std::isfinite(length) || length<=0.)return false;
            clear();put(0,animation_id(event).address);args_[8]=uint8_t(plan_.loop(event));if(!call(components_[i*6],17))return false;
            if(!running || seconds<plan_.start(event)){clear();if(!call(components_[i*6],18))return false;}
            const double age=std::max(0.,seconds-plan_.start(event));clear();put(0,float(plan_.loop(event)?std::fmod(age,length):std::min(age,length))); // bFireNotifies remains false
            if(!call(components_[i*6],31))return false;
            animation_done_[i]=seconds>=plan_.start(event);
        }
        if(!running){for(unsigned i=0;i<32;++i)audio_done_[i]=plan_.audio[i]>=0. && plan_.audio[i]<seconds;for(auto& sound:sounds_)if(sound.address){clear();if(!call(sound,21))return false;}clear();return call(audio_,21);}return true;
    }
    bool editor_fov(double fov){
        clear();put(0,ids_[11].address);if(!call(camera_,15))return false;
        const auto component=call_capture(base_,get<uint64_t>(8));clear();put(0,float(fov));
        if(!call(component,24))return false;editor_fov_=fov;return true;
    }
    bool photo_read(){
        constexpr FieldProof fov={"CameraComponent","FieldOfView","FloatProperty",560,4,6755477824209413ULL,0x6e11560ULL,0U};
        constexpr FieldProof rotation={"SceneComponent","RelativeRotation","StructProperty",320,24,18014472597668405ULL,0x6e136a0ULL,0U};
        constexpr FieldProof location={"SceneComponent","RelativeLocation","StructProperty",296,24,20266272411353653ULL,0x6e136a0ULL,0U};
        const auto fa=field(photo_camera_,fov),ra=field(photo_camera_,rotation),la=field(photo_camera_,location);
        if(!fa || !ra || !la)return false;
        // Stock photo camera has no translation or pitch/yaw offset. Reject unsupported rigs.
        for(unsigned i=0;i<3;++i)if(std::abs(local_read<double>(la+8*i))>.001)return false;
        if(std::abs(local_read<double>(ra))>.001 || std::abs(local_read<double>(ra+8))>.001)return false;
        clear();if(!call(ids_[2],3))return false;std::memcpy(plan_.editor_camera,args_,24);
        clear();if(!call(ids_[2],4))return false;std::memcpy(plan_.editor_camera+3,args_,24);
        plan_.editor_camera[5]=std::remainder(plan_.editor_camera[5]+local_read<double>(ra+16),360.);
        editor_fov_=local_read<float>(fa);
        return std::isfinite(editor_fov_) && editor_fov_>=20. && editor_fov_<=120. &&
            std::all_of(plan_.editor_camera,plan_.editor_camera+6,[](double v){return std::isfinite(v);});
    }
    bool photo_snap(const double* view){
        const double rotation[]={view[3],view[4],0.};
        if(!pose(ids_[2],view,rotation))return false;
        clear();std::memcpy(args_,rotation,24);if(!call(ids_[1],38))return false;
        // Preserve stock photo camera attachment and express roll on its local X axis.
        const double half=view[5]*3.141592653589793/360.;
        clear();put(0,-std::sin(half));put(24,std::cos(half));put(64,1.);put(72,1.);put(80,1.);args_[352]=1;
        if(!call(photo_camera_,29))return false;
        clear();put(0,float(view[6]));if(!call(photo_camera_,24))return false;
        editor_fov_=view[6];return true;
    }
    // Only the scene-owned skeletal components tick while the world remains paused.
    bool photo_mesh_ticks(){
        for(auto component:components_)if(component.address){
            // Paused Chaos cloth retains old world-space vertices. Preview only
            // the animated skin on our disposable meshes; never alter world pause.
            constexpr FieldProof blend={"SkeletalMeshComponent","ClothBlendWeight","FloatProperty",2648,4,6755477824209413ULL,0x6e11560ULL,0U};
            constexpr FieldProof disable={"SkeletalMeshComponent","bDisableClothSimulation","BoolProperty",2626,1,6755468160532485ULL,0x6e119b0ULL,0x4040001U};
            const auto weight=field(component,blend),flags=field(component,disable);
            if(!weight || !flags)return false;
            *reinterpret_cast<float*>(weight)=0.f;
            *reinterpret_cast<uint8_t*>(flags)|=4;
            clear();args_[0]=1;if(!call(component,39))return false;
            clear();args_[0]=1;if(!call(component,40))return false;
        }return true;
    }
    bool scene_cursor(bool enabled,bool capture=false){
        if(!enabled && !scene_cursor_owned_ && !capture)return true;
        if(!valid(ids_[1])){scene_cursor_owned_=false;return !enabled;}
        constexpr FieldProof cursor={"PlayerController","bShowMouseCursor","BoolProperty",1348,1,6755468160532485ULL,0x6e119b0ULL,0x1010001U};
        const auto at=field(ids_[1],cursor);if(!at)return false;
        auto value=local_read<uint8_t>(at);
        if(capture){scene_cursor_saved_=(value&1)!=0;return true;}
        if(enabled){
            scene_cursor_owned_=true;
            value|=1;
        }else{
            value=uint8_t((value&~1U)|(scene_cursor_saved_?1U:0U));scene_cursor_owned_=false;
        }
        *reinterpret_cast<uint8_t*>(at)=value;return true;
    }
    bool photo_preview_tick(double dt){
        if(photo_audition_<0)return true;
        const auto event=unsigned(photo_audition_);
        constexpr FieldProof length_field={"AnimSequenceBase","SequenceLength","FloatProperty",144,4,11268964466426389ULL,0x6e11560ULL,0U};
        const auto at=field(animation_id(event),length_field);if(!at)return false;
        const double length=local_read<float>(at);if(!std::isfinite(length)||length<=0.)return false;
        photo_age_+=dt;clear();put(0,float(plan_.loop(event)?std::fmod(photo_age_,length):std::min(photo_age_,length)));
        if(!call(components_[photo_audition_slot_*6],31))return false;
        if(!plan_.loop(event) && photo_age_>=length)photo_audition_=-1;
        return true;
    }
    bool camera_guides(){
        double shot[7]{};const double rad=3.141592653589793/180.;
        if(!plan_.camera_pose(editor_time_,shot)){shot[0]=-200.;shot[1]=-250.;shot[2]=plan_.camera[2];shot[3]=-10.;shot[4]=0.;shot[5]=0.;shot[6]=plan_.camera[6];}
        const double f[]={std::cos(yaw_*rad),std::sin(yaw_*rad)},r[]={-f[1],f[0]};
        const double p[]={origin_[0]+f[0]*shot[0]+r[0]*shot[1],origin_[1]+f[1]*shot[0]+r[1]*shot[1],origin_[2]+shot[2]},angles[]={shot[3],yaw_+shot[4],shot[5]};
        if(!pose(shot_,p,angles))return false;
        clear();put(0,ids_[11].address);if(!call(shot_,15))return false;const auto cc=call_capture(base_,get<uint64_t>(8));clear();put(0,float(shot[6]));if(!call(cc,24))return false;
        const double cp=std::cos(angles[0]*rad),sp=std::sin(angles[0]*rad),cy=std::cos(angles[1]*rad),sy=std::sin(angles[1]*rad),cr=std::cos(angles[2]*rad),sr=std::sin(angles[2]*rad);
        const double front[]={cp*cy,cp*sy,sp},right0[]={-sy,cy,0.},up0[]={-sp*cy,-sp*sy,cp};
        double corners[4][3]{};const double width=160.*std::tan(shot[6]*rad*.5),height=width*9./16.;
        for(unsigned k=0;k<4;++k)for(unsigned axis=0;axis<3;++axis){const double right=right0[axis]*cr+up0[axis]*sr,up=up0[axis]*cr-right0[axis]*sr;corners[k][axis]=p[axis]+160.*front[axis]+(k==0 || k==3?-width:width)*right+(k<2?height:-height)*up;}
        for(unsigned i=0;i<9;++i){
            double center[3]{},rotation[3]{},scale[]={.3,.2,.2};
            if(!i){std::memcpy(center,p,24);std::memcpy(rotation,angles,24);}
            else{const double* a=i<=4?p:corners[i-5];const double* b=i<=4?corners[i-1]:corners[(i-4)%4];double delta[3]{},length=0.;for(unsigned axis=0;axis<3;++axis){center[axis]=(a[axis]+b[axis])*.5;delta[axis]=b[axis]-a[axis];length+=delta[axis]*delta[axis];}scale[0]=std::sqrt(length)/100.;scale[1]=scale[2]=.04;rotation[0]=std::atan2(delta[2],std::hypot(delta[0],delta[1]))/rad;rotation[1]=std::atan2(delta[1],delta[0])/rad;}
            // StaticMeshActor's mesh is its root: setting a relative transform moves it.
            // Apply scale first, then restore the intended world position and angles.
            if(snapped_view_)scale[0]=scale[1]=scale[2]=0.;
            clear();put(24,1.);for(unsigned axis=0;axis<3;++axis)put(64+axis*8,scale[axis]);args_[352]=1;if(!call(guide_components_[i],29) || !pose(guides_[i],center,rotation))return false;
        }return true;
    }
    bool highlight(int slot){
        if(glowing_==slot)return true;
        if(glowing_>=0){const unsigned old=unsigned(glowing_);for(int j=0;j<material_count_[old];++j){clear();put(0,j);put(8,original_materials_[old][j].address);if(!call(components_[old*6],33))return false;}}
        glowing_=-1;if(slot<0)return true;const unsigned chosen=unsigned(slot);
        if(!material_count_[chosen]){clear();if(!call(components_[chosen*6],35))return false;const int count=get<int32_t>();if(count<1 || count>32)return true;
            for(int j=0;j<count;++j){clear();put(0,j);if(!call(components_[chosen*6],34))return false;auto material=call_capture(base_,get<uint64_t>(8));if(material.address && !hold(material))return false;original_materials_[chosen][j]=material;}material_count_[chosen]=count;}
        for(int j=0;j<material_count_[chosen];++j){clear();put(0,j);put(8,ids_[104].address);if(!call(components_[chosen*6],33))return false;}
        glowing_=slot;return true;
    }
    bool editor_tick(double dt){
        constexpr double rad=3.141592653589793/180.;auto& c=plan_.editor_camera;
        DWORD pid=0;const auto window=GetForegroundWindow();GetWindowThreadProcessId(window,&pid);POINT point{};RECT area{};
        const bool foreground=pid==GetCurrentProcessId() && GetCursorPos(&point) && ScreenToClient(window,&point) && GetClientRect(window,&area) && area.right>0 && area.bottom>0;
        auto key=[](int k){return (GetAsyncKeyState(k)&0x8000)!=0;};
        if(!foreground){left_down_=mouse_valid_=false;hovered_=-1;timeline_drag_.cancel();timeline_press_=timeline_message_down_=false;return highlight(-1);}
        if(!scene_cursor(!editor_input_))return false;
        if(!editor_input_){
            // Timeline has UI focus. Its visible track is the only raw-input region.
            const double x=double(point.x)/area.right,y=double(point.y)/area.bottom;
            double seconds=editor_time_;
            if(timeline_press_){
                timeline_press_=false;timeline_drag_.down=false;timeline_drag_.kind=-1;
                if(timeline_drag_.sample(plan_,selected_,true,double(timeline_press_point_.x)/timeline_press_area_.right,double(timeline_press_point_.y)/timeline_press_area_.bottom,double(timeline_press_area_.right),seconds)){state_=7;if(!editor_seek(seconds))return false;}
            }
            if(timeline_drag_.sample(plan_,selected_,timeline_message_down_,x,y,double(area.right),seconds)){state_=7;if(!editor_seek(seconds))return false;}
            left_down_=false;mouse_valid_=false;return highlight(int(selected_)) && camera_guides();
        }
        if(photo_mode_)return photo_read() && camera_guides();
        if(key(VK_RMENU)){left_down_=false;grab_depth_=0.;return camera_guides();}
        clear();if(!call(ids_[1],36))return false;const double dx=get<float>(),dy=get<float>(4);if(!std::isfinite(dx)||!std::isfinite(dy))return false;
        const bool moving=dx!=0. || dy!=0. || key('W') || key('S') || key('D') || key('A') || key('E') || key(VK_SPACE) || key('Q') || key(VK_CONTROL);
        if(snapped_view_ && moving){snapped_view_=false;if(!editor_fov(90.))return false;}
        if(!snapped_view_){c[4]=std::remainder(c[4]+std::clamp(dx,-4096.,4096.)*1.25,360.);c[3]=std::clamp(c[3]+std::clamp(dy,-4096.,4096.)*1.25,-89.,89.);c[5]=0.;}
        const double cp=std::cos(c[3]*rad),sp=std::sin(c[3]*rad),cy=std::cos(c[4]*rad),sy=std::sin(c[4]*rad),f[]={cp*cy,cp*sy,sp};
        const double forward=double(key('W'))-double(key('S')),side=double(key('D'))-double(key('A')),up=double(key('E')||key(VK_SPACE))-double(key('Q')||key(VK_CONTROL));
        const double speed=dt*1600.*(key(VK_SHIFT)?4.:1.)/std::max(1.,std::sqrt(forward*forward+side*side+up*up));
        c[0]+=speed*(f[0]*forward-sy*side);c[1]+=speed*(f[1]*forward+cy*side);c[2]+=speed*(f[2]*forward+up);
        for(unsigned i=0;i<3;++i)c[i]=std::clamp(c[i],-1.e8,1.e8);
        const double wf[]={std::cos(yaw_*rad),std::sin(yaw_*rad)},wr[]={-wf[1],wf[0]};
        hovered_=-1;double nearest=1.e30;
        for(unsigned i=0;i<unsigned(plan_.count);++i){const auto& v=plan_.poses[i];const auto name=scene_parts[unsigned(plan_.roles[i])][0].name;const bool mask=std::strcmp(name,"Face_Joy")==0 || std::strcmp(name,"Face_Anger")==0 || std::strcmp(name,"Face_Sadness")==0;const double radius=mask?70.:70.*v[8];const double delta[]={origin_[0]+wf[0]*v[0]+wr[0]*v[1]-c[0],origin_[1]+wf[1]*v[0]+wr[1]*v[1]-c[1],origin_[2]+v[2]+(mask?0.:80.*v[8])-c[2]};double along=0.,norm=0.;for(unsigned j=0;j<3;++j){along+=delta[j]*f[j];norm+=delta[j]*delta[j];}if(along>0. && along<nearest && norm-along*along<radius*radius){hovered_=int(i);nearest=along;}}
        double shot[7]{};if(!plan_.camera_pose(editor_time_,shot)){shot[0]=-200.;shot[1]=-250.;shot[2]=plan_.camera[2];shot[3]=-10.;shot[6]=plan_.camera[6];}
        const double camera_point[]={origin_[0]+wf[0]*shot[0]+wr[0]*shot[1],origin_[1]+wf[1]*shot[0]+wr[1]*shot[1],origin_[2]+shot[2]};
        double along=0.,norm=0.;for(unsigned j=0;j<3;++j){const double d=camera_point[j]-c[j];along+=d*f[j];norm+=d*d;}
        if(along>0. && along<nearest && norm-along*along<50.*50.){hovered_=6;nearest=along;}
        const bool left=key(VK_LBUTTON);
        if(left && !left_down_ && hovered_>=0){
            camera_selected_=hovered_==6;
            if(camera_selected_){timeline_drag_.camera_selected=plan_.editable_camera_key(editor_time_);if(timeline_drag_.camera_selected<0){camera_selected_=false;grab_depth_=0.;left_down_=left;return camera_guides();}editor_time_=plan_.keys[timeline_drag_.camera_selected][0];}
            else selected_=unsigned(hovered_);
            grab_depth_=nearest;
            const double* v=camera_selected_?plan_.keys[timeline_drag_.camera_selected]+1:plan_.poses[selected_];
            const double p[]={origin_[0]+wf[0]*v[0]+wr[0]*v[1],origin_[1]+wf[1]*v[0]+wr[1]*v[1],origin_[2]+v[2]};
            for(unsigned j=0;j<3;++j)grab_offset_[j]=p[j]-c[j]-f[j]*grab_depth_;
        }
        const bool dragging=left && (left_down_ || hovered_>=0) && grab_depth_>0.;
        if((camera_selected_ && timeline_drag_.camera_selected>=0) || (!camera_selected_ && selected_<unsigned(plan_.count))){
            double* v=camera_selected_?plan_.keys[timeline_drag_.camera_selected]+1:plan_.poses[selected_];bool changed=false;
            if(dragging){const double x=c[0]+f[0]*grab_depth_+grab_offset_[0]-origin_[0],y=c[1]+f[1]*grab_depth_+grab_offset_[1]-origin_[1];v[0]=std::clamp(x*wf[0]+y*wf[1],-5000.,5000.);v[1]=std::clamp(x*wr[0]+y*wr[1],-5000.,5000.);v[2]=std::clamp(c[2]+f[2]*grab_depth_+grab_offset_[2]-origin_[2],-5000.,5000.);changed=true;}
            const double fine=150.*dt*(key(VK_MENU)?.1:1.);const double delta[]={double(key(VK_NUMPAD8))-double(key(VK_NUMPAD2)),double(key(VK_NUMPAD6))-double(key(VK_NUMPAD4)),double(key(VK_NUMPAD9))-double(key(VK_NUMPAD3))};
            for(unsigned j=0;j<3;++j)if(delta[j]){v[j]=std::clamp(v[j]+fine*delta[j],-5000.,5000.);changed=true;}
            const double turn=double(key(VK_NUMPAD7))-double(key(VK_NUMPAD1));if(turn){v[4]=std::remainder(v[4]+fine*.1*turn,360.);changed=true;}
            if(changed && !(camera_selected_?camera_guides():editor_place()))return false;
        }
        left_down_=left;if(!left)grab_depth_=0.;
        return highlight(camera_selected_?-1:(dragging?int(selected_):(hovered_==6?-1:hovered_))) && camera_guides() && pose(camera_,c,c+3);
    }

public:
#include "runtime_scene_parameter_preflight.inl"
#include "runtime_scene_grounding.inl"
    void pointer_message(const MSG* message){
        if(!message || (state_!=7 && state_!=8) || editor_input_)return;
        if(message->message==WM_LBUTTONUP){timeline_message_down_=false;return;}
        if(message->message!=WM_LBUTTONDOWN)return;
        DWORD pid=0;GetWindowThreadProcessId(message->hwnd,&pid);
        RECT area{};if(pid!=GetCurrentProcessId() || !GetClientRect(message->hwnd,&area) || area.right<=0 || area.bottom<=0)return;
        timeline_press_point_={int16_t(LOWORD(message->lParam)),int16_t(HIWORD(message->lParam))};timeline_press_area_=area;timeline_press_=timeline_message_down_=true;
    }
    bool owns_timeline(CallIdentity widget)const{return pool_ && (state_==7 || state_==8) && same(timeline_widget_,widget) && valid(timeline_widget_);}
    bool timeline_shortcuts(CallIdentity widget)const{return (timeline_flags_&2) && owns_timeline(widget);}
    bool blocks_gameplay_shortcuts()const{return pool_ && (state_==2 || state_==7 || state_==8);}
    bool active()const{return pool_ || loading_;}
    bool visual_stage_active()const{return pool_ && visual_staging_;}
    void quarantine(){error_=2015;state_=3;}
    uint32_t close(uint32_t reason=0){
#ifdef E33_RETIRED_WORLD_SESSION
        if(pool_){
            e33_retired_world::TargetOps epoch{base_};
            if(!retired_anchor_.established()){
                if(loading_){TargetStrongReferenceOps refs{base_,{}};const auto loaded=loading_leases_.close(refs,owner_);
                    if(loaded!=StrongLeaseResult::Ok)return loaded==StrongLeaseResult::Deferred?407:2014;loading_=false;}
                const auto anchor_error=retired_anchor_.release(epoch,leases_,owner_);
                if(anchor_error)return anchor_error;
                TargetStrongReferenceOps refs{base_,{}};const auto result=leases_.close(refs,owner_);
                if(result!=StrongLeaseResult::Ok)return result==StrongLeaseResult::Deferred?407:2014;
                pool_=false;primary_lease_=0;retired_anchor_.reset();state_=5;return 0;
            }
            const auto proof=retired_anchor_.prove(epoch);
            if(proof==e33_retired_world::Result::Pending)return 407;
            if(proof==e33_retired_world::Result::Unknown)return 2052;
            if(proof==e33_retired_world::Result::Retired){
                retired_cleanup_=true;state_=3;reason_=reason;
                timeline_flags_=0;editor_input_=true;mouse_valid_=left_down_=false;
            }
            if(retired_cleanup_ && visual_arena_requested_)return 2055;
        }
#endif
        if(loading_){TargetStrongReferenceOps ops{base_,{}};if(loading_leases_.close(ops,owner_)!=StrongLeaseResult::Ok)return 407;loading_=false;}
        if(!pool_)return 0;
        // Revoke visual parameter authority before touching arena temporaries,
        // even if cleanup is deferred and must retain the owner for another poll.
        if(visual_staging_){state_=3;reason_=reason;}
        if(visual_arena_requested_ &&
           (!e33_enemy_spawn::close_arena_binding_temporary(visual_arena_binding_,visual_arena_state_) ||
            !visual_arena_binding_.close_owned_value()))return 407;
        timeline_flags_=0;timeline_widget_={};timeline_add_={};photo_hud_={};
        {const auto music_error=
#ifdef E33_RETIRED_WORLD_SESSION
            retired_cleanup_?music_pause_.retire_world(retired_anchor_):
#endif
            music_pause_.close();if(music_error)return music_error;}
        if(!stop_preview())return 2010;
        for(unsigned i=0;i<23;++i)if(!clear_cue(i))return 2010;
        for(auto& component:effects_){if(component.address && valid(component)){clear();put(0,component.address);if(!call(component,22))return 2010;}component={};}
        if(!TargetPodSchemaOps{base_}.context())return 407;
        state_=3;reason_=reason;
        if(audio_.address){if(valid(audio_)){clear();if(!call(audio_,21))return 2010;clear();put(0,audio_.address);if(!call(audio_,22))return 2010;}audio_={};}
#ifdef E33_RETIRED_WORLD_SESSION
        if(retired_cleanup_){
            // Epoch proof is native; never restore old gameplay presentation.
            view_armed_=look_ignored_=move_ignored_=scene_cursor_owned_=false;
        }
#endif
        if(view_armed_ && current()){
            clear();if(!call(ids_[1],6))return 2011;
            if(get<uint64_t>()==camera_.address && valid(saved_)){
                clear();put(0,saved_.address);if(!call(ids_[1],5))return 2011;
            }
        }
        view_armed_=false;
#ifdef E33_RETIRED_WORLD_SESSION
        if(!retired_cleanup_ && !scene_cursor(false))return 2012;
#else
        if(!scene_cursor(false))return 2012;
#endif
        if(look_ignored_){if(valid(ids_[1])){clear();if(!call(ids_[1],23))return 2012;}look_ignored_=false;}
        if(move_ignored_){if(valid(ids_[1])){clear();if(!call(ids_[1],7))return 2012;}move_ignored_=false;}
        for(auto& id:characters_){if(id.address && valid(id)){clear();if(!call(id,2))return 2013;}id={};}
        for(auto& id:guides_){if(id.address && valid(id)){clear();if(!call(id,2))return 2013;}id={};}
        for(auto& id:guide_components_)id={};
        for(auto* id:{&camera_,&shot_}){
            if(id->address && valid(*id)){clear();if(!call(*id,2))return 2013;}
            *id={};
        }
        TargetStrongReferenceOps ops{base_,{}};
        const auto result=leases_.close(ops,owner_);
        if(result==StrongLeaseResult::Deferred)return 407;
        if(result!=StrongLeaseResult::Ok)return 2014;
        pool_=false;visual_staging_=false;primary_lease_=0;
#ifdef E33_RETIRED_WORLD_SESSION
        retired_anchor_.reset();retired_cleanup_=false;
#endif
        visual_arena_requested_=false;visual_world_={};visual_arena_binding_={};visual_arena_state_={};
        visual_ground_requested_=false;visual_ground_={};visual_ground_result_=e33_npc_presentation::PreviewPlacementResult::Rejected;
        std::memset(visual_ground_scale_,0,sizeof(visual_ground_scale_));
        visual_ground_candidates_=0;
        for(auto& id:visual_arena_ids_)id={};for(auto& lease:visual_arena_leases_)lease=0;
        for(auto& id:components_)id={};state_=reason==0?4:reason==1?5:6;return 0;
    }
    void poll(){
        if(!pool_)return;
        if(state_==3){if(error_==407)error_=close(reason_);return;}
        if(!TargetPodSchemaOps{base_}.context())return;
#ifdef E33_RETIRED_WORLD_SESSION
        {e33_retired_world::TargetOps epoch{base_};
            if(!epoch.current_binding(retired_anchor_.engine(),retired_anchor_.viewport(),retired_anchor_.world())){
                error_=close(1);return;
            }
        }
#endif
        elapsed_=std::chrono::duration<double>(std::chrono::steady_clock::now()-clock_).count();
        if(!current()){error_=close(1);return;}
        if(preview_active_ && std::chrono::duration<double>(std::chrono::steady_clock::now()-preview_clock_).count()>=preview_limit_ && !stop_preview()){error_=2010;state_=3;return;}
        if(state_==1){if(elapsed_>60.)error_=close(1);return;}
        if(state_==7 || state_==8){
            clear();put(0,ids_[1].address);if(!call(ids_[3],12) || (args_[8] && !photo_mode_)){mouse_valid_=left_down_=false;editor_clock_=std::chrono::steady_clock::now();return;}
            const auto now=std::chrono::steady_clock::now();const double dt=std::clamp(std::chrono::duration<double>(now-editor_clock_).count(),0.,.05);editor_clock_=now;
            bool ok=!photo_mode_ || photo_preview_tick(dt);
            if(state_==8){const double previous=editor_time_,next=std::min(plan_.duration,previous+dt);ok=editor_seek(next,true);for(unsigned i=0;ok && i<32;++i)if(!audio_done_[i] && plan_.audio[i]>=previous && plan_.audio[i]<=next && plan_.audio[i]>=0.){ok=gain(i);if(ok){clear();ok=call(audio_component(i),20);}audio_done_[i]=true;}if(next>=plan_.duration){state_=7;ok=ok && editor_seek(next);}}
            if(!ok || !editor_tick(dt)){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}return;
        }
        if(!visual_staging_ && elapsed_>=plan_.duration){error_=close();return;}
        clear();put(0,ids_[1].address);if(!call(ids_[3],12)){error_=close(1);return;}
        if(args_[8]){if(!visual_staging_)error_=close(1);return;}
        if(!advance(elapsed_)){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
    }
    void command(uint64_t base,MeshPacket& packet,bool conflict){
        const auto op=packet.operation;
        constexpr bool visual_staging_available=
#if E33_RUNTIME_CINEMATIC_VERSION >= 171
            true;
#else
            false;
#endif
        if(packet.version!=7 || op<70 || (op>92 && op!=98 && !(visual_staging_available && op==148)
#if E33_RUNTIME_CINEMATIC_VERSION >= 172
            && op!=149
#endif
#if E33_RUNTIME_CINEMATIC_VERSION >= 174
            && op!=150
#endif
            ) || !packet.owner || packet.error || packet.state){packet.error=2000;return;}
        auto* raw=reinterpret_cast<uint8_t*>(&packet);
#ifdef E33_RETIRED_WORLD_SESSION
        if(pool_ && op!=72 && op!=73){
            e33_retired_world::TargetOps epoch{base_};
            if(!retired_anchor_.established()||!epoch.current_binding(retired_anchor_.engine(),retired_anchor_.viewport(),retired_anchor_.world())){
                packet.error=2052;packet.state=state_;return;
            }
        }
#endif
        if(op==98){
            CallIdentity animation{};std::memcpy(&animation,raw+88,16);uint32_t slot=0;std::memcpy(&slot,raw+104,4);
            Plan candidate{};std::memcpy(&candidate,raw+112,sizeof(candidate));
            bool ok=pool_ && state_==7 && owner_==packet.owner && !conflict && base_==base && current() && slot<24 && candidate.valid() && !std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) &&
                !std::any_of(raw+108,raw+112,[](uint8_t c){return c!=0;}) && !std::any_of(raw+112+sizeof(candidate),raw+sizeof(packet),[](uint8_t c){return c!=0;}) &&
                candidate.count==plan_.count && !std::memcmp(candidate.roles,plan_.roles,sizeof(plan_.roles)) && !std::memcmp(candidate.clips,plan_.clips,sizeof(plan_.clips)) &&
                !std::memcmp(candidate.anchor,plan_.anchor,sizeof(plan_.anchor)) && candidate.anchor_valid==plan_.anchor_valid &&
                slot<unsigned(candidate.extra_count) && candidate.extra[slot][1]>=0. && candidate.extra[slot][2]>=0. &&
                (slot>=unsigned(plan_.extra_count) || plan_.extra[slot][1]<0.);
            for(unsigned i=0;ok && i<24;++i)if(i!=slot && i<unsigned(candidate.extra_count) && candidate.extra[i][1]>=0.)
                ok=i<unsigned(plan_.extra_count) && candidate.extra[i][0]==plan_.extra[i][0] && candidate.extra[i][2]==plan_.extra[i][2];
            if(!ok){packet.error=2045;return;}
            const unsigned actor=unsigned(candidate.extra[slot][0]),clip=unsigned(candidate.extra[slot][2]);
            const auto& profile=scene_clips[clip];
            constexpr FieldProof additive={"AnimSequence","AdditiveAnimType","ByteProperty",328,1,6756568745902593ULL,0x6e10420ULL,0U};
            if(!valid(animation) || !palette_named(animation.address,profile.name,profile.package) || !named(base_,local_read<uint64_t>(animation.address+16),"AnimSequence","/Script/Engine")){packet.error=2045;return;}
            const auto mesh=field(ids_[57+actor*7],mesh_skeleton),anim=field(animation,animation_skeleton),notify=field(animation,notifies),root=field(animation,root_motion),add=field(animation,additive);
            if(!(mesh && anim && notify && root && add && local_read<uint64_t>(mesh) && local_read<uint64_t>(mesh)==local_read<uint64_t>(anim) && local_read<int32_t>(notify+8)==0 && local_read<int32_t>(notify+12)>=0 && !local_read<uint8_t>(root) && !local_read<uint8_t>(add))){packet.error=2045;return;}
            if(!hold(animation)){packet.error=2005;return;}
            ids_[109+slot]=animation;plan_=candidate;
            if(!editor_seek(std::min(editor_time_,plan_.duration))){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;packet.error=error_;}
            packet.state=state_;return;
        }
        if(op==92){
            // Scene camera transfer only: read the owned flight view or apply it
            // to the exact stock photo rig. No reflected property write surface.
            double values[8]{};std::memcpy(values,raw+88,sizeof(values));
            const bool write=values[0]==1.;
            bool ok=pool_ && owner_==packet.owner && !conflict && base_==base && current() && (state_==7 || state_==8) &&
                !std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) && !std::any_of(raw+152,raw+sizeof(packet),[](uint8_t c){return c!=0;}) &&
                (values[0]==0. || write);
            for(unsigned i=1;i<8;++i)ok=ok && std::isfinite(values[i]) && (!write?values[i]==0.:std::abs(values[i])<=(i<=3?1.e8:i<=6?360.:120.));
            if(write)ok=ok && photo_mode_ && values[7]>=20.;
            if(!ok){packet.error=2044;return;}
            if(write){state_=7;ok=photo_snap(values+1);if(ok)ok=photo_read();}
            else if(photo_mode_)ok=photo_read();
            if(!ok){packet.error=2044;return;}
            std::copy(plan_.editor_camera,plan_.editor_camera+6,values+1);values[7]=editor_fov_;
            std::memcpy(raw+88,values,sizeof(values));packet.state=state_;return;
        }
        if(op==91){
            // One exact game-owned entry event, only after our flight owner has
            // released all actors/input. No general Blueprint invocation path.
            if(pool_ || loading_ || owner_!=packet.owner || conflict || !base_ || base_!=base || !TargetPodSchemaOps{base}.context() || !current() ||
               std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+120,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2043;return;}
            CallIdentity gi{},fn{};std::memcpy(&gi,raw+88,16);std::memcpy(&fn,raw+104,16);
            if(!valid(gi) || !valid(fn)){packet.error=2043;return;}
            const auto cls=local_read<uint64_t>(gi.address+16),engine=local_read<uint64_t>(ids_[0].address+32);
            if(!valid(gi) || !valid(fn) || !named(base,cls,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom") ||
               !named(base,local_read<uint64_t>(engine+16),"GameEngine","/Script/Engine") || local_read<uint64_t>(gi.address+32)!=engine ||
               !exact_name(base,fn.address+24,"EnterPhotoMode") || local_read<uint64_t>(fn.address+32)!=cls ||
               !exact_name(base,local_read<uint64_t>(fn.address+16)+24,"Function") || local_read<uint32_t>(fn.address+0xb0)!=209846272U ||
               local_read<uint16_t>(fn.address+0xb6)!=0 || local_read<uint16_t>(fn.address+0xb8)!=65535 || local_read<uint64_t>(fn.address+0xd8)!=base+0x13937a0 ||
               !(named(base,local_read<uint64_t>(ids_[2].address+16),"BP_jRPG_Character_World_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_World") ||
                 named(base,local_read<uint64_t>(ids_[2].address+16),"BP_jRPG_Character_WorldMap_pawn_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_WorldMap_pawn"))){packet.error=2043;return;}
            const auto pe=local_read<uint64_t>(local_read<uint64_t>(gi.address)+0x268);
            if(pe!=base+0x1393330 && pe!=base+0x332bb90){packet.error=2043;return;}
            uint8_t no_parameters[16]{};
            reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(gi.address),reinterpret_cast<void*>(fn.address),no_parameters);
            return;
        }
        if(op==90){
            if(!pool_ || owner_!=packet.owner || !photo_mode_ || !current() || std::any_of(raw+24,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2042;return;}
            constexpr FieldProof opened={"WBP_PhotoModeHUD_C","PhotoModeMenuOpened","BoolProperty",1136,1,2251869606969861ULL,0x6e119b0ULL,0xff010001U};
            const auto at=field(photo_hud_,opened);if(!at){packet.error=2042;return;}
            raw[104]=local_read<uint8_t>(at)?1:0;return;
        }
        if(op==89){
            if(!pool_ || owner_!=packet.owner || !photo_mode_ || !current() || std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+104,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2041;return;}
            CallIdentity help{};std::memcpy(&help,raw+88,16);
            if(!valid(help) || !named(base_,local_read<uint64_t>(help.address+16),"WBP_PhotoModeInputsContainer_C","/Game/UI/Widgets/PhotoMode/WBP_PhotoModeInputsContainer")){packet.error=2041;return;}
            constexpr FieldProof transform={"Widget","RenderTransform","StructProperty",144,56,4503668346847237ULL,0x6e210c0ULL,0U};
            constexpr FieldProof pivot={"Widget","RenderTransformPivot","StructProperty",200,16,6755469234274821ULL,0x6e210c0ULL,0U};
            const auto t=field(help,transform),p=field(help,pivot);if(!t || !p){packet.error=2041;return;}
            auto hud=call_capture(base_,local_read<uint64_t>(local_read<uint64_t>(help.address+32)+32));
            if(!valid(hud) || !named(base_,local_read<uint64_t>(hud.address+16),"WBP_PhotoModeHUD_C","/Game/UI/Widgets/PhotoMode/WBP_PhotoModeHUD") || !hold(hud)){packet.error=2041;return;}
            photo_hud_=hud;
            double values[6]{};std::memcpy(values,reinterpret_cast<const void*>(t),32);std::memcpy(values+4,reinterpret_cast<const void*>(p),16);
            if(!std::all_of(values,values+6,[](double v){return std::isfinite(v) && std::abs(v)<1.e6;})){packet.error=2041;return;}
            std::memcpy(raw+104,values,48);return;
        }
        if(op==88){
            if(!pool_ || owner_!=packet.owner || conflict || (state_!=7 && state_!=8) || !current() || std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+124,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2040;return;}
            CallIdentity widget{},add{};uint32_t flags=0;std::memcpy(&widget,raw+88,16);std::memcpy(&add,raw+104,16);std::memcpy(&flags,raw+120,4);
            if(flags>3 || !valid(widget) || !valid(add) || timeline_widget_.address && (!same(timeline_widget_,widget) || !same(timeline_add_,add))){packet.error=2040;return;}
            timeline_add_=add;
            if(!schema(41) || !call_derives(base_,local_read<uint64_t>(widget.address+16),local_read<uint64_t>(add.address+32))){packet.error=2040;return;}
            if(!timeline_widget_.address && (!hold(widget) || !hold(timeline_add_))){packet.error=2005;return;}
            timeline_widget_=widget;timeline_flags_=flags;return;
        }
        if(op==86 || op==87){
            if(!pool_ || owner_!=packet.owner || conflict || (state_!=1 && state_!=7) || !current() || std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;})){packet.error=2035;return;}
            double value=0.;std::memcpy(&value,raw+88,8);
            if(op==86){
                if(!std::isfinite(value) || std::floor(value)!=value || value<0. || value>=23. || std::any_of(raw+96,raw+sizeof(packet),[](uint8_t c){return c!=0;}) || plan_.audio[9+unsigned(value)]>=0.){packet.error=2038;return;}
                if(!clear_cue(unsigned(value)))packet.error=2010;return;
            }
            if((value!=0. && value!=1.) || std::any_of(raw+160,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2038;return;}
            if(value==0.){if(std::any_of(raw+96,raw+160,[](uint8_t c){return c!=0;})){packet.error=2038;return;}packet.error=music_pause_.close();return;}
            if(music_pause_.active())return;
            CallIdentity system{},audio_class{},audio_default{},pause_fn{};std::memcpy(&system,raw+96,16);std::memcpy(&audio_class,raw+112,16);std::memcpy(&audio_default,raw+128,16);std::memcpy(&pause_fn,raw+144,16);
            MusicAudioReferences refs{};
            if(!music_audio_references(base_,system,audio_class,refs)){packet.error=2039;return;}
            CallPacket pause{};pause.version=1;pause.parameter_size=pause.allocation_extent=1;pause.return_offset=65535;pause.function_flags=0x4020403;pause.entry_rva=0x353bae0;pause.field_count=1;pause.target=audio_default;pause.function=pause_fn;
            auto& f=pause.fields[0];f.kind=CallBool;f.width=f.dimension=1;f.flags=6755469234274944ULL;f.bool_encoding=0xff010001U;std::memcpy(f.name,"bPause",7);f.constraint={-1,0,0};
            packet.error=music_pause_.open(base_,owner_,audio_class,refs,pause);packet.section_id=refs.count;return;
        }
        if(op>=83 && op<=85){
            const size_t end=op==85?88:116;
            if(std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+end,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2000;return;}
            if(!pool_ || owner_!=packet.owner || conflict || (state_!=1 && state_!=7 && (op!=85 || (state_!=2 && state_!=8))) || !TargetPodSchemaOps{base_}.context() || !current()){packet.error=2035;return;}
            if(op==85){if(!stop_preview())packet.error=2010;return;}
            CallIdentity source{};uint32_t slot=0,index=0;std::memcpy(&source,raw+88,16);std::memcpy(&slot,raw+104,4);std::memcpy(&index,raw+108,4);
            uint32_t kind=0;std::memcpy(&kind,raw+112,4);if(!kind)kind=2;
            if(kind<2 || kind>4){packet.error=2036;return;}
            constexpr const char* audio_types[]={"SoundWave","SoundCue","MetaSoundSource"};
            auto& catalog=catalogs_[kind];
            if((op==83?slot>=23:slot!=23) || !catalog.registry_complete_ || index>=catalog.registry_paths_.size() || !valid(source) || !named(base_,local_read<uint64_t>(source.address+16),audio_types[kind-2],kind==4?"/Script/MetasoundEngine":"/Script/Engine")){packet.error=2036;return;}
            const auto& path=catalog.registry_paths_[index];const auto dot=path.rfind('.');
            if(dot==std::string::npos || !palette_named(source.address,path.substr(dot+1).c_str(),path.substr(0,dot).c_str())){packet.error=2036;return;}
            bool ok=true;
            if(op==83){if(plan_.audio[9+slot]>=0. && sounds_[slot].address){packet.error=2037;return;}ok=clear_cue(slot);if(ok)ok=cue_leases_[slot].begin(owner_)==StrongLeaseResult::Ok;if(ok)ok=create_audio(source,sounds_[slot],false,int(slot));}
            else{preview_limit_=kind>=3?15.:5.;ok=stop_preview();if(ok){ok=preview_leases_.begin(owner_)==StrongLeaseResult::Ok;preview_active_=ok;}if(ok)ok=create_audio(source,preview_sound_,true);if(ok){clear();ok=call(preview_sound_,20);preview_clock_=std::chrono::steady_clock::now();}}
            if(!ok){packet.error=2008;const auto e=close(2);if(e)packet.error=e;}return;
        }
        if(op==80){
            if(std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+108,raw+2000,[](uint8_t c){return c!=0;}) || std::any_of(raw+2004,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2000;return;}
            if(conflict || !TargetPodSchemaOps{base}.context()){packet.error=407;return;}
            CallIdentity cls{};std::memcpy(&cls,raw+88,16);uint32_t kind=0;std::memcpy(&kind,raw+104,4);
            constexpr const char* types[]={"SkeletalMesh","AnimSequence","SoundWave","SoundCue","MetaSoundSource"};
            if(kind>4 || !call_identity(base,cls) || !named(base,cls.address,types[kind],kind==4?"/Script/MetasoundEngine":"/Script/Engine") || !catalogs_[kind].registry_page(base,cls,types[kind],raw,kind==4?"/Script/MetasoundEngine":"/Script/Engine"))packet.error=2030;
            return;
        }
        if(op==82){
            if(std::any_of(raw+24,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2000;return;}
            if(owner_!=packet.owner){packet.error=2001;return;}
            if(loading_){TargetStrongReferenceOps ops{base_,{}};if(loading_leases_.close(ops,owner_)!=StrongLeaseResult::Ok){packet.error=407;return;}loading_=false;}
            return;
        }
        if(op==81){
            if(std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+128,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2000;return;}
            if(conflict || !TargetPodSchemaOps{base}.context() || active() && owner_!=packet.owner){packet.error=2001;return;}
            CallIdentity recipient{},function{};std::memcpy(&recipient,raw+88,16);std::memcpy(&function,raw+104,16);
            uint32_t index=0,kind=0;std::memcpy(&index,raw+120,4);std::memcpy(&kind,raw+124,4);
            if(kind>4 || !catalogs_[kind].registry_complete_ || index>=catalogs_[kind].registry_paths_.size() || !call_identity(base,recipient) || !call_identity(base,function)){packet.error=2031;return;}
            const auto fn=function.address,cls=local_read<uint64_t>(fn+32);
            if(!named(base,cls,"KismetSystemLibrary","/Script/Engine") || !exact_name(base,fn+24,"LoadAsset_Blocking") || local_read<uint32_t>(fn+0xb0)!=67249155 || local_read<uint16_t>(fn+0xb6)!=48 || local_read<uint16_t>(fn+0xb8)!=40 || local_read<int32_t>(fn+0x58)!=48 || local_read<uint64_t>(fn+0xd8)!=base+0x3860130 || !call_derives(base,local_read<uint64_t>(recipient.address+16),cls)){packet.error=2032;return;}
            const auto a=local_read<uint64_t>(fn+0x50),r=a?local_read<uint64_t>(a+24):0;
            if(!a || !r || local_read<uint64_t>(r+24) || !exact_name(base,a+32,"Asset") || local_read<uint64_t>(a)!=base+0x6e128d8 || local_read<uint32_t>(a+0x34)!=40 || local_read<uint32_t>(a+0x44) || local_read<uint64_t>(a+0x38)!=7881299347898496ULL || !exact_name(base,r+32,"ReturnValue") || local_read<uint64_t>(r)!=base+0x6e11d38 || local_read<uint32_t>(r+0x44)!=40 || local_read<uint64_t>(r+0x38)!=6755468160534400ULL){packet.error=2033;return;}
            const auto object_class=local_read<uint64_t>(a+0x70);
            if(object_class!=local_read<uint64_t>(r+0x70) || !named(base,object_class,"Object","/Script/CoreUObject")){packet.error=2033;return;}
            const auto pe=local_read<uint64_t>(local_read<uint64_t>(recipient.address)+0x268);
            if(pe!=base+0x1393330 && pe!=base+0x332bb90){packet.error=2033;return;}
            base_=base;owner_=packet.owner;
            if(!loading_){if(loading_leases_.begin(owner_)!=StrongLeaseResult::Ok){packet.error=2005;return;}loading_=true;}
            const auto names=catalogs_[kind].registry_names_.at(catalogs_[kind].registry_paths_[index]);
            clear();put(8,names.first);put(16,names.second);
            reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(recipient.address),reinterpret_cast<void*>(fn),args_);
            auto result=call_capture(base,get<uint64_t>(40));constexpr const char* types[]={"SkeletalMesh","AnimSequence","SoundWave","SoundCue","MetaSoundSource"};uint64_t token=0;
            if(!result.address || !named(base,local_read<uint64_t>(result.address+16),types[kind],kind==4?"/Script/MetasoundEngine":"/Script/Engine")){packet.error=2034;return;}
            TargetStrongReferenceOps ops{base,result};if(loading_leases_.acquire(ops,owner_,result.address,token)!=StrongLeaseResult::Ok || !stabilize_retained_identity(ops,result)){packet.error=2005;return;}
            packet.actor=result;return;
        }
        if(op==74){
            if(pool_ || conflict){packet.error=2001;return;}
            Plan candidate{};std::memcpy(&candidate,raw+88,sizeof(candidate));
            if(std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) ||
               std::any_of(raw+88+sizeof(candidate),raw+sizeof(packet),[](uint8_t c){return c!=0;}) || !candidate.valid()){packet.error=2020;return;}
            plan_=candidate;configured_=true;owner_=packet.owner;return;
        }

        if(op==76){
            Plan candidate{};std::memcpy(&candidate,raw+88,sizeof(candidate));
            if(!pool_ || state_!=7 || owner_!=packet.owner || conflict || !current() || !candidate.valid() || candidate.count!=plan_.count ||
                std::memcmp(candidate.roles,plan_.roles,sizeof(plan_.roles)) || std::any_of(candidate.clips,candidate.clips+6,[&,n=0U](double clip)mutable{const auto i=n++;return clip>=0. && clip!=plan_.clips[i];}) ||
                std::any_of(candidate.extra,candidate.extra+24,[&,n=0U](const auto& row)mutable{const auto i=n++;return i<unsigned(candidate.extra_count) && row[1]>=0. && (row[0]!=plan_.extra[i][0] || row[2]!=plan_.extra[i][2]);}) ||
                std::memcmp(candidate.anchor,plan_.anchor,sizeof(plan_.anchor)) || candidate.anchor_valid!=plan_.anchor_valid ||
                std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) || std::any_of(raw+88+sizeof(candidate),raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2021;return;}
            plan_=candidate;camera_selected_=false;timeline_drag_.select_camera(plan_,editor_time_);
            if(auto* at=timeline_drag_.value(plan_);at && *at<0.){timeline_drag_.kind=timeline_drag_.index=-1;}
            if(timeline_drag_.selected_kind==1){const auto i=timeline_drag_.selected_index;if(i<0 || (i<6?plan_.animation[i]<0.:i>=6+int(plan_.extra_count) || plan_.extra[i-6][1]<0.))timeline_drag_.selected_kind=timeline_drag_.selected_index=-1;}
            if(timeline_drag_.selected_kind==2 && (timeline_drag_.selected_index<0 || plan_.audio[timeline_drag_.selected_index]<0.))timeline_drag_.selected_kind=timeline_drag_.selected_index=-1;
            if(!editor_place() || !editor_seek(std::min(editor_time_,plan_.duration))){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }
#ifdef E33_RETIRED_WORLD_SESSION
        uint32_t retirement_marker=0;std::memcpy(&retirement_marker,raw+24,4);
        const bool request_retired=op==72&&retirement_marker==0x45504f43U;
        if(request_retired){
            if(std::any_of(raw+28,raw+sizeof(packet),[](uint8_t c){return c!=0;}) ||
               (active() && owner_!=packet.owner) || base_!=base){packet.error=2000;return;}
            error_=0;
            if(pool_&&retired_anchor_.established()){e33_retired_world::TargetOps epoch{base_};const auto proof=retired_anchor_.prove(epoch);
                if(proof!=e33_retired_world::Result::Retired)error_=proof==e33_retired_world::Result::Pending?407:2052;
                else retired_cleanup_=true;
            }
            if(!error_)error_=close(1);
            if(error_==407)state_=3;
            packet.error=error_;packet.state=state_;
            packet.section_id=leases_.active()+preview_leases_.active();
            for(const auto&cue:cue_leases_)packet.section_id+=cue.active();
            if(music_pause_.active())packet.sections|=1U<<29;
            return;
        }
#endif
        const bool editor_values=op==77 || op==78 || op==79;
        if(std::any_of(raw+
#ifdef E33_RETIRED_WORLD_SESSION
           (request_retired?28:24)
#else
           24
#endif
           ,raw+88,[](uint8_t c){return c!=0;}) ||
           (op!=76 && std::any_of(raw+(op==70?88+16*inputs:editor_values?104:op==75?136:op==149?168:op==150?248:88),raw+sizeof(packet),[](uint8_t c){return c!=0;}))){packet.error=2000;return;}
        double value=0.,option=0.;if(editor_values){std::memcpy(&value,raw+88,8);std::memcpy(&option,raw+96,8);if(!std::isfinite(value) || !std::isfinite(option)){packet.error=2022;return;}}
        if((op>=75 && op<=79) && (!pool_ || owner_!=packet.owner || conflict || !current() || (op==75?state_!=1:state_!=7 && state_!=8))){packet.error=2022;return;}
        if(pool_ && owner_!=packet.owner){packet.error=2001;return;}
        if(op==70){
            if(pool_ || conflict || !configured_ || owner_!=packet.owner){packet.error=2001;return;}
            base_=base;owner_=packet.owner;error_=0;failed_step_=0;reason_=0;poses_=0;elapsed_=0;animation_at_=audio_at_=-1;timing_={};placed_=false;visual_staging_=false;
            std::fill(std::begin(active_animation_),std::end(active_animation_),-1);std::memset(animation_done_,0,sizeof(animation_done_));std::memset(audio_done_,0,sizeof(audio_done_));std::memset(impact_done_,0,sizeof(impact_done_));std::memset(recoil_done_,0,sizeof(recoil_done_));std::memset(trail_done_,0,sizeof(trail_done_));effect_count_=0;last_hit_=-10.;last_attacker_=0;
            std::memset(material_count_,0,sizeof(material_count_));std::memset(original_materials_,0,sizeof(original_materials_));glowing_=-1;hovered_=-1;snapped_view_=false;editor_fov_=90.;
            std::memcpy(ids_,raw+88,sizeof(ids_));photo_mode_=false;photo_rotation_={};photo_camera_={};photo_tick_={};photo_enable_tick_={};scene_cursor_owned_=false;photo_audition_=-1;
            photo_mode_=named(base_,local_read<uint64_t>(ids_[1].address+16),"BP_PhotoModeController_C","/Game/Gameplay/PhotoMode/BP_PhotoModeController") &&
                named(base_,local_read<uint64_t>(ids_[2].address+16),"BP_PhotoModePawn_C","/Game/Gameplay/PhotoMode/BP_PhotoModePawn");
            if(!TargetPodSchemaOps{base_}.context()){packet.error=407;return;}
            for(const auto& id:ids_)if(!valid(id)){packet.error=2002;return;}
            for(size_t i=0;i<38;++i)if(!schema(i)){packet.error=2003;packet.step=uint32_t(i+1);return;}
            if(!named(base_,ids_[4].address,"CameraActor","/Script/Engine") ||
               !named(base_,ids_[5].address,"SkeletalMeshActor","/Script/Engine") ||
               !named(base_,ids_[6].address,"SkeletalMeshComponent","/Script/Engine") ||
               !named(base_,ids_[100].address,"StaticMeshActor","/Script/Engine") || !named(base_,ids_[101].address,"StaticMeshComponent","/Script/Engine") ||
               !palette_named(ids_[104].address,"M_DebugEmissive1","/Game/LevelTools/FreeAimTargets/M_DebugEmissive1") ||
               !palette_named(ids_[102].address,"Cube","/Engine/BasicShapes/Cube") || !named(base_,local_read<uint64_t>(ids_[102].address+16),"StaticMesh","/Script/Engine") ||
               !named(base_,ids_[11].address,"CameraComponent","/Script/Engine") || !current() || !assets()){packet.error=2004;packet.step=failed_step_;return;}
#ifdef E33_RETIRED_WORLD_SESSION
            {e33_retired_world::TargetOps epoch{base_};e33_retired_world::Snapshot observed{};
                if(!epoch.observe(observed)||!epoch.controller_world(ids_[1],observed.world)){packet.error=2051;return;}}
#endif
            if(leases_.begin(owner_)!=StrongLeaseResult::Ok){packet.error=2005;return;}
            pool_=true;state_=1;clock_=std::chrono::steady_clock::now();
            bool ok=true;for(size_t i=0;i<inputs;++i){
                step_=5000+uint32_t(i);const auto before=ids_[i];
                if(!hold(ids_[i])){ok=false;break;}
                // A successful strong retain may assign an initially-zero weak
                // serial. Refresh only exact aliases of that observed identity.
                // Never accept an arbitrary stale/nonzero serial as a wildcard.
                if(before.serial==0 && ids_[i].serial>0)
                    for(size_t j=i+1;j<inputs;++j)if(same(ids_[j],before))ids_[j]=ids_[i];
            }
#ifdef E33_RETIRED_WORLD_SESSION
            if(ok){e33_retired_world::TargetOps epoch{base_};
                const auto captured=retired_anchor_.capture(epoch,leases_,owner_,ids_[1]);
                if(captured){error_=captured;state_=3;packet.error=captured;packet.state=state_;return;}
            }
#endif
            if(ok){clear();ok=call(ids_[1],6);saved_=call_capture(base_,get<uint64_t>());ok=ok && hold(saved_);}
            if(ok){clear();ok=call(ids_[2],3);std::memcpy(origin_,args_,24);}
            if(ok){clear();ok=call(ids_[2],4);yaw_=get<double>(8);const double rad=yaw_*3.141592653589793/180.;origin_[0]+=std::cos(rad)*300.;origin_[1]+=std::sin(rad)*300.;
                for(auto v:origin_)ok=ok && std::isfinite(v) && std::abs(v)<1.e8;ok=ok && std::isfinite(yaw_);}
            if(ok && plan_.anchor_valid){std::memcpy(origin_,plan_.anchor,24);yaw_=plan_.anchor[3];}
            std::memcpy(plan_.anchor,origin_,24);plan_.anchor[3]=yaw_;plan_.anchor_valid=1.;
            for(unsigned slot=0;ok && slot<unsigned(plan_.count);++slot){
                const auto role=unsigned(plan_.roles[slot]);const unsigned first=slot*6;
                for(unsigned part=0;ok && part<6;++part){
                    const auto& profile_part=scene_parts[role][part];if(!profile_part.name[0])continue;
                    const unsigned i=first+part;ok=spawn(ids_[5],characters_[i]);
                    if(ok){clear();put(0,ids_[6].address);ok=call(characters_[i],15);components_[i]=call_capture(base_,get<uint64_t>(8));ok=ok && hold(components_[i]);}
                    if(ok){clear();put(0,ids_[57+slot*7+part].address);ok=call(components_[i],16);}
                    if(ok){clear();args_[0]=2;ok=call(components_[i],10);}
                    if(ok && (profile_part.mode==1 || profile_part.mode==4)){
                        clear();put(0,components_[first+(profile_part.mode==4?1:0)].address);args_[8]=1;ok=call(components_[i],25);
                    }
                    if(ok && profile_part.mode>=2){
                        const unsigned parent=first+(profile_part.mode==3?0:1);
                        ok=attach(components_[i],components_[parent],profile_part.socket[0]?profile_part.socket:nullptr);
                    }
                    if(ok){
                        clear();std::memcpy(args_,profile_part.quaternion,32);std::memcpy(args_+32,profile_part.position,24);
                        for(unsigned axis=0;axis<3;++axis)put(64+8*axis,profile_part.scale[axis]*(profile_part.mode>=2?1.:plan_.poses[slot][6+axis]));
                        args_[352]=1;ok=call(components_[i],29);
                    }
                }
            }
            if(ok)ok=spawn(ids_[4],camera_);
            if(ok){clear();put(0,ids_[11].address);ok=call(camera_,15);const auto cc=call_capture(base_,get<uint64_t>(8));if(ok){clear();put(0,float(plan_.camera[6]));ok=call(cc,24);}}
            if(ok){clear();put(0,ids_[1].address);put(8,ids_[9].address);put(16,.35f);put(20,1.f);ok=call(ids_[3],19);audio_=call_capture(base_,get<uint64_t>(48));ok=ok && hold(audio_);}
            if(!ok){failed_step_=step_;error_=2006;const auto e=close(2);if(e)error_=e;}
        }
#if E33_RUNTIME_CINEMATIC_VERSION >= 171
        else if(op==148){
            // Reuse the prepared native visual owner without acquiring a view
            // target, input-ignore state, cursor or a timeline widget. Ambient
            // audio/effects are outside this narrowly scoped staging mode.
            if(!pool_ || state_!=1 || photo_mode_ || !current() || conflict ||
               std::any_of(std::begin(plan_.audio),std::end(plan_.audio),[](double at){return at>=0.;}) ||
               std::any_of(std::begin(plan_.impact),std::end(plan_.impact),[](double at){return at>=0.;}) ||
               std::any_of(std::begin(plan_.recoil),std::end(plan_.recoil),[](double at){return at>=0.;}) ||
               std::any_of(std::begin(plan_.trail),std::end(plan_.trail),[](double at){return at>=0.;})){packet.error=2046;return;}
            clear();put(0,ids_[1].address);
            if(!call(ids_[3],12) || args_[8]){packet.error=2046;return;}
            visual_staging_=true;
            if(advance(0.)){state_=9;clock_=std::chrono::steady_clock::now();}
            else{failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }
#endif
#if E33_RUNTIME_CINEMATIC_VERSION >= 172
        else if(op==149){
            // World plus the existing four arena-conversion dependencies.
            if(!pool_ || !visual_staging_ || state_!=9 || conflict || !current() ||
               std::any_of(raw+24,raw+88,[](uint8_t c){return c!=0;}) ||
               std::any_of(raw+168,raw+sizeof(packet),[](uint8_t c){return c!=0;})){packet.error=2047;return;}
            CallIdentity query[5]{};std::memcpy(query,raw+88,sizeof(query));
            error_=bind_visual_parameter_arena(query);
        }
#endif
#if E33_RUNTIME_CINEMATIC_VERSION >= 174
        else if(op==150){
            if(!pool_ || !visual_staging_ || state_!=9 || conflict || !current()){packet.error=2050;return;}
            CallIdentity query[10]{};std::memcpy(query,raw+88,sizeof(query));error_=ground_visual(query);
        }
#endif
        else if(op==71){
            if(photo_mode_){packet.error=2022;return;}
            if(!pool_ || state_!=1 || !current() || conflict){packet.error=2007;return;}
            clear();put(0,ids_[1].address);if(!call(ids_[3],12) || args_[8]){packet.error=2007;return;}
            bool ok=advance(0.);
            if(ok){clear();args_[0]=1;ok=call(ids_[1],7);move_ignored_=ok;}
            if(ok){clear();args_[0]=1;ok=call(ids_[1],23);look_ignored_=ok;}
            if(ok){clear();put(0,camera_.address);view_armed_=true;ok=call(ids_[1],5);}
            if(ok){state_=2;clock_=std::chrono::steady_clock::now();}
            else{failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }else if(op==75){
            if(photo_mode_){
                std::memcpy(&photo_rotation_,raw+88,16);
                std::memcpy(&photo_tick_,raw+104,16);std::memcpy(&photo_enable_tick_,raw+120,16);
                if(!schema(38) || !hold(photo_rotation_) || !schema(39) || !hold(photo_tick_) || !schema(40) || !hold(photo_enable_tick_)){packet.error=2003;return;}
                clear();put(0,ids_[11].address);if(!call(ids_[2],15)){packet.error=2003;return;}
                photo_camera_=call_capture(base_,get<uint64_t>(8));if(!hold(photo_camera_) || !photo_read()){packet.error=2003;return;}
            }else if(std::any_of(raw+88,raw+136,[](uint8_t c){return c!=0;})){packet.error=2022;return;}
            clear();put(0,ids_[1].address);if(!call(ids_[3],12) || (args_[8] && !photo_mode_)){packet.error=2007;return;}
            bool ok=(scene_cursor(false,true) && (!photo_mode_ || photo_mesh_ticks())) && editor_place() && spawn(ids_[4],shot_);
            for(unsigned i=0;ok && i<9;++i){ok=spawn(ids_[100],guides_[i]);if(ok){clear();put(0,ids_[101].address);ok=call(guides_[i],15);guide_components_[i]=call_capture(base_,get<uint64_t>(8));ok=ok && hold(guide_components_[i]);}if(ok){clear();args_[0]=2;ok=call(guide_components_[i],10);}if(ok){clear();put(0,ids_[102].address);ok=call(guide_components_[i],32) && args_[8];if(ok){clear();put(0,0);put(8,ids_[104].address);ok=call(guide_components_[i],33);}}}
            selected_=0;camera_selected_=false;editor_input_=true;mouse_valid_=left_down_=false;timeline_drag_={};
            if(ok && !plan_.camera_valid){const double rad=yaw_*3.141592653589793/180.;plan_.editor_camera[0]=origin_[0]-std::cos(rad)*850.;plan_.editor_camera[1]=origin_[1]-std::sin(rad)*850.;plan_.editor_camera[2]=origin_[2]+240.;plan_.editor_camera[3]=-15.;plan_.editor_camera[4]=yaw_;plan_.editor_camera[5]=0.;plan_.camera_valid=1.;}
            if(ok){clear();put(0,ids_[11].address);ok=call(camera_,15);const auto cc=call_capture(base_,get<uint64_t>(8));if(ok){clear();put(0,90.f);ok=call(cc,24);}}
            // Initialize visible guides before exposing authoring; background focus must not leave default cubes.
            if(ok)ok=pose(camera_,plan_.editor_camera,plan_.editor_camera+3) && editor_seek(0.) && camera_guides();
            if(ok && !photo_mode_){clear();args_[0]=1;ok=call(ids_[1],7);move_ignored_=ok;}
            if(ok && !photo_mode_){clear();args_[0]=1;ok=call(ids_[1],23);look_ignored_=ok;}
            if(ok && !photo_mode_){clear();put(0,camera_.address);view_armed_=true;ok=call(ids_[1],5);}
            if(ok){state_=7;editor_clock_=std::chrono::steady_clock::now();}
            else{failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }else if(op==77){
            state_=7;
            if(value!=std::floor(value) || value<0. || value>=plan_.count || (option!=0. && option!=1.)){packet.error=2022;return;}
            camera_selected_=false;selected_=unsigned(value);bool ok=editor_seek(editor_time_);
            const unsigned event=plan_.active_animation(selected_,editor_time_);
            if(ok && plan_.clip(event)>=0. && option==1.){clear();put(0,animation_id(event).address);args_[8]=uint8_t(plan_.loop(event));ok=call(components_[selected_*6],17);if(ok && photo_mode_){photo_audition_=int(event);photo_audition_slot_=selected_;photo_age_=0.;}}
            if(!ok){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }else if(op==78){
            if(value<0. || value>plan_.duration || option!=0.){packet.error=2022;return;}
            state_=7;if(!editor_seek(value)){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }else if(op==79){
            if(value!=std::floor(value) || value<0. || value>7. || option!=std::floor(option) || option<0. || option>5.){packet.error=2022;return;}
            bool ok=true;
            if(value==0.){state_=7;ok=editor_seek(editor_time_);}
            else if(value==1.){if(editor_time_>=plan_.duration)ok=editor_seek(0.);state_=8;editor_clock_=std::chrono::steady_clock::now();}
            else if(value==5.){if(option>1.){packet.error=2022;return;}
                if(photo_mode_ && editor_input_!=(option==1.)){
                    clear();args_[0]=uint8_t(option==0.);ok=call(ids_[1],7);if(ok)move_ignored_=option==0.;
                    if(ok){clear();args_[0]=uint8_t(option==0.);ok=call(ids_[1],23);if(ok)look_ignored_=option==0.;}
                }if(ok)ok=scene_cursor(option==0.);editor_input_=option==1.;mouse_valid_=left_down_=false;grab_depth_=0.;timeline_drag_.cancel();}
            else if(value==6. || value==7.){
                if(option!=0.){packet.error=2022;return;}
                state_=7;ok=editor_seek(editor_time_);mouse_valid_=left_down_=false;grab_depth_=0.;timeline_drag_.cancel();
                if(ok && value==6.){double view[7]{};plan_.camera_world(editor_time_,view);std::copy(view,view+6,plan_.editor_camera);snapped_view_=true;ok=(photo_mode_?photo_snap(view):editor_fov(view[6]) && pose(camera_,view,view+3)) && highlight(-1) && camera_guides();}
                else if(ok){if(photo_mode_ && !photo_read()){packet.error=2008;return;}const int index=plan_.capture_editor_camera(editor_time_,editor_fov_);if(index<0){packet.error=2022;return;}timeline_drag_.camera_selected=index;camera_selected_=true;editor_time_=plan_.keys[index][0];ok=editor_seek(editor_time_) && camera_guides();}
            }
            else if(option>=plan_.count){packet.error=2022;return;}
            else{camera_selected_=false;selected_=unsigned(option);auto& v=plan_.poses[selected_];const double rad=yaw_*3.141592653589793/180.,f[]={std::cos(rad),std::sin(rad)},r[]={-f[1],f[0]};auto& c=plan_.editor_camera;
                if(value==2.){c[0]=origin_[0]+f[0]*(v[0]-300.)+r[0]*v[1];c[1]=origin_[1]+f[1]*(v[0]-300.)+r[1]*v[1];c[2]=origin_[2]+v[2]+140.;c[3]=-10.;c[4]=yaw_;c[5]=0.;}
                else if(value==3.){const double x=c[0]+std::cos(c[4]*3.141592653589793/180.)*300.-origin_[0],y=c[1]+std::sin(c[4]*3.141592653589793/180.)*300.-origin_[1];v[0]=std::clamp(x*f[0]+y*f[1],-5000.,5000.);v[1]=std::clamp(x*r[0]+y*r[1],-5000.,5000.);v[2]=std::clamp(c[2]-140.-origin_[2],-5000.,5000.);ok=editor_place();}
            }
            if(!ok){failed_step_=step_;error_=2008;const auto e=close(2);if(e)error_=e;}
        }else if(op==72){error_=close(1);}
        else if(op!=76)poll();
        packet.error=error_;packet.state=state_;packet.actor=visual_staging_?characters_[0]:camera_;packet.component=components_[0];
        packet.position[0]=elapsed_;packet.position[1]=animation_at_;packet.position[2]=audio_at_;
        packet.step=failed_step_?failed_step_:step_;packet.sections=(timing_.animation?1U:0U)|(timing_.audio?2U:0U)|(poses_?4U:0U)|(timing_.audio_count<<8)|(effect_count_<<16);
        packet.sections|=(uint32_t(timeline_drag_.camera_selected+1)&31U)<<24;
        if(music_pause_.active())packet.sections|=1U<<29;
        if(camera_selected_)packet.sections|=1U<<30;
        DWORD focus_pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&focus_pid);
        if(focus_pid==GetCurrentProcessId() && (GetAsyncKeyState(VK_RMENU)&0x8000))packet.sections|=1U<<31;
        packet.section_id=leases_.active()+preview_leases_.active();for(const auto& cue:cue_leases_)packet.section_id+=cue.active();packet.reserved=poses_;
        if(state_==7 || state_==8){packet.position[0]=editor_time_;packet.position[1]=double(timeline_drag_.selected_kind*100+timeline_drag_.selected_index);packet.position[2]=double(selected_);std::memcpy(raw+88,&plan_,sizeof(plan_));}
        if(op==150)ground_snapshot(raw+4096);
    }
};
}
#pragma warning(pop)
