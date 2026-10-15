#pragma once
#pragma warning(push)
#pragma warning(disable:4324)
#include <filesystem>
#include <chrono>
#include "builder_profile.h"
#include "target_owned_text.h"
#include "../gpu/bridge.h"
#include "gpu_properties.h"
namespace e33_builder {
// Only fixed reflected Engine functions, dispatched on the SDK game thread.
// No pointer supplied by Python is used without a live slot/serial check.
class Owner {
    CallIdentity ids_[128]{},camera_{},target_{},selected_{},hover_{},hover_actor_{},selected_actor_{};
    bool schemas_[64]{},dragging_=false,left_was_=true,nudging_=false;
    bool auto_tick_=true,want_grab_=false,carrying_=false;
    unsigned highlight_mode_=1;
    bool duplicate_click_=false,duplicate_requested_=false;
    double mouse_sensitivity_=1.25,fly_speed_=1600.;
    uint64_t last_frame_=0,last_clock_=0,last_hover_=0,last_hud_=0,ticks_=0;
    double tick_ms_sum_=0,cost_ms_sum_=0,max_cost_ms_=0;
    uint32_t tick_error_=0;
    double ray_error_=0;
    std::string label_;
    OwnedTextStorage text_;
    uint64_t owner_=0,token_=0;
    CallIdentity menu_widget_{};
    bool active_=false,ignored_=false,frozen_=false;
    uint8_t mode_=0,custom_=0;
    double position_[3]{},rotation_[3]{},original_rotation_[3]{},offset_[3]{},depth_=0;
    struct Edit {CallIdentity component;uint8_t mobility;std::array<uint8_t,96> transform;CallIdentity created_actor{},asset{},actor_class{};};
    std::vector<Edit> edits_,undo_,redo_;
    struct HistoryEvent {uint64_t revision;CallIdentity before,actor,component;};
    std::vector<HistoryEvent> history_events_;
    unsigned history_request_=0;
    uint32_t undo_revision_=0;
    alignas(16) uint8_t args_[512]{};
    uint32_t step_=0;
    void clear(){std::memset(args_,0,sizeof(args_));}
    template<class T> void put(size_t at,const T& value){std::memcpy(args_+at,&value,sizeof(T));}
    template<class T> T get(size_t at=0){T v{};std::memcpy(&v,args_+at,sizeof(T));return v;}
    bool call(uint64_t b,CallIdentity recipient,size_t i) {
        step_=uint32_t(i+1);
        if(i>=64 || !TargetPodSchemaOps{b}.context())return false;
        const auto fn=call_identity(b,ids_[i>=56?96+i-56:(i>=41?64+i-41:(i==40?62:8+i))]);const auto& p=profiles[i];
        if(i==46)step_=4701;if(!fn)return false;
        if(i==46)step_=4702;
        if(!schemas_[i] && (!exact_name(b,local_read<uint64_t>(fn+16)+24,"Function") ||
           !exact_name(b,fn+24,p.name) || !named(b,local_read<uint64_t>(fn+32),p.owner,packages[i]) ||
           local_read<uint32_t>(fn+0xb0)!=p.flags || local_read<uint16_t>(fn+0xb6)!=p.params ||
           local_read<uint16_t>(fn+0xb8)!=p.returned || local_read<int32_t>(fn+0x58)!=int(p.extent) ||
           local_read<uint64_t>(fn+0xd8)!=b+p.entry || !fields(b,fn,p.fields,p.count)))return false;
        schemas_[i]=true;
        if(i==46)step_=4703;
        const auto o=call_identity(b,recipient);
        if(!o || !call_derives(b,local_read<uint64_t>(o+16),local_read<uint64_t>(fn+32)))return false;
        if(i==46)step_=4704;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(o)+0x268);
        if(pe!=b+0x1393330 && pe!=b+0x332bb90)return false;
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(o),reinterpret_cast<void*>(fn),args_);
        if(i==46)step_=4705;
        return true;
    }
    bool byte_property(uint64_t b,CallIdentity obj,const char* owner,const char* name,uint8_t& value) {
        const auto o=call_identity(b,obj);if(!o)return false;
        auto cls=local_read<uint64_t>(o+16);
        for(int n=0;cls&&n<64;++n,cls=local_read<uint64_t>(cls+0x40)) {
            if(!named(b,cls,owner,"/Script/Engine"))continue;
            auto f=local_read<uint64_t>(cls+0x50);
            for(int j=0;f&&j<512;++j,f=local_read<uint64_t>(f+24)) {
                if(!exact_name(b,f+32,name))continue;
                const auto at=local_read<int32_t>(f+0x44);
                if(local_read<uint64_t>(f+16)!=(cls|1) || !exact_name(b,local_read<uint64_t>(f+8),"ByteProperty") ||
                   local_read<int32_t>(f+0x30)!=1 || local_read<int32_t>(f+0x34)!=1 || at<0 || at>=local_read<int32_t>(cls+0x58))return false;
                value=local_read<uint8_t>(o+at);return true;
            }
        }
        return false;
    }
    bool current(uint64_t b) {
        clear();return call(b,ids_[0],21) && get<uint64_t>()==call_identity(b,ids_[1]) && call_identity(b,ids_[1]);
    }
    bool camera_pose(uint64_t b) {
        clear();std::memcpy(args_,position_,24);std::memcpy(args_+24,rotation_,24);args_[304]=1;
        return call(b,camera_,5)&&args_[305];
    }
    bool component_pose(uint64_t b,CallIdentity component,const uint8_t* pose) {
        clear();std::memcpy(args_,pose,96);args_[352]=1;return call(b,component,20);
    }
    bool restore_edits(uint64_t b) {
        while(!edits_.empty()) {
            const auto& e=edits_.back();
            if(call_identity(b,e.component)) {
                if(!component_pose(b,e.component,e.transform.data()))return false;
                clear();args_[0]=e.mobility;if(!call(b,e.component,16))return false;
            }
            edits_.pop_back();
        }
        selected_={};selected_actor_={};undo_.clear();redo_.clear();dragging_=false;return true;
    }
    #include "builder_selection.h"
    #include "builder_gpu.h"
    #include "builder_registry.h"
    bool pick(uint64_t b,bool select=true) {
        if(select){selected_={};selected_actor_={};}
        hover_={};hover_actor_={};
        clear();if(!call(b,ids_[0],32))return false;
        const auto width=get<int32_t>(),height=get<int32_t>(4);if(width<=0||height<=0)return true;
        clear();put(0,float(width)*.5f);put(4,float(height)*.5f);
        if(!call(b,ids_[0],40))return false;if(!args_[56])return true;
        double origin[3],dir[3],end[3];std::memcpy(origin,args_+8,24);std::memcpy(dir,args_+32,24);
        double length=0;for(int j=0;j<3;++j){if(!std::isfinite(origin[j])||!std::isfinite(dir[j]))return false;length+=dir[j]*dir[j];}
        if(length<.99||length>1.01)return false;
        for(int j=0;j<3;++j)end[j]=origin[j]+dir[j]*200000.;
        // Round-trip the ray through the actual viewport projection for diagnostics.
        double point[3];for(int j=0;j<3;++j)point[j]=origin[j]+dir[j]*1000.;
        clear();std::memcpy(args_,point,24);
        if(!call(b,ids_[0],24)||!args_[41])return false;
        ray_error_=std::hypot(get<double>(24)-width*.5,get<double>(32)-height*.5);
        if(!std::isfinite(ray_error_)||ray_error_>2.)return false;
        std::vector<uint64_t> ignored{ids_[1].address,camera_.address};
        CallIdentity actor{},component{};double distance=200000.;
        for(int pass=0;pass<16;++pass) {
            clear();put(0,ids_[0].address);std::memcpy(args_+8,origin,24);std::memcpy(args_+32,end,24);args_[57]=1;
            const Array a{ignored.data(),int32_t(ignored.size()),int32_t(ignored.size())};put(64,a);args_[336]=1;
            if(!call(b,ids_[5],14))return false;
            if(!args_[376])break;
            uint8_t hit[248];std::memcpy(hit,args_+88,248);clear();std::memcpy(args_,hit,248);
            if(!call(b,ids_[4],15))return false;
            distance=get<float>(256);
            if(!std::isfinite(distance)||distance<0)return true;
            actor=call_capture(b,get<uint64_t>(368));component=call_capture(b,get<uint64_t>(376));
            if(ambient(b,actor,component)) {
                ignored.push_back(actor.address);actor={};component={};distance=200000.;continue;
            }
            if(!ordinary(b,actor,component)){actor={};component={};}
            break;
        }
        // Collision is only an occlusion cap for unsupported world geometry.
        // Editable props must pass the rendered-surface test, even with collision.
        if(component.address)distance=200000.;actor={};component={};
        if(!gpu_pick(b,origin,dir,actor,component,distance))return false;
        if(!actor.address||!component.address)return true;
        hover_=component;hover_actor_=actor;
        if(!select)return true;
        if(!checkpoint(b,component))return false;
        auto it=std::find_if(edits_.begin(),edits_.end(),[&](const Edit& e){return e.component.address==component.address&&e.component.serial==component.serial;});
        if(it==edits_.end()) {
            if(edits_.size()>=scene_limit_)return false;
            Edit e{};e.component=component;
            if(!byte_property(b,component,"SceneComponent","Mobility",e.mobility)||e.mobility>2)return false;
            clear();if(!call(b,component,19))return false;std::memcpy(e.transform.data(),args_,96);edits_.push_back(e);
        }
        clear();args_[0]=2;if(!call(b,component,16))return false;
        clear();if(!call(b,component,19))return false;
        depth_=std::max(50.,double(distance));
        const double rad=3.141592653589793/180.,cp=std::cos(rotation_[0]*rad),sp=std::sin(rotation_[0]*rad),cy=std::cos(rotation_[1]*rad),sy=std::sin(rotation_[1]*rad);
        const double carryDir[]={cp*cy,cp*sy,sp};
        for(int j=0;j<3;++j)offset_[j]=get<double>(32+8*j)-position_[j]-carryDir[j]*depth_;
        selected_=component;selected_actor_=actor;return true;
    }
    bool move(uint64_t b,const double* v) {
                const double rad=3.141592653589793/180.,cp=std::cos(rotation_[0]*rad),sp=std::sin(rotation_[0]*rad),cy=std::cos(rotation_[1]*rad),sy=std::sin(rotation_[1]*rad);
                const double dir[]={cp*cy,cp*sy,sp};
                position_[0]+=v[0]*dir[0]-v[1]*sy;position_[1]+=v[0]*dir[1]+v[1]*cy;position_[2]+=v[0]*dir[2]+v[2];
                if(!camera_pose(b)){return false;}
                if(selected_.address&&(v[3]||v[4]||v[5]||v[6]||v[7])) {
                    clear();if(!call(b,selected_,19)){selected_={};return false;}
                    uint8_t pose[96];std::memcpy(pose,args_,96);double loc[3];std::memcpy(loc,pose+32,24);
                    if(v[3])for(int j=0;j<3;++j)loc[j]=position_[j]+dir[j]*depth_+offset_[j];
                    const double delta[]={v[4]*cy-v[5]*sy,v[4]*sy+v[5]*cy,v[6]};
                    for(int j=0;j<3;++j){loc[j]+=delta[j];offset_[j]+=delta[j];}std::memcpy(pose+32,loc,24);
                    if(v[7]) {double q[4];std::memcpy(q,pose,32);const auto s=std::sin(v[7]*rad/2),c=std::cos(v[7]*rad/2);const double rotated[]={c*q[0]-s*q[1],c*q[1]+s*q[0],c*q[2]+s*q[3],c*q[3]-s*q[2]};std::memcpy(pose,rotated,32);}
                    if(!component_pose(b,selected_,pose)){return false;}
                    refresh_candidate(b,selected_);
                }
        return true;
    }
