    bool checkpoint(uint64_t b,CallIdentity component) {
        clear();if(!call(b,component,19))return false;
        Edit e{};e.component=component;std::memcpy(e.transform.data(),args_,96);
        if(undo_.size()>=64)undo_.erase(undo_.begin());
        undo_.push_back(e);return true;
    }
    bool undo(uint64_t b) {
        dragging_=false;nudging_=false;left_was_=true;
        while(!undo_.empty()) {
            const auto e=undo_.back();
            if(call_identity(b,e.component)) {
                if(!component_pose(b,e.component,e.transform.data()))return false;
                refresh_candidate(b,e.component);undo_.pop_back();return true;
            }
            undo_.pop_back();
        }
        return true;
    }
    std::string object_name(uint64_t b,CallIdentity component) {
        auto o=call_identity(b,component);if(!o)return "";
        auto cls=local_read<uint64_t>(o+16);
        if(named(b,cls,"StaticMeshComponent","/Script/Engine")) {
            auto f=local_read<uint64_t>(cls+0x50);
            for(int i=0;f&&i<512;++i,f=local_read<uint64_t>(f+24)) {
                if(!exact_name(b,f+32,"StaticMesh"))continue;
                const auto at=local_read<int32_t>(f+0x44);
                if(local_read<uint64_t>(f+16)!=(cls|1)||!exact_name(b,local_read<uint64_t>(f+8),"ObjectProperty")||
                   local_read<int32_t>(f+0x34)!=8||local_read<int32_t>(f+0x30)!=1||at<0||at+8>local_read<int32_t>(cls+0x58))break;
                const auto mesh=call_capture(b,local_read<uint64_t>(o+at));
                char name[64]{};
                if(mesh.address&&skin_name(b,local_read<uint64_t>(mesh.address+24),name))return std::string(name)+" #"+std::to_string(component.index);
            }
        }
        return "World prop #"+std::to_string(component.index);
    }
    bool label(uint64_t b,const std::string& value) {
        if(label_==value)return true;
        TargetOwnedTextOps ops{b};
        if(release_owned_text(ops,text_)!=OwnedTextResult::Ok)return false;
        std::wstring wide(value.begin(),value.end());
        if(create_owned_text(ops,text_,reinterpret_cast<const uint16_t*>(wide.c_str()),uint32_t(wide.size()+1))!=OwnedTextResult::Ok)return false;
        clear();put(0,text_.value);if(!call(b,ids_[49],29))return false;
        if(release_owned_text(ops,text_)!=OwnedTextResult::Ok)return false;
        label_=value;return true;
    }
    bool visibility(uint64_t b,CallIdentity widget,bool visible) {
        clear();args_[0]=visible?3:1; // ESlateVisibility: HitTestInvisible / Collapsed.
        return call(b,widget,28);
    }
    bool feedback(uint64_t b) {
        if(!ids_[48].address)return true;
        const auto component=dragging_?selected_:hover_;
        const auto actor=dragging_?selected_actor_:hover_actor_;
        const bool valid=call_identity(b,component)&&call_identity(b,actor);
        const std::string name=valid?object_name(b,component):std::string();
        if(!label(b,valid?(dragging_?"MOVING: ":"AIM: ")+name+(dragging_?"  |  Release to place":"  |  Hold LMB to grab"):
            "WORLD BUILDER  |  Aim at a prop  |  Alt+Z undo"))return false;
        const float color[]={dragging_?0.1f:1.f,dragging_?0.95f:0.8f,dragging_?1.f:0.15f,1.f};
        for(int j=0;j<2;++j){clear();const float white[]={1,1,1,.95f};std::memcpy(args_,valid?color:white,16);if(!call(b,ids_[60+j],33))return false;}
        for(int j=0;j<4;++j)if(!visibility(b,ids_[54+j],false))return false;
        return true;
    }
