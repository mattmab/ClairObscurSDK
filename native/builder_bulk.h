    // Fixed-size commands; at most 64 rows and a 4 ms game-thread budget.
    // A single cold engine load cannot be preempted, so the budget is checked
    // after every object, never after the entire requested batch.
    static constexpr size_t scene_limit_=6000;
    std::unordered_map<uint32_t,CallIdentity> bulk_meshes_;
    CallIdentity gallery_floor_{},gallery_floor_component_{};
    double gallery_origin_[3]{},gallery_spacing_=600,gallery_width_=3600;
    double gallery_x_=0,gallery_y_=0,gallery_depth_=0,gallery_max_x_=100,gallery_max_y_=100;
    uint32_t gallery_columns_=6,gallery_count_=0;
    bool gallery_tight_=true;
    CallIdentity bulk_mesh(uint64_t b,uint32_t index) {
        if(index==0xffffffffU)return ids_[88]; // Verified engine cube for floors.
        if(!registry_complete_||index>=registry_paths_.size())return {};
        const auto cached=bulk_meshes_.find(index);
        if(cached!=bulk_meshes_.end()&&call_identity(b,cached->second))return cached->second;
        const auto names=registry_names_.find(registry_paths_[index]);
        if(names==registry_names_.end())return {};
        std::string package,asset;
        if(!registry_name(b,names->second.first,package)||!registry_name(b,names->second.second,asset)||package+"."+asset!=registry_paths_[index])return {};
        clear();put(8,names->second.first);put(16,names->second.second);
        if(!call(b,ids_[5],61))return {};
        const auto mesh=call_capture(b,get<uint64_t>(40));
        if(!call_identity(b,mesh)||!call_derives(b,local_read<uint64_t>(mesh.address+16),ids_[85].address))return {};
        bulk_meshes_[index]=mesh;return mesh;
    }
    bool bulk_bounds(uint64_t b,CallIdentity actor,double* center,double* extent) {
        clear();args_[56]=1;if(!call(b,actor,25))return false;
        std::memcpy(center,args_+8,24);std::memcpy(extent,args_+32,24);
        for(int j=0;j<3;++j)if(!std::isfinite(center[j])||!std::isfinite(extent[j])||extent[j]<0||extent[j]>1.e6)return false;
        return true;
    }
    bool gallery_floor_size(uint64_t b) {
        if(!call_identity(b,gallery_floor_component_))return false;
        const double width=std::max(100.,gallery_max_y_+100.),span_x=std::max(100.,gallery_max_x_+100.);
        const double pose[]={0,0,0,1,gallery_origin_[0]+span_x/2-50,gallery_origin_[1]+width/2-50,gallery_origin_[2]-10,0,span_x/100,width/100,.2,0};
        if(!valid_pose(reinterpret_cast<const uint8_t*>(pose)))return false;
        return component_pose(b,gallery_floor_component_,reinterpret_cast<const uint8_t*>(pose));
    }
    template<class Pool> bool gallery_begin(uint64_t b,uint64_t session,Pool& pool,const double* settings) {
        if(gallery_floor_.address&&call_identity(b,gallery_floor_))return false;
        for(int j=0;j<8;++j)if(!std::isfinite(settings[j]))return false;
        for(int j=0;j<3;++j)if(std::abs(settings[j])>1.e7)return false;
        if(settings[3]<50||settings[3]>10000||settings[4]<0||settings[4]>1||settings[5]<1||settings[5]>100||settings[6]!=0||settings[7]!=0)return false;
        std::memcpy(gallery_origin_,settings,24);gallery_spacing_=settings[3];gallery_tight_=settings[4]!=0;gallery_columns_=uint32_t(settings[5]);
        gallery_width_=std::max(3000.,gallery_spacing_*gallery_columns_);gallery_x_=gallery_y_=gallery_depth_=0;gallery_max_x_=gallery_max_y_=100;gallery_count_=0;
        const double pose[]={0,0,0,1,settings[0],settings[1],settings[2]-10,0,1,1,.2,0};
        if(!spawn_asset(b,session,pool,ids_[88],ids_[84],reinterpret_cast<const uint8_t*>(pose),gallery_floor_,gallery_floor_component_))return false;
        candidates_.erase(std::remove_if(candidates_.begin(),candidates_.end(),[&](const Candidate& c){return c.component.address==gallery_floor_component_.address;}),candidates_.end());
        if(gallery_floor_size(b))return true;
        clear_spawned(b,session,pool,gallery_floor_);return false;
    }
    bool gallery_place(uint64_t b,CallIdentity actor,CallIdentity component,double* pose,double* center,double* extent) {
        uint32_t error=0;
            if(!error){
                // A catalog includes entire landscape backdrops. Fit only
                // gallery exhibits to the selected cell size, never map rows.
                const double span=2*std::max({extent[0],extent[1],extent[2]});
                if(span>gallery_spacing_){
                    const double factor=gallery_spacing_/span;
                    for(int j=8;j<11;++j)pose[j]*=factor;
                    if(!valid_pose(reinterpret_cast<const uint8_t*>(pose))||!component_pose(b,component,reinterpret_cast<const uint8_t*>(pose))||!bulk_bounds(b,actor,center,extent))error=1954;
                }
            }
            if(!error){
                const double old_x=gallery_x_,old_y=gallery_y_,old_depth=gallery_depth_;
                const double width=std::max(50.,extent[1]*2),span_x=std::max(50.,extent[0]*2);
                double x=0,y=0;
                if(gallery_tight_){if(gallery_y_&&gallery_y_+width>gallery_width_){gallery_x_+=gallery_depth_+50;gallery_y_=gallery_depth_=0;}x=gallery_x_;y=gallery_y_;gallery_y_+=width+50;gallery_depth_=std::max(gallery_depth_,span_x);}
                else {x=(gallery_count_/gallery_columns_)*gallery_spacing_;y=(gallery_count_%gallery_columns_)*gallery_spacing_;}
                const double center_target[]={gallery_origin_[0]+x+span_x/2,gallery_origin_[1]+y+width/2,gallery_origin_[2]+extent[2]};
                for(int j=0;j<3;++j){pose[4+j]+=center_target[j]-center[j];center[j]=center_target[j];}
                if(x+span_x>999800||y+width>999800||!valid_pose(reinterpret_cast<const uint8_t*>(pose))||!component_pose(b,component,reinterpret_cast<const uint8_t*>(pose)))error=1954;
                else {refresh_candidate(b,component);gallery_max_x_=std::max(gallery_max_x_,x+span_x);gallery_max_y_=std::max(gallery_max_y_,y+width);++gallery_count_;}
                if(error){gallery_x_=old_x;gallery_y_=old_y;gallery_depth_=old_depth;}
            }
        return error==0;
    }
    template<class Pool> bool bulk_spawn(uint64_t b,uint64_t session,Pool& pool,uint8_t* raw) {
        uint32_t count=0;std::memcpy(&count,raw+2000,4);if(!count||count>64)return false;
        // Validate all rows before any creation; rows use registry indices,
        // not caller pointers or names supplied to the engine.
        for(uint32_t i=0;i<count;++i){const auto* row=raw+4096+i*192;uint32_t index=0,flags=0;std::memcpy(&index,row,4);std::memcpy(&flags,row+4,4);
            if(flags>1||!valid_pose(row+8)||(index!=0xffffffffU&&(!registry_complete_||index>=registry_paths_.size()))||(flags&&!call_identity(b,gallery_floor_)))return false;}
        const auto begin=std::chrono::steady_clock::now();uint32_t processed=0,successes=0;bool gallery=false;
        for(;processed<count;++processed){auto* row=raw+4096+processed*192;uint32_t index=0,flags=0;std::memcpy(&index,row,4);std::memcpy(&flags,row+4,4);double pose[12];std::memcpy(pose,row+8,96);
            std::memset(row,0,192);uint32_t error=0;CallIdentity actor{},component{};double center[3]{},extent[3]{};
            const auto before=spawned_.size();const auto mesh=bulk_mesh(b,index);
            if(!mesh.address)error=1951;
            else if(!spawn_asset(b,session,pool,mesh,ids_[84],reinterpret_cast<const uint8_t*>(pose),actor,component))error=1952;
            else if(!bulk_bounds(b,actor,center,extent))error=1953;
            if(!error&&flags){if(!gallery_place(b,actor,component,pose,center,extent))error=1954;else gallery=true;}
            if(error){if(spawned_.size()>before&&!clear_spawned(b,session,pool,spawned_.back().actor))return false;}
            else {++successes;std::memcpy(row+8,&actor,16);std::memcpy(row+24,&component,16);std::memcpy(row+40,pose,96);std::memcpy(row+136,center,24);std::memcpy(row+160,extent,24);}
            std::memcpy(row,&error,4);
            if(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count()>=4){++processed;break;}
        }
        if(gallery&&!gallery_floor_size(b))return false;
        const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
        std::memcpy(raw+3560,&processed,4);std::memcpy(raw+3564,&successes,4);std::memcpy(raw+3568,&ms,8);return true;
    }
    template<class Pool> bool bulk_delete(uint64_t b,uint64_t session,Pool& pool,uint8_t* raw) {
        uint32_t count=0;std::memcpy(&count,raw+2000,4);if(!count||count>128)return false;
        const auto begin=std::chrono::steady_clock::now();uint32_t done=0;
        for(;done<count;++done){CallIdentity actor{};std::memcpy(&actor,raw+4096+done*16,16);
            if(!actor.address)return false;
            const bool floor=actor.address==gallery_floor_.address&&actor.serial==gallery_floor_.serial;
            if(!clear_spawned(b,session,pool,actor))return false;
            if(floor){gallery_floor_={};gallery_floor_component_={};}
            if(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count()>=4){++done;break;}}
        std::memcpy(raw+3560,&done,4);return true;
    }
    bool gallery_existing(uint64_t b,uint8_t* raw) {
        CallIdentity actor{};std::memcpy(&actor,raw+88,16);
        const auto found=std::find_if(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.actor.address==actor.address&&row.actor.serial==actor.serial;});
        if(found==spawned_.end()||actor.address==gallery_floor_.address||!call_identity(b,gallery_floor_))return false;
        const auto component=found->component;double pose[12],center[3],extent[3];
        clear();if(!call(b,component,19))return false;std::memcpy(pose,args_,96);
        if(!bulk_bounds(b,actor,center,extent)||!gallery_place(b,actor,component,pose,center,extent)||!gallery_floor_size(b))return false;
        std::memcpy(raw+4096+40,pose,96);std::memcpy(raw+4096+136,center,24);std::memcpy(raw+4096+160,extent,24);return true;
    }
