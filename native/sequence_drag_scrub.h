#pragma once
#include "target_sequence_seek.h"

#include "sequence_drag_protocol.h"

// Borrowed exclusively from this sequence's retained menu tree and scope.
// Never queues pointer positions: each game-thread pass evaluates the newest
// Slate value. Closing or retiring the sequence cancels this before release.
class SequenceDragScrub {
    CallPacket getter_{},pause_{};
    SequenceDragConfig config_{};
    SequenceDragStatus status_{};
    bool bound_=false,held_=false,paused_=false,continuous_=false;
    float previous_=0;
#if E33_RUNTIME_CINEMATIC_VERSION>=258
    SequenceViewportStatus viewport_{};
    POINT pressed_{};bool pick_armed_=false,remap_=false,timeline_drag_=false;
    static bool pointer(POINT& point,RECT& area){
        DWORD pid=0;const auto window=GetForegroundWindow();GetWindowThreadProcessId(window,&pid);
        return pid==GetCurrentProcessId() && GetCursorPos(&point) && ScreenToClient(window,&point) &&
            GetClientRect(window,&area) && area.right>0 && area.bottom>0;
    }
    static bool inside(const POINT& point,const RECT& area){
        return point.x>=area.right*.08 && point.x<=area.right*.92 && point.y>=area.bottom*
#if E33_RUNTIME_CINEMATIC_VERSION>=259
            .75 && point.y<=area.bottom*.95
#else
            .85 && point.y<=area.bottom*.94
#endif
            ;
    }
#endif
    static bool zero(const void* p,size_t n){auto b=static_cast<const uint8_t*>(p);for(size_t i=0;i<n;++i)if(b[i])return false;return true;}
public:
    void reset(){*this=SequenceDragScrub{};}
    bool active()const{return bound_;}
    bool continuous()const{return continuous_;}
    const SequenceDragStatus& status()const{return status_;}
#if E33_RUNTIME_CINEMATIC_VERSION>=258
    const SequenceViewportStatus& viewport()const{return viewport_;}
    void pointer_message(MSG* message,bool eligible){
        if(!bound_ || !eligible || !message)return;
        const auto kind=message->message;
        if(kind!=WM_MOUSEWHEEL && kind!=WM_MBUTTONDOWN && kind!=WM_LBUTTONDOWN && kind!=WM_LBUTTONUP && kind!=WM_MOUSEMOVE)return;
        POINT point{};RECT area{};if(!pointer(point,area))return;
        DWORD pid=0;GetWindowThreadProcessId(message->hwnd,&pid);if(pid!=GetCurrentProcessId())return;
        point.x=static_cast<short>(LOWORD(message->lParam));point.y=static_cast<short>(HIWORD(message->lParam));
        if(kind==WM_MOUSEWHEEL && !ScreenToClient(GetForegroundWindow(),&point))return;
#if E33_RUNTIME_CINEMATIC_VERSION>=259
        const double py=double(point.y)/area.bottom;
        const bool row_hover=inside(point,area) && sequence_timeline_lane(py)>=0;
        const float fraction=static_cast<float>(std::clamp((double(point.x)/area.right-.08)/.84,0.,1.));
        std::memcpy(&viewport_.reserved[0],&fraction,4);
        viewport_.reserved[1]=row_hover?static_cast<uint32_t>(sequence_timeline_lane(py)):0;
        viewport_.reserved[2]=row_hover?1:0;++viewport_.reserved[3];
#endif
        if(kind==WM_LBUTTONDOWN){pick_armed_=inside(point,area)
#if E33_RUNTIME_CINEMATIC_VERSION>=259
            && sequence_timeline_lane(py)>=0
#endif
            ;pressed_=point;return;}
        if(kind==WM_MOUSEMOVE){
            if(pick_armed_ && (std::abs(point.x-pressed_.x)>5 || std::abs(point.y-pressed_.y)>5))pick_armed_=false;
            return;
        }
        if(kind==WM_LBUTTONUP){
            if(pick_armed_ && inside(point,area) && std::abs(point.x-pressed_.x)<=5 && std::abs(point.y-pressed_.y)<=5){
                const double y=double(point.y)/area.bottom;
#if E33_RUNTIME_CINEMATIC_VERSION>=259
                const auto lane=sequence_timeline_lane(y);if(lane<0){pick_armed_=false;return;}
                viewport_.lane=static_cast<uint32_t>(lane);
#else
                viewport_.lane=y<.88?0:y<.905?1:2;
#endif
                viewport_.pick_frame=viewport_.start+std::clamp((double(point.x)/area.right-.08)/.84,0.,1.)*(viewport_.end-viewport_.start);
                ++viewport_.pick_counter;
            }
            pick_armed_=false;return;
        }
        if(!inside(point,area))return;
        if(held_)return;
        if(message->message==WM_MBUTTONDOWN){viewport_.start=config_.start;viewport_.end=config_.end;}
        else{
            const double steps=static_cast<short>(HIWORD(message->wParam))/120.;
            if(!sequence_viewport_zoom(config_.start,config_.end,(double(point.x)/area.right-.08)/.84,steps,
                                       (LOWORD(message->wParam)&MK_SHIFT)!=0,viewport_.start,viewport_.end))return;
        }
        ++viewport_.revision;remap_=true;message->message=WM_NULL;
    }
#endif
    uint32_t bind(uint64_t base,const CallIdentity& root,const CallIdentity& player,const CallIdentity& actor,
                  const CallPacket& getter,const SequenceDragConfig& config){
        if(bound_ || config.magic!=0x44533345 || config.version!=1 || config.end<=config.start ||
           !zero(config.reserved,sizeof(config.reserved)) || getter.version!=1 || getter.parameter_size!=4 ||
           getter.allocation_extent!=4 || getter.return_offset || getter.field_count!=1 || getter.object_count ||
           getter.fields[0].kind!=CallFloat || getter.fields[0].offset || getter.fields[0].width!=4 ||
           getter.fields[0].dimension!=1 || std::strcmp(getter.fields[0].name,"ReturnValue"))return 1811;
        const auto object=call_identity(base,getter.target),fn=call_identity(base,getter.function);
        if(!object || !fn || !exact_name(base,local_read<uint64_t>(object+16)+24,"Slider") ||
           !exact_name(base,fn+24,"GetValue"))return 1811;
        auto cls=local_read<uint64_t>(fn+32);
        if(!call_is_class(base,cls) || !exact_name(base,cls+24,"Slider") ||
           !exact_name(base,local_read<uint64_t>(cls+32)+24,"/Script/UMG"))return 1811;
        bool owned=false;auto outer=object;
        for(unsigned i=0;outer && i<16;++i,outer=local_read<uint64_t>(outer+32))if(outer==root.address){owned=true;break;}
        auto query=getter;
        if(!owned || reflected_call(base,query,nullptr,nullptr,nullptr,nullptr,true))return 1811;
        SequenceSeekPacket seek{};seek.magic=0x53533345;seek.version=1;seek.function=config.seek;seek.frame=config.start;
        TargetSequenceSeekOps ops{{base}};
        if(!sequence_seek_target(ops,player,actor,seek) ||
           config.start!=local_read<int32_t>(player.address+0x298) ||
           int64_t(config.end)!=int64_t(config.start)+local_read<int32_t>(player.address+0x29c))return 1811;
        const auto pause_fn=call_identity(base,config.pause);
        const auto owner=pause_fn?local_read<uint64_t>(pause_fn+32):0;
        if(!pause_fn || !call_is_class(base,owner) || !exact_name(base,pause_fn+24,"Pause") ||
           !exact_name(base,owner+24,"MovieSceneSequencePlayer") ||
           !exact_name(base,local_read<uint64_t>(owner+32)+24,"/Script/MovieScene"))return 1811;
        CallPacket pause{};pause.version=1;pause.return_offset=0xffff;pause.target=player;pause.function=config.pause;
        pause.function_flags=local_read<uint32_t>(pause_fn+0xb0);
        const auto entry=local_read<uint64_t>(pause_fn+0xd8);
        if(entry<base || entry-base>=166776832)return 1811;
        pause.entry_rva=static_cast<uint32_t>(entry-base);
        if(reflected_call(base,pause,nullptr,nullptr,nullptr,nullptr,true))return 1811;
        if(reflected_call(base,query) || query.outcome!=CallDispatchReturned)return 1813;
        std::memcpy(&previous_,query.data,4);
        if(!std::isfinite(previous_) || previous_<0 || previous_>1)return 1811;
        getter_=getter;pause_=pause;config_=config;
        status_={};status_.magic=0x44533345;status_.version=1;status_.value=previous_;
#if E33_RUNTIME_CINEMATIC_VERSION>=258
        viewport_={};viewport_.magic=0x56533345;viewport_.version=
#if E33_RUNTIME_CINEMATIC_VERSION>=259
            2;
#else
            1;
#endif
        viewport_.start=config.start;viewport_.end=config.end;
        pick_armed_=remap_=false;
#endif
        bound_=true;held_=paused_=false;return 0;
    }
    bool candidate(uint64_t base,bool eligible,SequenceSeekPacket& seek,uint32_t& error){
        error=0;if(!bound_)return false;
        DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);
        const bool down=eligible && pid==GetCurrentProcessId() && (GetAsyncKeyState(VK_LBUTTON)&0x8000)!=0;
#if E33_RUNTIME_CINEMATIC_VERSION>=258
        POINT point{};RECT area{};const bool located=pointer(point,area);
        if(down && !held_)timeline_drag_=located && inside(point,area)
#if E33_RUNTIME_CINEMATIC_VERSION>=259
            && sequence_timeline_ruler(double(point.y)/area.bottom)
#endif
            ;
#endif
        const bool final=held_ && !down;
        held_=down;status_.dragging=down?1:0;
        if(!down && !final){paused_=false;return false;}
#if E33_RUNTIME_CINEMATIC_VERSION>=258
        if(!timeline_drag_)return false;
#endif
        auto query=getter_;
        if(reflected_call(base,query) || query.outcome!=CallDispatchReturned){error=1813;return false;}
        float value{};std::memcpy(&value,query.data,4);
        if(!std::isfinite(value) || value<0 || value>1){error=1813;return false;}
        if(std::abs(value-previous_)<=.000001f
#if E33_RUNTIME_CINEMATIC_VERSION>=258
           && !remap_
#endif
        )return false;
        previous_=value;
        continuous_=paused_;
        if(!paused_){auto pause=pause_;if(reflected_call(base,pause) || pause.outcome!=CallDispatchReturned){error=1813;return false;}paused_=true;}
        seek={};seek.magic=0x53533345;seek.version=1;seek.function=config_.seek;
#if E33_RUNTIME_CINEMATIC_VERSION>=258
        const double cursor=viewport_.start+double(value)*(viewport_.end-viewport_.start);
        seek.frame=static_cast<int32_t>(std::floor(std::min(cursor,double(config_.end)-1.)));
        seek.subframe=cursor>=config_.end?0.f:static_cast<float>(cursor-std::floor(cursor));
        if(seek.subframe>=1.f){++seek.frame;seek.subframe=0;}
        remap_=false;
#else
        if(!sequence_drag_position(config_,value,seek.frame,seek.subframe)){error=1813;return false;}
#endif
        return true;
    }
    void applied(const SequenceSeekPacket& seek){
        ++status_.counter;status_.frame=seek.frame;status_.subframe=seek.subframe;status_.value=previous_;
    }
};
