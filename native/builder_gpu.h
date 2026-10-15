    builder_gpu::Bridge gpu_bridge_;
    CallIdentity gpu_actor_{},gpu_capture_{},gpu_target_{};
    uint64_t gpu_actor_lease_=0,gpu_target_lease_=0,gpu_sequence_=0,gpu_pending_=0,gpu_sent_at_=0,gpu_last_capture_=0,gpu_completed_=0;
    uint32_t gpu_error_=0;
    double gpu_last_depth_=0,gpu_last_latency_=0;
    uint64_t gpu_surface_hits_=0;
    struct GpuCandidate {CallIdentity actor,component;double entry;};
    std::vector<GpuCandidate> gpu_candidates_;
    struct GpuPending {uint64_t request,sent;CallIdentity actor,component;};
    std::vector<GpuPending> gpu_flights_;
    size_t gpu_next_=0;
    bool gpu_query_active_=false;
    double gpu_origin_[3]{},gpu_dir_[3]{},gpu_best_distance_=200000.,gpu_ready_point_[3]{};
    CallIdentity gpu_best_actor_{},gpu_best_component_{},gpu_pending_actor_{},gpu_pending_component_{},gpu_ready_actor_{},gpu_ready_component_{};
    uint64_t gpu_ready_time_=0;
    uint64_t gpu_property(uint64_t b,CallIdentity object,const char* name,const GpuProperty*& descriptor,uint64_t& owner) {
        descriptor=nullptr;if(!call_identity(b,object))return 0;
        for(const auto& p:gpu_properties)if(!std::strcmp(p.name,name)){descriptor=&p;break;}
        if(!descriptor)return 0;const auto& p=*descriptor;
        auto cls=local_read<uint64_t>(object.address+16);
        for(int sampleDepth=0;cls&&sampleDepth<64;++sampleDepth,cls=local_read<uint64_t>(cls+0x40)) {
            auto f=local_read<uint64_t>(cls+0x50);
            for(int n=0;f&&n<512;++n,f=local_read<uint64_t>(f+24)) {
                if(!exact_name(b,f+32,name))continue;
                if(local_read<uint64_t>(f+16)!=(cls|1)||local_read<uint64_t>(f)!=b+p.table||!exact_name(b,local_read<uint64_t>(f+8),p.type)||
                   local_read<uint32_t>(f+0x44)!=p.offset||local_read<uint32_t>(f+0x34)!=p.width||local_read<uint32_t>(f+0x30)!=1||local_read<uint64_t>(f+0x38)!=p.flags||
                   p.offset+p.width>uint32_t(local_read<int32_t>(cls+0x58))||(p.boolean&&local_read<uint32_t>(f+0x70)!=p.boolean))return 0;
                owner=cls;return f;
            }
        }
        return 0;
    }
    bool gpu_setting(uint64_t b,const char* name,uint64_t value) {
        // Only this mod's newly spawned capture component may be configured.
        if(!call_identity(b,gpu_actor_)||!call_identity(b,gpu_capture_))return false;
        clear();if(!call(b,gpu_capture_,18)||get<uint64_t>()!=gpu_actor_.address)return false;
        const GpuProperty* p=nullptr;uint64_t owner=0;const auto field=gpu_property(b,gpu_capture_,name,p,owner);if(!field)return false;
        if(!std::strcmp(p->type,"ObjectProperty")) {
            ObjectAssignment r{};r.target=gpu_capture_;r.owner=call_capture(b,owner);r.constraint=call_capture(b,local_read<uint64_t>(field+0x70));
            r.expected=call_capture(b,local_read<uint64_t>(gpu_capture_.address+p->offset));r.value=call_capture(b,value);r.flags=p->flags;r.offset=p->offset;r.dimension=1;strcpy_s(r.name,name);
            TargetObjectAssignmentOps ops{b};return assign_object_property(ops,r)==ObjectAssignmentResult::Ok;
        }
        auto* dest=reinterpret_cast<uint8_t*>(gpu_capture_.address+p->offset);
        if(p->boolean){const auto mask=uint8_t(p->boolean>>24),bit=uint8_t(p->boolean>>16);*dest=uint8_t((*dest&~mask)|(value?bit:0));}
        else if(p->width==1||p->width==4)std::memcpy(dest,&value,p->width);else return false;
        return true;
    }
    template<class Pool> bool gpu_setup(uint64_t b,uint64_t session,Pool& pool) {
        gpu_error_=0;gpu_pending_=gpu_completed_=gpu_last_capture_=gpu_ready_time_=0;gpu_query_active_=false;gpu_flights_.clear();gpu_candidates_.clear();gpu_ready_component_={};
        if(!gpu_bridge_.start(257,259,2)){gpu_error_=gpu_bridge_.error();return false;}
        clear();put(0,ids_[0].address);put(8,ids_[80].address);transform(args_+16,position_);args_[112]=1;
        if(!call(b,ids_[4],0))return false;gpu_actor_=call_capture(b,get<uint64_t>(136));
        if(!gpu_actor_.address)return false;
        TargetStrongReferenceOps actorOps{b,gpu_actor_};if(pool.acquire(actorOps,session,gpu_actor_.address,gpu_actor_lease_)!=StrongLeaseResult::Ok)return false;
        const GpuProperty* p=nullptr;uint64_t owner=0;if(!gpu_property(b,gpu_actor_,"CaptureComponent2D",p,owner))return false;
        gpu_capture_=call_capture(b,local_read<uint64_t>(gpu_actor_.address+p->offset));if(!gpu_capture_.address)return false;
        float fov=1.f,clip=1.f;uint32_t fovBits=0,clipBits=0;std::memcpy(&fovBits,&fov,4);std::memcpy(&clipBits,&clip,4);
        if(!gpu_setting(b,"bCaptureEveryFrame",0)||!gpu_setting(b,"bCaptureOnMovement",0)||!gpu_setting(b,"bUseRayTracingIfEnabled",0)||!gpu_setting(b,"CaptureSource",4)||!gpu_setting(b,"PrimitiveRenderMode",2)||!gpu_setting(b,"FOVAngle",fovBits)||!gpu_setting(b,"bOverride_CustomNearClippingPlane",1)||!gpu_setting(b,"CustomNearClippingPlane",clipBits))return false;
        clear();put(0,gpu_actor_.address);transform(args_+16,position_);if(!call(b,ids_[4],1))return false;
        clear();put(0,ids_[0].address);put(8,int32_t(257));put(12,int32_t(259));args_[16]=7;
        if(!call(b,ids_[83],44))return false;gpu_target_=call_capture(b,get<uint64_t>(40));if(!gpu_target_.address)return false;
        TargetStrongReferenceOps targetOps{b,gpu_target_};if(pool.acquire(targetOps,session,gpu_target_.address,gpu_target_lease_)!=StrongLeaseResult::Ok)return false;
        return gpu_setting(b,"TextureTarget",gpu_target_.address);
    }
    template<class Pool> bool gpu_stop(uint64_t b,uint64_t session,Pool& pool) {
        if(!gpu_bridge_.stop())return false;
        if(call_identity(b,gpu_actor_)){clear();if(!call(b,gpu_actor_,2))return false;}gpu_actor_={};gpu_capture_={};
        if(call_identity(b,gpu_target_)){clear();put(0,gpu_target_.address);if(!call(b,ids_[83],45))return false;}gpu_target_={};
        TargetStrongReferenceOps ops{b,{-1,0,0}};
        if(gpu_actor_lease_){if(pool.release(ops,session,gpu_actor_lease_)!=StrongLeaseResult::Ok)return false;gpu_actor_lease_=0;}
        if(gpu_target_lease_){if(pool.release(ops,session,gpu_target_lease_)!=StrongLeaseResult::Ok)return false;gpu_target_lease_=0;}
        gpu_pending_=0;gpu_query_active_=false;gpu_flights_.clear();gpu_candidates_.clear();gpu_ready_component_={};return true;
    }
    bool gpu_centered(uint64_t b,const double* point) {
        clear();if(!call(b,ids_[0],32))return false;const auto width=get<int32_t>(),height=get<int32_t>(4);
        clear();std::memcpy(args_,point,24);if(!call(b,ids_[0],24)||!args_[41])return false;
        return std::hypot(get<double>(24)-width*.5,get<double>(32)-height*.5)<=2.;
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
        if(gpu_candidates_.size()>32)gpu_candidates_.resize(32);
    }
    bool gpu_pick(uint64_t b,const double* origin,const double* dir,CallIdentity& actor,CallIdentity& component,double& distance) {
        const auto now=GetTickCount64();gpu_error_=gpu_bridge_.error();if(gpu_error_)return true;
        float sampleDepth=0;uint64_t completed=0;
        while((completed=gpu_bridge_.poll(sampleDepth))!=0) {
            auto it=std::find_if(gpu_flights_.begin(),gpu_flights_.end(),[&](const GpuPending& p){return p.request==completed;});
            if(it==gpu_flights_.end())continue;
            ++gpu_completed_;gpu_last_depth_=sampleDepth;gpu_last_latency_=double(now-it->sent);
            if(std::isfinite(sampleDepth)&&sampleDepth>1.f&&sampleDepth<gpu_best_distance_&&call_identity(b,it->actor)&&call_identity(b,it->component)) {
                ++gpu_surface_hits_;gpu_best_actor_=it->actor;gpu_best_component_=it->component;gpu_best_distance_=sampleDepth;
            }
            gpu_flights_.erase(it);
        }
        gpu_pending_=gpu_flights_.size();
        double originDelta=0,directionDot=0;for(int j=0;j<3;++j){originDelta+=(origin[j]-gpu_origin_[j])*(origin[j]-gpu_origin_[j]);directionDot+=dir[j]*gpu_dir_[j];}
        if(gpu_query_active_&&(originDelta>2500.||directionDot<.9999)){if(gpu_pending_)return true;gpu_query_active_=false;}
        if(gpu_pending_&&now-gpu_flights_.front().sent>2000){gpu_error_=6;return true;}
        if(gpu_query_active_&&!gpu_pending_&&(gpu_next_>=gpu_candidates_.size()||gpu_candidates_[gpu_next_].entry>=gpu_best_distance_)) {
            gpu_query_active_=false;gpu_ready_actor_=gpu_best_actor_;gpu_ready_component_=gpu_best_component_;gpu_ready_time_=now;
            for(int j=0;j<3;++j)gpu_ready_point_[j]=gpu_origin_[j]+gpu_dir_[j]*gpu_best_distance_;
        }
        if(gpu_ready_component_.address&&now-gpu_ready_time_<150&&call_identity(b,gpu_ready_component_)&&gpu_centered(b,gpu_ready_point_)) {
            double squared=0;for(int j=0;j<3;++j)squared+=(gpu_ready_point_[j]-origin[j])*(gpu_ready_point_[j]-origin[j]);
            const auto hitDistance=std::sqrt(squared);
            if(hitDistance<distance){actor=gpu_ready_actor_;component=gpu_ready_component_;distance=hitDistance;}
        }
        if(!gpu_query_active_&&!gpu_pending_) {
            std::memcpy(gpu_origin_,origin,24);std::memcpy(gpu_dir_,dir,24);gpu_best_actor_=actor;gpu_best_component_=component;gpu_best_distance_=distance;
            gpu_candidates(origin,dir,distance);gpu_next_=0;gpu_query_active_=!gpu_candidates_.empty();
        }
        if(!gpu_query_active_||gpu_pending_>=3||gpu_next_>=gpu_candidates_.size()||gpu_candidates_[gpu_next_].entry>=gpu_best_distance_||!gpu_bridge_.ready())return true;
        const auto candidate=gpu_candidates_[gpu_next_++];
        if(!call_identity(b,candidate.actor)||!call_identity(b,candidate.component))return true;
        const double rotation[]={std::atan2(gpu_dir_[2],std::hypot(gpu_dir_[0],gpu_dir_[1]))*180./3.141592653589793,std::atan2(gpu_dir_[1],gpu_dir_[0])*180./3.141592653589793,0.};
        clear();std::memcpy(args_,gpu_origin_,24);std::memcpy(args_+24,rotation,24);args_[304]=1;if(!call(b,gpu_actor_,5)||!args_[305])return false;
        clear();if(!call(b,gpu_capture_,43))return false;
        clear();put(0,candidate.component.address);if(!call(b,gpu_capture_,42))return false;
        const auto request=++gpu_sequence_;if(!gpu_bridge_.arm(request)){--gpu_next_;return true;}
        gpu_flights_.push_back({request,now,candidate.actor,candidate.component});gpu_pending_=gpu_flights_.size();gpu_sent_at_=gpu_last_capture_=now;
        clear();return call(b,gpu_capture_,41);
    }

