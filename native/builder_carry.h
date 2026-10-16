    bool carry_owned(uint64_t b,CallIdentity component) {
        auto it=std::find_if(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.component.index==component.index&&row.component.serial==component.serial&&row.component.address==component.address;});
        if(it==spawned_.end()||!call_identity(b,component)||!call_identity(b,it->actor))return false;
        double center[3],extent[3];if(!bulk_bounds(b,it->actor,center,extent))return false;
        clear();if(!call(b,component,19))return false;
        depth_=std::clamp(std::sqrt(extent[0]*extent[0]+extent[1]*extent[1]+extent[2]*extent[2])*2.,450.,20000.);
        for(int j=0;j<3;++j)offset_[j]=get<double>(32+8*j)-center[j];
        selected_=component;selected_actor_=it->actor;carrying_=true;dragging_=true;want_grab_=false;left_was_=true;
        const double motion[]={0,0,0,1,0,0,0,0};
        if(!move(b,motion))return false;
        Edit created{};created.component=component;created.created_actor=it->actor;
        if(undo_.size()>=64)undo_.erase(undo_.begin());
        redo_.clear();undo_.push_back(created);return true;
    }
    template<class Pool> bool duplicate_hand(uint64_t b,uint64_t session,Pool& pool,CallIdentity source,CallIdentity& actor,CallIdentity& component) {
        auto it=std::find_if(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.component.index==source.index&&row.component.serial==source.serial&&row.component.address==source.address;});
        if(it==spawned_.end()||!call_identity(b,source)||!call_identity(b,it->asset)||!call_identity(b,it->actor))return false;
        const auto asset=it->asset;
        clear();if(!call(b,source,19))return false;
        uint8_t pose[96];std::memcpy(pose,args_,96);
        if(!spawn_asset(b,session,pool,asset,ids_[84],pose,actor,component))return false;
        if(carry_owned(b,component))return true;
        clear_spawned(b,session,pool,actor);actor={};component={};return false;
    }
