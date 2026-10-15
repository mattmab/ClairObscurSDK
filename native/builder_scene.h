    struct Spawned {CallIdentity actor,component,asset;uint64_t lease;};
    std::vector<Spawned> spawned_;
    bool valid_pose(const uint8_t* pose) {
        double v[12];std::memcpy(v,pose,96);
        for(auto n:v)if(!std::isfinite(n)||std::abs(n)>1.e8)return false;
        double norm=0;for(int i=0;i<4;++i)norm+=v[i]*v[i];
        if(norm<.999||norm>1.001)return false;
        for(int i=8;i<11;++i)if(std::abs(v[i])<.001||std::abs(v[i])>10000)return false;
        return true;
    }
    bool track_component(uint64_t b,CallIdentity component) {
        if(std::any_of(edits_.begin(),edits_.end(),[&](const Edit& e){return e.component.address==component.address&&e.component.serial==component.serial;}))return true;
        if(edits_.size()>=scene_limit_)return false;
        Edit e{};e.component=component;
        if(!byte_property(b,component,"SceneComponent","Mobility",e.mobility)||e.mobility>2)return false;
        clear();if(!call(b,component,19))return false;std::memcpy(e.transform.data(),args_,96);edits_.push_back(e);return true;
    }
    template<class Pool> bool clear_spawned(uint64_t b,uint64_t session,Pool& pool,CallIdentity only={}) {
        if(!glow(b,session,pool,{}))return false;
        for(size_t i=spawned_.size();i>0;--i) {
            auto& row=spawned_[i-1];if(only.address&&(only.address!=row.actor.address||only.serial!=row.actor.serial))continue;
            if(call_identity(b,row.actor)){clear();if(!call(b,row.actor,2))return false;}
            const auto component=row.component;
            auto matches=[&](const Edit& e){return e.component.address==component.address&&e.component.serial==component.serial;};
            edits_.erase(std::remove_if(edits_.begin(),edits_.end(),matches),edits_.end());undo_.erase(std::remove_if(undo_.begin(),undo_.end(),matches),undo_.end());
            if(selected_.address==component.address){selected_={};selected_actor_={};dragging_=false;}
            TargetStrongReferenceOps ops{b,{-1,0,0}};if(row.lease&&pool.release(ops,session,row.lease)!=StrongLeaseResult::Ok)return false;
            if(row.actor.address==thumbnail_prop_.address)thumbnail_prop_={};
            if(row.actor.address==gallery_floor_.address){gallery_floor_={};gallery_floor_component_={};}
            spawned_.erase(spawned_.begin()+i-1);
        }
        gpu_ready_component_={};return true;
    }
    template<class Pool> bool spawn_asset(uint64_t b,uint64_t session,Pool& pool,CallIdentity asset,CallIdentity cls,const uint8_t* pose,CallIdentity& resultActor,CallIdentity& resultComponent) {
        if(!valid_pose(pose)||edits_.size()>=scene_limit_||spawned_.size()>=scene_limit_||!call_identity(b,cls)||!call_is_class(b,cls.address)||!call_derives(b,cls.address,ids_[86].address)||call_derives(b,cls.address,ids_[7].address))return false;
        if(asset.address&&(!call_identity(b,asset)||!call_derives(b,local_read<uint64_t>(asset.address+16),ids_[85].address)||cls.address!=ids_[84].address))return false;
        clear();put(0,ids_[0].address);put(8,cls.address);std::memcpy(args_+16,pose,96);args_[112]=1;
        if(!call(b,ids_[4],0))return false;const auto actor=call_capture(b,get<uint64_t>(136));if(!actor.address)return false;
        spawned_.push_back({actor,{},asset,0});auto& row=spawned_.back();
        TargetStrongReferenceOps ops{b,actor};if(pool.acquire(ops,session,actor.address,row.lease)!=StrongLeaseResult::Ok)return false;
        clear();if(!call(b,actor,17))return false;row.component=call_capture(b,get<uint64_t>());
        if(row.component.address){clear();args_[0]=2;if(!call(b,row.component,16))return false;clear();if(!call(b,actor,17))return false;row.component=call_capture(b,get<uint64_t>());}
        if(asset.address){if(!row.component.address)return false;clear();put(0,asset.address);if(!call(b,row.component,46)||!args_[8])return false;}
        clear();put(0,actor.address);std::memcpy(args_+16,pose,96);if(!call(b,ids_[4],1)||get<uint64_t>(120)!=actor.address)return false;
        clear();if(!call(b,actor,17))return false;row.component=call_capture(b,get<uint64_t>());
        if(!row.component.address)return false;
        clear();args_[0]=2;if(!call(b,row.component,16))return false;
        clear();if(!call(b,actor,17))return false;row.component=call_capture(b,get<uint64_t>());
        if(!track_component(b,row.component)||!component_pose(b,row.component,pose))return false;
        resultActor=actor;resultComponent=row.component;
        if(ordinary(b,actor,row.component)){Candidate c{};c.actor=actor;c.component=row.component;if(candidate_pose(b,c))candidates_.push_back(c);}
        return true;
    }
    bool apply_pose(uint64_t b,CallIdentity component,const uint8_t* pose) {
        if(!valid_pose(pose)||!call_identity(b,component))return false;
        clear();if(!call(b,component,18))return false;const auto actor=call_capture(b,get<uint64_t>());
        const bool owned=std::any_of(spawned_.begin(),spawned_.end(),[&](const Spawned& s){return s.actor.address==actor.address&&s.component.address==component.address;});
        if(!owned&&!ordinary(b,actor,component))return false;
        if(!checkpoint(b,component)||!track_component(b,component))return false;
        clear();args_[0]=2;if(!call(b,component,16)||!component_pose(b,component,pose))return false;
        refresh_candidate(b,component);gpu_ready_component_={};return true;
    }
    bool export_scene(uint64_t b,uint8_t* raw,uint32_t offset=0) {
        uint32_t count=0,index=offset;const auto total=uint32_t(edits_.size());if(offset>total)return false;
        for(;index<total&&count<128;++index) {const auto& e=edits_[index];
            if(!call_identity(b,e.component))continue;
            if(thumbnail_prop_.address&&std::any_of(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.actor.address==thumbnail_prop_.address&&row.component.address==e.component.address;}))continue;
            if(booth_active_){const auto excluded=std::any_of(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.component.address==e.component.address&&(row.actor.address==booth_prop_.address||std::any_of(booth_owned_.begin(),booth_owned_.end(),[&](const CallIdentity& a){return a.address==row.actor.address;}));});if(excluded)continue;}
            clear();if(!call(b,e.component,19))return false;
            auto* row=raw+4096+count*128;std::memcpy(row,&e.component,16);std::memcpy(row+16,args_,96);
            const uint32_t owned=std::any_of(spawned_.begin(),spawned_.end(),[&](const Spawned& s){return s.component.address==e.component.address&&s.component.serial==e.component.serial;})?1:0;
            std::memcpy(row+112,&owned,4);row[116]=e.mobility;++count;
        }
        std::memcpy(raw+3560,&count,4);std::memcpy(raw+3564,&total,4);std::memcpy(raw+3568,&index,4);return true;
    }