public:
    template<class Pool> void poll(uint64_t b,uint64_t session,Pool& pool,bool eligible) {
        if(!active_||!TargetPodSchemaOps{b}.context())return;
        const auto frame=local_read<uint64_t>(b+0x9272d10);
        if(!frame||frame==last_frame_)return;last_frame_=frame;
        image_tick(b);
        if(!auto_tick_||tick_error_)return;
        const auto now=GetTickCount64();const auto elapsed=last_clock_?now-last_clock_:0;last_clock_=now;
        DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);
        if(!eligible||pid!=GetCurrentProcessId()) {
            dragging_=false;nudging_=false;left_was_=true;
            glow(b,session,pool,{});if(ids_[48].address)visibility(b,ids_[48],false);
            return;
        }
        clear();put(0,ids_[0].address);
        if(!call(b,ids_[4],34)){tick_error_=1912;return;}
        if(args_[8]) {dragging_=false;left_was_=true;glow(b,session,pool,{});if(ids_[48].address)visibility(b,ids_[48],false);return;}
        LARGE_INTEGER begin{},end{},frequency{};QueryPerformanceCounter(&begin);QueryPerformanceFrequency(&frequency);
        // Escape is edge-triggered and consumed by the native message router.
        // Polling its held state here would close the next layer on another frame.
        auto key=[](int k){return (GetAsyncKeyState(k)&0x8000)!=0;};
        if(booth_active_){
            const double dt=std::min(.05,double(elapsed)*.001);
            clear();if(!call(b,ids_[0],8)){tick_error_=1944;return;}
            const double pitch=get<double>(),yaw=get<double>(8);
            const bool lamp=key('L');
            if(!booth_motion(b,std::remainder(yaw-rotation_[1],360.),std::remainder(pitch-rotation_[0],360.),(int(key('S'))-int(key('W')))*dt,
                (int(key(VK_NUMPAD8))-int(key(VK_NUMPAD2)))*60*dt,(int(key(VK_NUMPAD7))-int(key(VK_NUMPAD1)))*60*dt,(int(key(VK_NUMPAD9))-int(key(VK_NUMPAD3)))*60*dt,lamp&&!booth_lamp_was_))tick_error_=1944;
            booth_lamp_was_=lamp;return;
        }
        if(!current(b)){tick_error_=1904;stop(b,session,pool,false);return;}
        scan_candidates(b);
        const bool undo_pressed=key(VK_MENU)&&key('Z');
        if(undo_pressed&&!undo_was_){if(!undo(b))tick_error_=1911;}
        undo_was_=undo_pressed;
        const bool left=key(VK_LBUTTON);
        const double dt=std::min(.05,double(elapsed)*.001);
        const double forward=int(key('W'))-int(key('S')),right=int(key('D'))-int(key('A'));
        const double up=int(key(VK_SPACE)||key('E'))-int(key(VK_CONTROL)||key('Q'));
        const double speed=1600.*dt*(key(VK_SHIFT)?4.:1.)/std::max(1.,std::sqrt(forward*forward+right*right+up*up));
        const double fine=150.*dt*(key(VK_MENU)?.1:1.);
        double v[]={forward*speed,right*speed,up*speed,0,
            (int(key(VK_NUMPAD8))-int(key(VK_NUMPAD2)))*fine,
            (int(key(VK_NUMPAD6))-int(key(VK_NUMPAD4)))*fine,
            (int(key(VK_NUMPAD9))-int(key(VK_NUMPAD3)))*fine,
            (int(key(VK_NUMPAD7))-int(key(VK_NUMPAD1)))*fine*.1};
        if(undo_pressed)std::fill(std::begin(v),std::end(v),0.);
        // Sample view before ray selection; hovering never changes mobility or history.
        clear();if(!call(b,ids_[0],8)){tick_error_=1906;return;}std::memcpy(rotation_,args_,24);
        if(left&&(!left_was_||want_grab_)&&!undo_pressed) {if(!pick(b))tick_error_=1905;dragging_=selected_.address!=0;want_grab_=!dragging_;}
        if(!left){dragging_=false;want_grab_=false;}left_was_=left;
        const bool nudge=v[4]||v[5]||v[6]||v[7];
        if(nudge&&!nudging_&&!dragging_&&selected_.address)if(!checkpoint(b,selected_))tick_error_=1911;
        nudging_=nudge;v[3]=dragging_?1.:0.;
        if(!tick_error_&&!move(b,v))tick_error_=1906;
        if(!dragging_){last_hover_=now;if(!pick(b,false))tick_error_=1905;}
        if(true) {
            last_hud_=now;
            if(!glow(b,session,pool,dragging_?selected_:hover_))tick_error_=1913;
            if(ids_[48].address&&(!visibility(b,ids_[48],true)||!feedback(b)))tick_error_=1910;
        }
        QueryPerformanceCounter(&end);const double cost=double(end.QuadPart-begin.QuadPart)*1000./double(frequency.QuadPart);
        ++ticks_;tick_ms_sum_+=double(elapsed);cost_ms_sum_+=cost;max_cost_ms_=std::max(max_cost_ms_,cost);
        if(tick_error_)stop(b,session,pool,false);
    }
private:
