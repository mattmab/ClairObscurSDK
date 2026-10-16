    void gpu_begin_click(const double* origin,const double* dir) {
        if(gpu_click_active_)return;
        gpu_click_active_=true;gpu_click_empty_=false;
        std::memcpy(gpu_click_origin_,origin,24);std::memcpy(gpu_click_dir_,dir,24);
        // A click starts a fresh frozen query; never grab an older hover result.
        gpu_ready_component_={};gpu_query_stale_=true;
    }
    void gpu_end_click(){gpu_click_active_=false;gpu_click_empty_=false;}
    bool gpu_centered(uint64_t b,const double* point) {
        clear();if(!call(b,ids_[0],32))return false;const auto width=get<int32_t>(),height=get<int32_t>(4);
        clear();std::memcpy(args_,point,24);if(!call(b,ids_[0],24)||!args_[41])return false;
        return std::hypot(get<double>(24)-width*.5,get<double>(32)-height*.5)<=8.;
    }
    void gpu_candidates(const double* rayOrigin,const double* dir,double maximum) {
        gpu_candidates_.clear();
        for(const auto& c:candidates_) {
            double relative[3];for(int j=0;j<3;++j)relative[j]=rayOrigin[j]-c.pose[4+j];
            double origin[3],direction[3];inverse_rotate(c.pose,relative,origin);inverse_rotate(c.pose,dir,direction);
            double entry=0,exitDistance=maximum;bool valid=true;
            for(int j=0;j<3;++j) {
                origin[j]/=c.pose[8+j];direction[j]/=c.pose[8+j];
                if(std::abs(direction[j])<1.e-10){if(origin[j]<c.low[j]||origin[j]>c.high[j])valid=false;continue;}
                double a=(c.low[j]-origin[j])/direction[j],z=(c.high[j]-origin[j])/direction[j];if(a>z)std::swap(a,z);
                entry=std::max(entry,a);exitDistance=std::min(exitDistance,z);if(entry>exitDistance)valid=false;
            }
            if(valid&&exitDistance>1&&entry<maximum)gpu_candidates_.push_back({c.actor,c.component,entry});
        }
        std::sort(gpu_candidates_.begin(),gpu_candidates_.end(),[](const GpuCandidate& a,const GpuCandidate& b){return a.entry<b.entry;});
        // A physics hit is only a scheduling hint: its rendered mesh must
        // still match the foreground scene surface. Keep the remaining list sorted.
        const auto preferred=std::find_if(gpu_candidates_.begin(),gpu_candidates_.end(),[&](const GpuCandidate& c){return c.component.address==gpu_preferred_component_.address&&c.component.serial==gpu_preferred_component_.serial;});
        if(preferred!=gpu_candidates_.end())std::rotate(gpu_candidates_.begin(),preferred,preferred+1);
        // Every overlapping bound remains eligible; a nearer rendered surface
        // may be behind many large, empty bounds in the sorted list.
    }
    bool gpu_pick(uint64_t b,const double* origin,const double* dir,CallIdentity& actor,CallIdentity& component,double& distance) {
        const auto now=GetTickCount64();gpu_error_=gpu_bridge_.error();if(gpu_error_)return true;
        // Capture the current occlusion cap before publishing an older display
        // result. An old hit must never seed (and survive) a new surface search.
        const double limit=distance;
        double originDelta=0,directionDot=0;
        for(int j=0;j<3;++j){originDelta+=(origin[j]-gpu_origin_[j])*(origin[j]-gpu_origin_[j]);directionDot+=dir[j]*gpu_dir_[j];}
        // Let the frozen capture finish during normal camera motion. Validate
        // its actual surface point against the live crosshair before use.
        // Teleports, sharp turns and over-age queries still restart promptly.
        if(gpu_query_active_&&(originDelta>625.||directionDot<.996194698||now-gpu_query_started_>=2000))gpu_query_stale_=true;
        float sampleDepth=0;uint64_t completed=0;
        while((completed=gpu_bridge_.poll(sampleDepth))!=0) {
            auto it=std::find_if(gpu_flights_.begin(),gpu_flights_.end(),[&](const GpuPending& p){return p.request==completed;});
            if(it==gpu_flights_.end())continue;
            ++gpu_completed_;gpu_last_depth_=sampleDepth;gpu_last_latency_=double(now-it->sent);
            auto* diagnostic=gpu_samples_+6*(gpu_sample_cursor_++%8);diagnostic[0]=double(completed);diagnostic[1]=it->scene?1.:0.;diagnostic[2]=double(it->component.index);diagnostic[3]=sampleDepth;diagnostic[4]=gpu_best_distance_;diagnostic[5]=gpu_query_stale_?1.:0.;
            if(!gpu_query_stale_) {
                if(it->scene) {
                    gpu_scene_depth_=sampleDepth;
                    // Render all scene primitives first, including unsupported
                    // instances. They must occlude selectable props behind them.
                    if(std::isfinite(sampleDepth)&&sampleDepth>0.f)
                        gpu_best_distance_=std::min(gpu_query_limit_,double(sampleDepth)+std::max(1.,double(sampleDepth)*1.e-5));
                    else gpu_best_distance_=0.; // Unknown scene depth: do not pick through it.
                    gpu_candidates(gpu_origin_,gpu_dir_,gpu_best_distance_);
                    gpu_next_=0;gpu_scene_pending_=false;
                } else if(std::isfinite(sampleDepth)&&sampleDepth>1.f&&sampleDepth<gpu_best_distance_&&call_identity(b,it->actor)&&call_identity(b,it->component)) {
                    ++gpu_surface_hits_;gpu_best_actor_=it->actor;gpu_best_component_=it->component;gpu_best_distance_=sampleDepth;
                    // Identical scene and isolated depths prove this is the
                    // foreground mesh; empty bounds need no further captures.
                    if(std::isfinite(gpu_scene_depth_)&&gpu_scene_depth_>1.&&std::abs(double(sampleDepth)-gpu_scene_depth_)<=.01)gpu_next_=gpu_candidates_.size();
                }
            }
            gpu_flights_.erase(it);
        }
        gpu_pending_=gpu_flights_.size();
        if(gpu_pending_&&now-gpu_flights_.front().sent>2000){gpu_error_=6;return true;}
        if(gpu_query_active_&&gpu_query_stale_&&!gpu_pending_)gpu_query_active_=false;
        if(gpu_query_active_&&!gpu_scene_pending_&&!gpu_pending_&&(gpu_next_>=gpu_candidates_.size()||gpu_candidates_[gpu_next_].entry>=gpu_best_distance_)) {
            gpu_click_empty_=gpu_click_active_&&!gpu_best_component_.address;
            gpu_query_active_=false;gpu_ready_actor_=gpu_best_actor_;gpu_ready_component_=gpu_best_component_;gpu_ready_time_=now;
            std::memcpy(gpu_ready_origin_,gpu_origin_,24);
            for(int j=0;j<3;++j)gpu_ready_point_[j]=gpu_origin_[j]+gpu_dir_[j]*gpu_best_distance_;
        }
        double readyDepth=0;for(int j=0;j<3;++j)readyDepth+=(gpu_ready_point_[j]-gpu_ready_origin_[j])*(gpu_ready_point_[j]-gpu_ready_origin_[j]);
        const double travelLimit=std::min(25.,std::sqrt(readyDepth)*.05);
        double readyDelta=0;for(int j=0;j<3;++j)readyDelta+=(origin[j]-gpu_ready_origin_[j])*(origin[j]-gpu_ready_origin_[j]);
        if(readyDelta<=travelLimit*travelLimit&&gpu_ready_component_.address&&now-gpu_ready_time_<150&&call_identity(b,gpu_ready_actor_)&&call_identity(b,gpu_ready_component_)&&(gpu_click_active_||gpu_centered(b,gpu_ready_point_))) {
            double squared=0;for(int j=0;j<3;++j)squared+=(gpu_ready_point_[j]-origin[j])*(gpu_ready_point_[j]-origin[j]);
            const auto hitDistance=std::sqrt(squared);
            if(hitDistance<distance){actor=gpu_ready_actor_;component=gpu_ready_component_;distance=hitDistance;}
        }
        if(!gpu_query_active_&&!gpu_pending_) {
            gpu_query_started_=now;
            std::memcpy(gpu_origin_,origin,24);std::memcpy(gpu_dir_,dir,24);
            gpu_best_actor_={};gpu_best_component_={};gpu_best_distance_=gpu_query_limit_=limit;
            gpu_candidates_.clear();gpu_next_=0;gpu_query_active_=gpu_scene_pending_=true;gpu_query_stale_=false;
        }
        // Only one capture may own the shared target at a time. Changing the
        // show-only list before its readback finishes can associate another
        // component's depth with this request's identity.
        if(!gpu_query_active_||gpu_query_stale_||gpu_pending_||!gpu_bridge_.ready())return true;
        GpuCandidate candidate{};
        const bool scene=gpu_scene_pending_;
        if(!scene) {
            if(gpu_next_>=gpu_candidates_.size()||gpu_candidates_[gpu_next_].entry>=gpu_best_distance_)return true;
            candidate=gpu_candidates_[gpu_next_++];
            if(!call_identity(b,candidate.actor)||!call_identity(b,candidate.component)) {
                auto* diagnostic=gpu_samples_+6*(gpu_sample_cursor_++%8);
                diagnostic[0]=double(gpu_sequence_);diagnostic[1]=-1.;diagnostic[2]=double(candidate.component.index);
                diagnostic[3]=candidate.entry;diagnostic[4]=double(candidate.actor.serial);diagnostic[5]=double(candidate.component.serial);
                return true;
            }
        }
        const double rotation[]={std::atan2(gpu_dir_[2],std::hypot(gpu_dir_[0],gpu_dir_[1]))*180./3.141592653589793,std::atan2(gpu_dir_[1],gpu_dir_[0])*180./3.141592653589793,0.};
        clear();std::memcpy(args_,gpu_origin_,24);std::memcpy(args_+24,rotation,24);args_[304]=1;if(!call(b,gpu_actor_,5)||!args_[305])return false;
        if(!gpu_setting(b,"PrimitiveRenderMode",scene?1:2))return false;
        clear();if(!call(b,gpu_capture_,43))return false;
        if(!scene){clear();put(0,candidate.component.address);if(!call(b,gpu_capture_,42))return false;}
        const auto request=++gpu_sequence_;if(!gpu_bridge_.arm(request)){if(!scene)--gpu_next_;return true;}
        gpu_flights_.push_back({request,now,candidate.actor,candidate.component,scene});gpu_pending_=gpu_flights_.size();gpu_sent_at_=gpu_last_capture_=now;
        clear();return call(b,gpu_capture_,41);
    }