#include "builder_feedback.h"
#include "builder_scene.h"
#include "builder_bulk.h"
#include "builder_carry.h"
#include "builder_preview.h"
#include "builder_booth.h"
public:
    bool preview_active()const{return booth_active_;}
    bool owns_menu(const CallIdentity& widget)const {
        return active_ && menu_widget_.address && menu_widget_.address==widget.address &&
            menu_widget_.index==widget.index && menu_widget_.serial==widget.serial;
    }
    bool active()const{return active_;}
    void request_history(bool redo){if(active_&&!booth_active_)history_request_=redo?2:1;}
    uint32_t step()const{return step_;}
    template<class Pool> uint32_t stop(uint64_t b,uint64_t session,Pool& pool,bool restore) {
        if(!TargetPodSchemaOps{b}.context())return 407;
        dragging_=false;carrying_=false;duplicate_requested_=false;nudging_=false;
        if(!booth_end(b,session,pool))return 1940;
        if(!preview_stop(b,session,pool)||!thumbnail_clear(b,session,pool))return 1934;
        if(!gpu_stop(b,session,pool))return 1920;
        if(!glow(b,session,pool,{}))return 1913;
        if(ids_[48].address && call_identity(b,ids_[48])){clear();if(!call(b,ids_[48],30))return 1910;}
        TargetOwnedTextOps text_ops{b};if(release_owned_text(text_ops,text_)!=OwnedTextResult::Ok)return 1910;
        if(restore&&(!restore_edits(b)||!clear_spawned(b,session,pool)))return 1908;
        if(active_ && call_identity(b,ids_[0])) {
            clear();put(0,call_identity(b,target_)?target_.address:call_identity(b,ids_[1]));
            if(!call(b,ids_[0],6))return 1909;
            clear();std::memcpy(args_,original_rotation_,24);if(!call(b,ids_[0],23))return 1909;
        }
        if(ignored_&&call_identity(b,ids_[0])) {clear();if(!call(b,ids_[0],9))return 1909;}ignored_=false;
        if(frozen_&&call_identity(b,ids_[2])) {clear();args_[0]=mode_;args_[1]=custom_;if(!call(b,ids_[2],10))return 1909;}frozen_=false;
        if(call_identity(b,camera_)){clear();if(!call(b,camera_,2))return 1909;}
        camera_={};active_=false;selected_={};
        if(token_) {TargetStrongReferenceOps ops{b,{-1,0,0}};auto e=pool.release(ops,session,token_);if(e!=StrongLeaseResult::Ok)return uint32_t(e);token_=0;}
        if(restore)owner_=0;
        return 0;
    }
    template<class Pool> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& packet) {
        auto raw=reinterpret_cast<uint8_t*>(&packet);
        const auto op=packet.operation;
        if(packet.version!=3||op<20||op>61||!packet.owner||packet.error||packet.state||!TargetPodSchemaOps{b}.context()){packet.error=1900;return;}
        if(owner_&&owner_!=packet.owner){packet.error=1901;return;}
        if(op==45) {
            CallIdentity widget{};std::memcpy(&widget,raw+88,sizeof(widget));
            if(!active_ || !call_identity(b,widget) || !exact_name(b,local_read<uint64_t>(widget.address+16)+24,"CommonActivatableWidget")) {packet.error=1902;return;}
            menu_widget_=widget;
        } else if(op==20) {
            if(active_||camera_.address||token_){packet.error=1901;return;}
            candidates_.clear();scan_index_=0;
            owner_=packet.owner;std::memcpy(ids_,raw+88,sizeof(ids_));std::fill(std::begin(schemas_),std::end(schemas_),false);
            tick_error_=0;ticks_=0;tick_ms_sum_=cost_ms_sum_=max_cost_ms_=0;label_.clear();last_frame_=last_clock_=last_hover_=last_hud_=0;left_was_=true;dragging_=false;carrying_=false;duplicate_requested_=false;auto_tick_=true;
            for(int j=0;j<8;++j)if(!call_identity(b,ids_[j])){packet.error=1902;return;}
            if(!named(b,ids_[6].address,"CameraActor","/Script/Engine")||!call_is_class(b,ids_[6].address)||!current(b)){packet.error=1902;return;}
            clear();if(!call(b,ids_[1],11)||!args_[0]){packet.error=1902;return;}
            clear();if(!call(b,ids_[2],18)||get<uint64_t>()!=ids_[1].address){packet.error=1902;return;}
            if(!byte_property(b,ids_[2],"CharacterMovementComponent","MovementMode",mode_)||mode_>6||
               !byte_property(b,ids_[2],"CharacterMovementComponent","CustomMovementMode",custom_)){packet.error=1902;return;}
            clear();if(!call(b,ids_[0],7)){packet.error=1902;return;}target_=call_capture(b,get<uint64_t>());
            clear();if(!call(b,ids_[0],8)){packet.error=1902;return;}std::memcpy(original_rotation_,args_,24);
            clear();if(!call(b,ids_[3],12)){packet.error=1902;return;}std::memcpy(position_,args_,24);
            clear();if(!call(b,ids_[3],13)){packet.error=1902;return;}std::memcpy(rotation_,args_,24);rotation_[0]=std::clamp(std::remainder(rotation_[0],360.),-89.,89.);
            clear();put(0,ids_[0].address);put(8,ids_[6].address);transform(args_+16,position_);args_[112]=1;
            if(!call(b,ids_[4],0)){packet.error=1903;return;}camera_=call_capture(b,get<uint64_t>(136));
            if(!camera_.address){packet.error=1903;return;}
            TargetStrongReferenceOps ops{b,camera_};auto lease=pool.acquire(ops,session,camera_.address,token_);
            if(lease!=StrongLeaseResult::Ok){packet.error=uint32_t(lease);return;}
            clear();put(0,camera_.address);transform(args_+16,position_);if(!call(b,ids_[4],1)||!camera_pose(b)){packet.error=1903;return;}
            clear();if(!call(b,ids_[2],10)){packet.error=1903;return;}frozen_=true;
            clear();args_[0]=1;if(!call(b,ids_[0],9)){packet.error=1903;return;}ignored_=true;
            clear();std::memcpy(args_,rotation_,24);if(!call(b,ids_[0],23)){packet.error=1903;return;}
            if(!gpu_setup(b,session,pool)){packet.error=1920;return;}
            // Mark camera ownership before switching view so failure cleanup restores it.
            active_=true;clear();put(0,camera_.address);put(8,0.2f);
            if(!call(b,ids_[0],6)){packet.error=1903;return;}
        } else if(op==22 || op==25) {
            packet.error=op==22?stop(b,session,pool,false):((restore_edits(b)&&clear_spawned(b,session,pool))?0:1908);
            if(op==25&&!active_&&!packet.error)owner_=0;
        } else if(op==27) {
            if(!undo(b,session,pool))packet.error=1911;
        } else if(op==28) {
            auto_tick_=packet.section_id!=0;last_clock_=0;
        } else if(op==29||op==51) {
            uint32_t offset=0;if(op==51)std::memcpy(&offset,raw+2000,4);
            if(!export_scene(b,raw,offset))packet.error=1930;
        } else if(op==50) {
            if(!active_||!current(b)||!bulk_spawn(b,session,pool,raw))packet.error=1950;
        } else if(op==52) {
            double settings[8];std::memcpy(settings,raw+2000,64);
            if(!active_||!current(b)||!gallery_begin(b,session,pool,settings))packet.error=1955;
            std::memcpy(raw+3568,&gallery_floor_,16);std::memcpy(raw+3584,&gallery_floor_component_,16);
        } else if(op==57||op==58) {
            CallIdentity source{},actor{},component{};std::memcpy(&source,raw+88,16);
            if(!active_||booth_active_||carrying_||!current(b)){packet.error=1963;return;}
            if(op==57){if(!duplicate_hand(b,session,pool,source,actor,component))packet.error=1964;}
            else if(!carry_owned(b,source))packet.error=1964;
            std::memcpy(raw+3568,&actor,16);std::memcpy(raw+3584,&component,16);
        } else if(op==61) {
            if(!active_||booth_active_||carrying_||!current(b)||!redo(b,session,pool))packet.error=1965;
        } else if(op==60) {
            const auto count=uint32_t(history_events_.size());std::memcpy(raw+3560,&count,4);
            for(size_t i=0;i<history_events_.size();++i)std::memcpy(raw+4096+56*i,&history_events_[i],56);
        } else if(op==59) {
            duplicate_requested_=false;want_grab_=false;
        } else if(op==56) {
            double v[8];std::memcpy(v,raw+2000,64);
            if(!active_||!std::isfinite(v[0])||v[0]<.05||v[0]>10.||!std::isfinite(v[1])||v[1]<100.||v[1]>10000.||(v[2]!=0.&&v[2]!=1.&&v[2]!=2.)||(v[3]!=0.&&v[3]!=1.)||v[4]||v[5]||v[6]||v[7]){packet.error=1962;return;}
            if(!glow(b,session,pool,{})){packet.error=1913;return;}
            mouse_sensitivity_=v[0];fly_speed_=v[1];highlight_mode_=unsigned(v[2]);duplicate_click_=v[3]!=0.;duplicate_requested_=false;
        } else if(op==55) {
            if(!active_||booth_active_||!current(b)){packet.error=1958;return;}
            clear();std::memcpy(args_,position_,24);put(32,rotation_[1]);
            if(!call(b,ids_[1],63)||!args_[48])packet.error=1959;
            else {std::memcpy(original_rotation_,rotation_,24);packet.error=stop(b,session,pool,false);}
        } else if(op==54) {
            if(!active_||!current(b)||!gallery_existing(b,raw))packet.error=1957;
        } else if(op==53) {
            if(!bulk_delete(b,session,pool,raw))packet.error=1956;
        } else if(op==30||op==31) {
            if(!active_||!current(b)){packet.error=1904;return;}
            CallIdentity object{},cls{};std::memcpy(&object,raw+88,16);std::memcpy(&cls,raw+104,16);
            if(op==30){if(!apply_pose(b,object,raw+2000))packet.error=1931;}
            else {CallIdentity actor{},component{};const auto before=spawned_.size();if(!spawn_asset(b,session,pool,object,cls,raw+2000,actor,component)){const auto failedStep=step_;packet.error=1932;if(spawned_.size()>before){const auto failedActor=spawned_.back().actor;if(!clear_spawned(b,session,pool,failedActor))packet.error=1933;}step_=failedStep;}std::memcpy(raw+3568,&actor,16);std::memcpy(raw+3584,&component,16);}
        } else if(op==40) {
            CallIdentity actor{};std::memcpy(&actor,raw+88,16);
            if(!active_||!booth_begin(b,session,pool,actor))packet.error=1940;
        } else if(op==41) {
            if(!booth_end(b,session,pool))packet.error=1941;
        } else if(op==42) {
            double v[8];std::memcpy(v,raw+2000,64);
            for(auto x:v)if(!std::isfinite(x)||std::abs(x)>1.e7){packet.error=1900;return;}
            if(!active_||booth_active_){packet.error=1942;return;}
            std::memcpy(position_,v,24);std::memcpy(rotation_,v+3,24);
            clear();std::memcpy(args_,rotation_,24);if(!call(b,ids_[0],23)||!camera_pose(b))packet.error=1942;
        } else if(op==43) {
            if(!map_capture(b,session,pool))packet.error=1943;
        } else if(op==44) {
            double v[8];std::memcpy(v,raw+2000,64);
            for(auto x:v)if(!std::isfinite(x)||std::abs(x)>10000){packet.error=1900;return;}
            if(!booth_active_||!booth_motion(b,v[0],v[1],v[2],v[3],v[4],v[5],v[6]!=0))packet.error=1944;
        } else if(op==37) {
            if(!thumbnail_export(b,raw))packet.error=1936;
        } else if(op==38) {
            CallIdentity image{};if(!thumbnail_import(b,session,pool,raw,image))packet.error=1937;std::memcpy(raw+3568,&image,16);
        } else if(op==39) {
            if(!thumbnail_clear(b,session,pool))packet.error=1938;
        } else if(op==36) {
            if(!preview_stop(b,session,pool))packet.error=1934;
        } else if(op==35) {
            if(!active_||!registry_page(b,raw))packet.error=1935;
        } else if(op==48||op==49) {
            uint32_t ready=0;
            if(!active_)packet.error=1948;
            else if(op==48){if(!image_begin(b,raw,ready))packet.error=1948;}
            else {image_tick(b);ready=image_result_;if(image_error_)packet.error=image_error_;}
            std::memcpy(raw+3576,&image_max_ms_,8);
            std::memcpy(raw+3560,&ready,4);const auto format=image_bridge_.observed_format();std::memcpy(raw+3564,&format,4);
        } else if(op==47) {
            if(!active_||!registry_complete_){packet.error=1947;return;}
            const auto* path=reinterpret_cast<const char*>(raw+2000);size_t length=0;
            while(length<512&&path[length])++length;
            if(!length||length>=512){packet.error=1947;return;}
            const auto it=registry_names_.find(std::string(path,length));
            if(it==registry_names_.end()){packet.error=1947;return;}
            std::string package,asset;
            if((it->second.first>>32)||(it->second.second>>32)||!registry_name(b,it->second.first,package)||!registry_name(b,it->second.second,asset)||package+"."+asset!=it->first){packet.error=1947;return;}
            const uint32_t names[]={uint32_t(it->second.first),uint32_t(it->second.second)};std::memcpy(raw+3568,names,8);
        } else if(op==46) {
            CallIdentity mesh{};std::memcpy(&mesh,raw+88,16);
            if(!active_||!current(b)||!thumbnail_mesh(b,session,pool,mesh))packet.error=1946;
        } else if(op==34) {
            CallIdentity actor{},imageTarget{};std::memcpy(&actor,raw+88,16);
            if(!active_||!preview(b,session,pool,actor,imageTarget))packet.error=1934;
            std::memcpy(raw+3568,&imageTarget,16);
        } else if(op==32||op==33) {
            CallIdentity only{};if(op==33)std::memcpy(&only,raw+88,16);
            if(!clear_spawned(b,session,pool,only))packet.error=1933;
        } else if(op==26) {
            // Read-only owner status.
        } else {
            if(!active_||!current(b)){packet.error=1904;return;}
            if(op==23){if(!pick(b))packet.error=1905;}
            if(op==21 || op==24) {
                double v[8];std::memcpy(v,raw+2000,sizeof(v));
                for(auto value:v)if(!std::isfinite(value)||std::abs(value)>10000){packet.error=1900;return;}
                if(!move(b,v))packet.error=1906;
            }
        }
        packet.state=active_?1:0;
        const double stats[]={double(ticks_),ticks_?tick_ms_sum_/ticks_:0.,ticks_?cost_ms_sum_/ticks_:0.,max_cost_ms_,double(tick_error_),double(undo_.size()),double(hover_.index),double(dragging_)};
        std::memcpy(raw+3000,stats,sizeof(stats));
        std::memcpy(raw+3064,&ray_error_,8);
        const double gpuStats[]={double(gpu_completed_),double(gpu_pending_),double(gpu_error_?gpu_error_:gpu_bridge_.error())};std::memcpy(raw+3072,gpuStats,24);
        uint64_t gpuDiag[12];gpu_bridge_.diagnostics(gpuDiag);std::memcpy(raw+3400,gpuDiag,96);
        const double gpuProof[]={gpu_last_depth_,gpu_last_latency_,double(gpu_surface_hits_),double(gpu_ready_component_.index),double(gpu_candidates_.size()),double(gpu_next_)};std::memcpy(raw+3496,gpuProof,48);
        const uint32_t gpuReady=gpu_bridge_.ready()?1:0;std::memcpy(raw+3096,&gpuReady,4);
        std::memcpy(raw+3356,rotation_,24);const uint32_t carryFlag=carrying_?1:0;std::memcpy(raw+3380,&carryFlag,4);const uint32_t requestFlag=duplicate_requested_?1:0;std::memcpy(raw+3384,&requestFlag,4);std::memcpy(raw+3388,&undo_revision_,4);
        const auto text=label_.substr(0,255);std::memcpy(raw+3100,text.c_str(),text.size()+1);
        const double boothStats[]={booth_active_?1.:0.,booth_distance_,booth_rotation_[0],booth_rotation_[1],booth_rotation_[2],double(booth_lighting_)};std::memcpy(raw+3600,boothStats,sizeof(boothStats));
        packet.actor=camera_;packet.component=selected_;packet.step=step_;packet.sections=uint32_t(edits_.size());std::memcpy(packet.position,position_,24);
    }
};
}

#pragma warning(pop)

