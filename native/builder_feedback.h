    bool checkpoint(uint64_t b,CallIdentity component) {
        clear();if(!call(b,component,19))return false;
        Edit e{};e.component=component;std::memcpy(e.transform.data(),args_,96);
        if(undo_.size()>=64)undo_.erase(undo_.begin());
        redo_.clear();undo_.push_back(e);return true;
    }
    void history_event(CallIdentity before,CallIdentity actor={},CallIdentity component={}) {
        if(history_events_.size()>=64)history_events_.erase(history_events_.begin());
        history_events_.push_back({++undo_revision_,before,actor,component});
    }
    static bool same_history_identity(CallIdentity a,CallIdentity b) {
        return a.index==b.index&&a.serial==b.serial&&a.address==b.address;
    }
    template<class Pool> bool retain_history_asset(uint64_t b,uint64_t session,Pool& pool,CallIdentity identity) {
        if(!identity.address)return true;
        if(!call_identity(b,identity))return false;
        if(std::any_of(history_assets_.begin(),history_assets_.end(),[&](const auto& row){return same_history_identity(row.identity,identity);}))return true;
        uint64_t lease=0;TargetStrongReferenceOps ops{b,identity};
        if(pool.acquire(ops,session,identity.address,lease)!=StrongLeaseResult::Ok)return false;
        history_assets_.push_back({identity,lease});return true;
    }
    template<class Pool> bool prune_history_assets(uint64_t b,uint64_t session,Pool& pool) {
        for(size_t i=history_assets_.size();i>0;--i) {
            const auto& row=history_assets_[i-1];bool used=false;
            for(const auto* stack:{&undo_,&redo_})for(const auto& edit:*stack)
                if(same_history_identity(edit.asset,row.identity)||same_history_identity(edit.actor_class,row.identity))used=true;
            if(used)continue;
            TargetStrongReferenceOps ops{b,{-1,0,0}};
            if(pool.release(ops,session,row.lease)!=StrongLeaseResult::Ok)return false;
            history_assets_.erase(history_assets_.begin()+i-1);
        }
        return true;
    }
    void remap_history(const Edit& old,CallIdentity actor,CallIdentity component) {
        for(auto* stack:{&undo_,&redo_})for(auto& edit:*stack) {
            if(same_history_identity(edit.component,old.component))edit.component=component;
            if(same_history_identity(edit.created_actor,old.created_actor))edit.created_actor=actor;
        }
    }
    template<class Pool> bool delete_checkpoint(uint64_t b,uint64_t session,Pool& pool,CallIdentity actor) {
        const auto owned=std::find_if(spawned_.begin(),spawned_.end(),[&](const auto& row){return same_history_identity(row.actor,actor);});
        if(owned==spawned_.end()||!call_identity(b,actor))return false;
        Edit e{};e.deleted=true;e.component=owned->component;e.created_actor=actor;e.asset=owned->asset;
        e.actor_class=call_capture(b,local_read<uint64_t>(actor.address+16));
        clear();if(!call(b,e.component,19))return false;std::memcpy(e.transform.data(),args_,96);
        if(!retain_history_asset(b,session,pool,e.asset)||!retain_history_asset(b,session,pool,e.actor_class))return false;
        if(!clear_spawned(b,session,pool,actor,true))return false;
        redo_.clear();if(undo_.size()>=64)undo_.erase(undo_.begin());undo_.push_back(e);
        history_event(actor);want_grab_=false;duplicate_requested_=false;left_was_=true;return true;
    }
    template<class Pool> bool redo(uint64_t b,uint64_t session,Pool& pool) {
        if(redo_.empty())return true;
        const auto e=redo_.back();Edit reverse=e;
        if(e.deleted) {
            const auto owned=std::find_if(spawned_.begin(),spawned_.end(),[&](const auto& row){return same_history_identity(row.actor,e.created_actor)&&same_history_identity(row.component,e.component);});
            if(owned==spawned_.end()||!call_identity(b,e.created_actor))return false;
            clear();if(!call(b,e.component,19))return false;std::memcpy(reverse.transform.data(),args_,96);
            if(!clear_spawned(b,session,pool,e.created_actor,true))return false;
            history_event(e.created_actor);
        } else if(e.created_actor.address) {
            if(!call_identity(b,e.actor_class)||(e.asset.address&&!call_identity(b,e.asset)))return false;
            CallIdentity actor{},component{};
            if(!spawn_asset(b,session,pool,e.asset,e.actor_class,e.transform.data(),actor,component))return false;
            reverse.created_actor=actor;reverse.component=component;
            history_event(e.created_actor,actor,component);
            // Subsequent transform redos refer to the newly spawned identity.
            remap_history(e,actor,component);
            selected_=component;selected_actor_=actor;
        } else {
            if(!call_identity(b,e.component))return false;
            clear();if(!call(b,e.component,19))return false;std::memcpy(reverse.transform.data(),args_,96);
            if(!component_pose(b,e.component,e.transform.data()))return false;
            refresh_candidate(b,e.component);
        }
        redo_.pop_back();if(undo_.size()>=64)undo_.erase(undo_.begin());undo_.push_back(reverse);
        dragging_=false;carrying_=false;want_grab_=false;nudging_=false;left_was_=true;return true;
    }
    template<class Pool> bool undo(uint64_t b,uint64_t session,Pool& pool) {
        dragging_=false;carrying_=false;duplicate_requested_=false;want_grab_=false;nudging_=false;left_was_=true;
        while(!undo_.empty()) {
            const auto e=undo_.back();
            if(e.deleted) {
                if(!call_identity(b,e.actor_class)||(e.asset.address&&!call_identity(b,e.asset)))return false;
                CallIdentity actor{},component{};
                if(!spawn_asset(b,session,pool,e.asset,e.actor_class,e.transform.data(),actor,component))return false;
                remap_history(e,actor,component);
                Edit reverse=e;reverse.created_actor=actor;reverse.component=component;
                undo_.pop_back();redo_.push_back(reverse);history_event(e.created_actor,actor,component);
                selected_=component;selected_actor_=actor;return true;
            }
            if(e.created_actor.address) {
                // Only the full identity of a duplicate owned by this session can be removed.
                const auto owned=std::find_if(spawned_.begin(),spawned_.end(),[&](const auto& row){return row.actor.index==e.created_actor.index&&row.actor.serial==e.created_actor.serial&&row.actor.address==e.created_actor.address&&row.component.index==e.component.index&&row.component.serial==e.component.serial&&row.component.address==e.component.address;});
                if(owned==spawned_.end()){undo_.pop_back();continue;}
                if(!call_identity(b,owned->actor))return false;
                Edit saved=e;saved.asset=owned->asset;saved.actor_class=call_capture(b,local_read<uint64_t>(owned->actor.address+16));
                clear();if(!call(b,e.component,19))return false;std::memcpy(saved.transform.data(),args_,96);
                if(!clear_spawned(b,session,pool,e.created_actor))return false;
                // clear_spawned also removes this copy's history; don't pop the previous edit.
                redo_.push_back(saved);history_event(e.created_actor);return true;
            }
            if(call_identity(b,e.component)) {
                Edit saved=e;clear();if(!call(b,e.component,19))return false;std::memcpy(saved.transform.data(),args_,96);
                if(!component_pose(b,e.component,e.transform.data()))return false;
                redo_.push_back(saved);
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
        if(!label(b,valid?(dragging_?"MOVING: ":"AIM: ")+name+(carrying_?"  |  Click to place":dragging_?"  |  Release to place":duplicate_click_?"  |  Click to copy":"  |  Hold LMB to grab"):
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
            gpu_end_click();history_request_=0;dragging_=false;nudging_=false;left_was_=true;
            glow(b,session,pool,{});if(ids_[48].address)visibility(b,ids_[48],false);
            return;
        }
        clear();put(0,ids_[0].address);
        if(!call(b,ids_[4],34)){tick_error_=1912;return;}
        if(args_[8]) {gpu_end_click();dragging_=false;left_was_=true;glow(b,session,pool,{});if(ids_[48].address)visibility(b,ids_[48],false);return;}
        LARGE_INTEGER begin{},end{},frequency{};QueryPerformanceCounter(&begin);QueryPerformanceFrequency(&frequency);
        // Escape is edge-triggered and consumed by the native message router.
        // Polling its held state here would close the next layer on another frame.
        auto key=[](int k){return (GetAsyncKeyState(k)&0x8000)!=0;};
        clear();if(!call(b,ids_[0],62)){tick_error_=1960;return;}
        const double mouse_x=get<float>(),mouse_y=get<float>(4);
        if(!std::isfinite(mouse_x)||!std::isfinite(mouse_y)){tick_error_=1960;return;}
        const double look_yaw=elapsed?std::clamp(mouse_x,-4096.,4096.)*mouse_sensitivity_:0;
        const double look_pitch=elapsed?std::clamp(mouse_y,-4096.,4096.)*mouse_sensitivity_:0;
        if(booth_active_){
            const double dt=std::min(.05,double(elapsed)*.001);
            const bool lamp=key('L');
            if(!booth_motion(b,look_yaw,look_pitch,(int(key('S'))-int(key('W')))*dt,
                (int(key(VK_NUMPAD8))-int(key(VK_NUMPAD2)))*60*dt,(int(key(VK_NUMPAD7))-int(key(VK_NUMPAD1)))*60*dt,(int(key(VK_NUMPAD9))-int(key(VK_NUMPAD3)))*60*dt,lamp&&!booth_lamp_was_))tick_error_=1944;
            booth_lamp_was_=lamp;return;
        }
        if(!current(b)){tick_error_=1904;stop(b,session,pool,false);return;}
        scan_candidates(b);
        const auto history_request=history_request_;history_request_=0;
        const bool undo_pressed=history_request==1;
        const bool redo_pressed=history_request==2;
        if(undo_pressed&&!undo(b,session,pool))tick_error_=1911;
        if(redo_pressed&&!carrying_&&!redo(b,session,pool))tick_error_=1965;
        const bool left=key(VK_LBUTTON);
        if(!left||undo_pressed||redo_pressed)gpu_end_click();
        const double dt=std::min(.05,double(elapsed)*.001);
        const double forward=int(key('W'))-int(key('S')),right=int(key('D'))-int(key('A'));
        const double up=int(key(VK_SPACE)||key('E'))-int(key(VK_CONTROL)||key('Q'));
        const double speed=fly_speed_*dt*(key(VK_SHIFT)?4.:1.)/std::max(1.,std::sqrt(forward*forward+right*right+up*up));
        const double fine=150.*dt*(key(VK_MENU)?.1:1.);
        double v[]={forward*speed,right*speed,up*speed,0,
            (int(key(VK_NUMPAD8))-int(key(VK_NUMPAD2)))*fine,
            (int(key(VK_NUMPAD6))-int(key(VK_NUMPAD4)))*fine,
            (int(key(VK_NUMPAD9))-int(key(VK_NUMPAD3)))*fine,
            (int(key(VK_NUMPAD7))-int(key(VK_NUMPAD1)))*fine*.1};
        if(undo_pressed||redo_pressed)std::fill(std::begin(v),std::end(v),0.);
        // Sample view before ray selection; hovering never changes mobility or history.
        rotation_[0]=std::clamp(std::remainder(rotation_[0],360.)+look_pitch,-89.,89.);
        rotation_[1]=std::remainder(rotation_[1]+look_yaw,360.);rotation_[2]=0;
        const bool placing=carrying_&&left&&!left_was_;
        if(placing){carrying_=false;dragging_=false;}
        if(!carrying_&&!placing&&!duplicate_requested_&&left&&(!left_was_||want_grab_)&&!undo_pressed) {
            if(duplicate_click_) {
                if(!pick(b,false,true))tick_error_=1905;
                const auto owned=std::find_if(spawned_.begin(),spawned_.end(),[&](const auto& row){return row.component.index==hover_.index&&row.component.serial==hover_.serial&&row.component.address==hover_.address;});
                if(hover_.address&&owned!=spawned_.end()){selected_=hover_;selected_actor_=hover_actor_;duplicate_requested_=true;gpu_end_click();}
                dragging_=false;want_grab_=!duplicate_requested_;
            } else {if(!pick(b))tick_error_=1905;dragging_=selected_.address!=0;want_grab_=!dragging_;}
        }
        if(duplicate_requested_)for(int j=3;j<8;++j)v[j]=0;
        if(!left){dragging_=carrying_;want_grab_=false;}
        if(carrying_)dragging_=true;left_was_=left;
        const bool nudge=v[4]||v[5]||v[6]||v[7];
        if(nudge&&!nudging_&&!dragging_&&selected_.address)if(!checkpoint(b,selected_))tick_error_=1911;
        nudging_=nudge;v[3]=dragging_?1.:0.;
        if(!tick_error_&&!move(b,v))tick_error_=1906;
        if(!dragging_){last_hover_=now;if(!pick(b,false))tick_error_=1905;}
        if(true) {
            last_hud_=now;
            if(!glow(b,session,pool,highlight_mode_==1?(dragging_?selected_:hover_):(highlight_mode_==2&&dragging_?selected_:CallIdentity{})))tick_error_=1913;
            if(ids_[48].address&&(!visibility(b,ids_[48],true)||!feedback(b)))tick_error_=1910;
        }
        QueryPerformanceCounter(&end);const double cost=double(end.QuadPart-begin.QuadPart)*1000./double(frequency.QuadPart);
        ++ticks_;tick_ms_sum_+=double(elapsed);cost_ms_sum_+=cost;max_cost_ms_=std::max(max_cost_ms_,cost);
        if(tick_error_)stop(b,session,pool,false);
    }
private:
