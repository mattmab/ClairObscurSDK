#pragma once
#include "editor_flight_math.h"

// The menu keeps its existing input/cursor ownership. Keyboard movement is
// independent of RMB look; the owned value field blocks movement while typing.
// This borrows only a positively owned source camera, never the gameplay camera.
static bool timeline_viewport_camera_proof(uint64_t,const CallIdentity&,const CallIdentity&);
class SequenceFlightOwner {
    CallPacket move_{},status_{},text_focus_{};
    bool input_bound_=false;
    bool external_=false;CallPacket cuts_{};
    CallIdentity external_camera_{},external_player_{};
    CallPacket source_camera_{},camera_owner_{};
    bool bound_=false;
    double pose_[6]{};
    double sampled_=0;
    e33_editor_flight::TickGate tick_gate_;
    static double seconds(){
        static const double frequency=[](){LARGE_INTEGER f{};QueryPerformanceFrequency(&f);return double(f.QuadPart);}();
        LARGE_INTEGER now{};QueryPerformanceCounter(&now);return double(now.QuadPart)/frequency;
    }
    POINT pointer_{};
    bool active_=false,dragging_=false;
    double nudge_[3]{};
    ULONGLONG input_sampled_=0;
    bool back_down_=false,toggle_ui_=false;
    static bool named(uint64_t base,const CallPacket& p,const char* owner,const char* name,const char* package){
        const auto fn=call_identity(base,p.function),cls=fn?local_read<uint64_t>(fn+32):0;
        return fn && call_is_class(base,cls) && exact_name(base,fn+24,name) && exact_name(base,cls+24,owner) &&
            exact_name(base,local_read<uint64_t>(cls+32)+24,package);
    }
public:
    void reset(){*this=SequenceFlightOwner{};}
    bool due(){return tick_gate_.due(seconds());}
    bool external()const{return external_;}
    uint32_t external_view(uint64_t base,const CallPacket& cuts,const CallIdentity& camera,const CallIdentity& player){
        if(active_ || !timeline_viewport_camera_proof(base,player,camera))return 1791;
        cuts_=cuts;external_camera_=camera;external_player_=player;external_=true;return 0;
    }
    uint32_t release_external(uint64_t base){
        if(!external_)return 0;
        auto cuts=cuts_;cuts.data[0]=0;
        if(reflected_call(base,cuts) || cuts.outcome!=CallDispatchReturned)return 1793;
        external_=false;return 0;
    }
    uint32_t bind_input(uint64_t base,const CallPacket& field,const CallIdentity& root){
        if(active_ || !named(base,field,"Widget","HasKeyboardFocus","/Script/UMG") ||
           field.parameter_size!=1 || field.allocation_extent!=1 || field.return_offset || field.field_count!=1 || field.object_count ||
           field.fields[0].kind!=CallBool || field.fields[0].offset || field.fields[0].width!=1)return 1791;
        auto object=call_identity(base,field.target);
        if(!object || !exact_name(base,local_read<uint64_t>(object+16)+24,"EditableText"))return 1791;
        auto outer=object;bool owned=false;
        for(unsigned i=0;outer && i<16;++i,outer=local_read<uint64_t>(outer+32)){if(outer==root.address){owned=true;break;}}
        auto check=field;if(!owned || reflected_call(base,check,nullptr,nullptr,nullptr,nullptr,true))return 1791;
        text_focus_=field;input_bound_=true;return 0;
    }
    void sample_input(bool eligible){
        const auto now=GetTickCount64();const double dt=input_sampled_?std::min(.05,double(now-input_sampled_)/1000.):0.;input_sampled_=now;
        DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);
        const auto down=[](int key){return (GetAsyncKeyState(key)&0x8000)!=0;};
        const bool foreground=eligible && pid==GetCurrentProcessId();
        const bool back=foreground && down(VK_BACK);
        if(back && !back_down_ && !down(VK_CONTROL) && !down(VK_MENU))toggle_ui_=!toggle_ui_;
        back_down_=back;
        if(!foreground || !active_)return;
        const double step=150.*dt*(down(VK_MENU)?.1:1.);
        const double angle=pose_[4]*3.14159265358979323846/180.;
        const double forward=double(down(VK_NUMPAD8))-double(down(VK_NUMPAD2));
        const double side=double(down(VK_NUMPAD6))-double(down(VK_NUMPAD4));
        nudge_[0]+=step*(forward*std::cos(angle)-side*std::sin(angle));
        nudge_[1]+=step*(forward*std::sin(angle)+side*std::cos(angle));
        nudge_[2]+=step*(double(down(VK_NUMPAD9))-double(down(VK_NUMPAD3)));
        for(auto& value:nudge_)value=std::clamp(value,-10000.,10000.);
    }
    void drain_input(uint32_t& toggle,double* delta){
        toggle=toggle_ui_?1:0;toggle_ui_=false;
        std::memcpy(delta,nudge_,sizeof(nudge_));std::fill(std::begin(nudge_),std::end(nudge_),0.);
    }
    uint32_t bind(uint64_t base,const CallPacket& source,const CallPacket& owner,const CallIdentity& player){
        if(active_ || std::memcmp(&source.target,&player,sizeof(player)) ||
           !named(base,source,"LevelSequencePlayer","GetActiveCameraComponent","/Script/LevelSequence") ||
           !named(base,owner,"ActorComponent","GetOwner","/Script/Engine"))return 1791;
        for(const auto* p:{&source,&owner}){
            if(p->parameter_size!=8 || p->allocation_extent!=8 || p->return_offset || p->field_count!=1 || p->object_count ||
               p->fields[0].kind!=CallObject || p->fields[0].offset || p->fields[0].width!=8 ||
               std::strcmp(p->fields[0].name,"ReturnValue"))return 1791;
            auto check=*p;if(reflected_call(base,check,nullptr,nullptr,nullptr,nullptr,true))return 1791;
        }
        source_camera_=source;camera_owner_=owner;bound_=true;return 0;
    }
    bool current_camera(uint64_t base,const CallIdentity& camera)const{
        if(external_)return !std::memcmp(&camera,&external_camera_,sizeof(camera)) && timeline_viewport_camera_proof(base,external_player_,camera);
        if(!bound_ || !call_identity(base,camera) || !(local_read<uint32_t>(camera.address+8)&0x40))return false;
        auto source=source_camera_,owner=camera_owner_;
        if(reflected_call(base,source) || source.outcome!=CallDispatchReturned || source.object_count!=1 ||
           std::memcmp(&source.objects[0].identity,&owner.target,sizeof(CallIdentity)))return false;
        if(reflected_call(base,owner) || owner.outcome!=CallDispatchReturned || owner.object_count!=1 ||
           std::memcmp(&owner.objects[0].identity,&camera,sizeof(CallIdentity)))return false;
        return true;
    }
    bool active()const{return active_;}
    uint32_t restore_pose(uint64_t base,const CallPodValidation* pod){
        if(!active_ || !current_camera(base,move_.target))return 1791;
        auto move=move_;std::memcpy(move.data,pose_,sizeof(pose_));
        return reflected_call(base,move,nullptr,pod) || move.outcome!=CallDispatchReturned || !move.data[48]?1793:0;
    }
    const CallIdentity& camera()const{return move_.target;}
    void cancel(){active_=dragging_=false;sampled_=0;std::fill(std::begin(nudge_),std::end(nudge_),0.);}
    void pose(double* destination)const{std::memcpy(destination,pose_,sizeof(pose_));}
    uint32_t prepare(uint64_t base,const CallPacket& move,const CallPacket& status,const CallIdentity& player,const CallPodValidation* pod){
        if(active_ || !pod || !current_camera(base,move.target) || std::memcmp(&status.target,&player,sizeof(player)) ||
           !named(base,move,"Actor","K2_TeleportTo","/Script/Engine") ||
           !named(base,status,"MovieSceneSequencePlayer","IsPlaying","/Script/MovieScene") ||
           move.parameter_size!=49 || move.allocation_extent!=56 || move.return_offset!=48 || move.field_count!=3 || move.object_count ||
           status.parameter_size!=1 || status.return_offset || status.field_count!=1 || status.object_count ||
           move.fields[0].kind!=CallVector || move.fields[0].offset || move.fields[0].width!=24 ||
           move.fields[1].kind!=CallRotator || move.fields[1].offset!=24 || move.fields[1].width!=24 ||
           move.fields[2].kind!=CallBool || move.fields[2].offset!=48 || move.fields[2].width!=1 ||
           status.fields[0].kind!=CallBool || status.fields[0].offset || status.fields[0].width!=1)return 1791;
        auto a=move,b=status;
        if(reflected_call(base,a,nullptr,pod,nullptr,nullptr,true) || reflected_call(base,b,nullptr,nullptr,nullptr,nullptr,true))return 1791;
        // Query first; no camera dispatch is performed during admission.
        if(reflected_call(base,b) || b.outcome!=CallDispatchReturned)return b.outcome==CallNotDispatched?1791:1793;
        if(b.data[0])return 1791;
        move_=move;status_=status;std::memcpy(pose_,move.data,sizeof(pose_));
        for(double v:pose_)if(!std::isfinite(v))return 1791;
        sampled_=seconds();tick_gate_={};dragging_=false;active_=true;return 0;
    }
    uint32_t tick(uint64_t base,const CallPodValidation* pod,bool eligible){
        if(!active_)return 0;
        const auto now=seconds();const double dt=std::min(.05,now-sampled_);sampled_=now;
        DWORD pid=0;const auto window=GetForegroundWindow();GetWindowThreadProcessId(window,&pid);
        POINT point{};RECT area{};
        const bool foreground=eligible && pid==GetCurrentProcessId() &&
            GetCursorPos(&point) && ScreenToClient(window,&point) && GetClientRect(window,&area) &&
            point.x>=0 && point.y>=0 && point.x<area.right && point.y<area.bottom;
        if(!foreground){dragging_=false;return 0;}
        const auto down=[](int key){return (GetAsyncKeyState(key)&0x8000)!=0;};
        e33_editor_flight::Input input;
        const bool look=(GetAsyncKeyState(VK_RBUTTON)&0x8000)!=0;
        input.dx=look && dragging_?double(point.x-pointer_.x)/8.:0.;input.dy=look && dragging_?double(pointer_.y-point.y)/8.:0.;
        pointer_=point;dragging_=look;
        input.forward=double(down('W'))-double(down('S'));input.side=double(down('D'))-double(down('A'));
        input.up=double(down('E')||down(VK_SPACE))-double(down('Q')||down(VK_CONTROL));input.fast=down(VK_SHIFT);
        if(!e33_editor_flight::moving(input))return 0;
        if(input_bound_){auto focus=text_focus_;if(reflected_call(base,focus) || focus.outcome!=CallDispatchReturned)return 1791;
            if(focus.data[0]){dragging_=false;return 0;}
        }else if(!look)return 0;
        auto query=status_;
        if(reflected_call(base,query) || query.outcome!=CallDispatchReturned)return query.outcome==CallNotDispatched?1791:1793;
        if(query.data[0] && !external_){cancel();return 0;}
        if(!current_camera(base,move_.target))return 1791;
        e33_editor_flight::advance(pose_,dt,input);
        auto move=move_;std::memcpy(move.data,pose_,sizeof(pose_));
        if(reflected_call(base,move,nullptr,pod) || move.outcome!=CallDispatchReturned || !move.data[48])return 1793;
        return 0;
    }
};
