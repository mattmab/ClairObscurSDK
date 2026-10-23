    // This path never restores borrowed movement, materials, camera or input.
    // A separately proved different viewport world precedes storage release.
    template<class Pool> uint32_t retire_world(uint64_t b,uint64_t session,Pool& pool) {
        e33_retired_world::TargetOps proof{b};
        if(!proof.context())return 407;
        if(!owner_){
            if(token_||active_||!spawned_.empty()||!materials_.empty()||
                !history_assets_.empty()||gpu_actor_lease_||gpu_target_lease_||
                preview_actor_lease_||preview_target_lease_||!preview_images_.empty()||!cached_images_.empty())return 1968;
            const auto error=epoch_.release(proof,pool,session);if(error)return error;
            epoch_.reset();return 0;
        }
        if(!epoch_.established())return 1968;
        const auto state=epoch_.prove(proof);
        if(state==e33_retired_world::Result::SameWorld||state==e33_retired_world::Result::Pending)return 407;
        if(state!=e33_retired_world::Result::Retired)return 1968;
        retiring_=true;auto_tick_=false;dragging_=carrying_=want_grab_=false;
        if(!retirement_bridges_stopped_){
            if(!gpu_bridge_.stop())return 407;
            if(image_started_)image_bridge_.stop();
            image_started_=image_pending_=image_await_arm_=false;
            TargetOwnedTextOps text_ops{b};
            if(release_owned_text(text_ops,text_)!=OwnedTextResult::Ok)return 1968;
            retirement_bridges_stopped_=true;
        }
        auto release=[&](uint64_t&token,const CallIdentity&id)->uint32_t{
            TargetStrongReferenceOps refs{b,{}};
            return release_retired_storage(pool,refs,session,id.address,token);
        };
        // Remove only acknowledged records; a pending/unknown suffix remains
        // owned. There are no game-object callbacks to replay on a later poll.
        for(auto* rows:{&preview_images_,&cached_images_}){
            while(!rows->empty()){
                auto&row=rows->back();const auto error=release(row.second,row.first);
                if(error)return error;rows->pop_back();
            }
        }
        while(!materials_.empty()){
            auto&row=materials_.back();const auto error=release(row.lease,row.original);
            if(error)return error;materials_.pop_back();
        }
        while(!history_assets_.empty()){
            auto&row=history_assets_.back();const auto error=release(row.lease,row.identity);
            if(error)return error;history_assets_.pop_back();
        }
        while(!spawned_.empty()){
            auto&row=spawned_.back();const auto error=release(row.lease,row.actor);
            if(error)return error;spawned_.pop_back();
        }
        for(auto pair:{std::make_pair(&gpu_actor_lease_,gpu_actor_),std::make_pair(&gpu_target_lease_,gpu_target_),
                std::make_pair(&preview_actor_lease_,preview_actor_),std::make_pair(&preview_target_lease_,preview_target_),
                std::make_pair(&token_,camera_)}){
            const auto error=release(*pair.first,pair.second);if(error)return error;
        }
        const auto error=epoch_.release(proof,pool,session);if(error)return error;
        edits_.clear();undo_.clear();redo_.clear();history_events_.clear();candidates_.clear();
        booth_owned_.clear();booth_lights_.clear();gpu_flights_.clear();gpu_candidates_.clear();
        camera_={};target_={};selected_={};selected_actor_={};hover_={};hover_actor_={};glowing_={};menu_widget_={};
        gpu_actor_={};gpu_capture_={};gpu_target_={};gpu_ready_component_={};
        preview_actor_={};preview_capture_={};preview_target_={};thumbnail_prop_={};
        booth_prop_={};gallery_floor_={};gallery_floor_component_={};
        active_=ignored_=frozen_=overlay_=booth_active_=false;
        menu_drag_enabled_=menu_drag_down_=menu_dragging_=false;
        gpu_pending_=0;gpu_query_active_=gpu_scene_pending_=gpu_click_active_=false;
        mouse_rotation_.reset();std::fill(std::begin(ids_),std::end(ids_),CallIdentity{});
        epoch_.reset();owner_=0;retiring_=retirement_bridges_stopped_=false;
        return 0;
    }
