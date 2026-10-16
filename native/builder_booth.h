
    bool booth_active_=false,booth_lamp_was_=false;
    CallIdentity booth_prop_{};std::vector<CallIdentity> booth_owned_,booth_lights_;
    double booth_return_[6]{},booth_center_[3]{},booth_rotation_[3]{},booth_distance_=1000,booth_radius_=100,booth_room_=2000;
    int booth_lighting_=0;
    bool booth_light(uint64_t b) {
        const float levels[]={8.f,24.f,0.f};const float powers[]={1.f,.45f,.7f};
        for(size_t i=0;i<booth_lights_.size();++i){clear();put(0,levels[booth_lighting_]*powers[i%3]);if(!call(b,booth_lights_[i],54))return false;}return true;
    }
    bool booth_motion(uint64_t b,double yaw,double pitch,double zoom,double rx,double ry,double rz,bool lighting) {
        if(!call_identity(b,booth_prop_))return false;
        rotation_[0]=std::clamp(rotation_[0]+pitch,-85.,85.);rotation_[1]=std::remainder(rotation_[1]+yaw,360.);rotation_[2]=0;
        booth_distance_=std::clamp(booth_distance_*std::exp(zoom),booth_radius_*.35,booth_room_*.82);
        for(int j=0;j<3;++j)booth_rotation_[j]=std::remainder(booth_rotation_[j]+(j==0?rx:j==1?ry:rz),360.);
        if(rx||ry||rz){clear();if(!call(b,booth_prop_,3))return false;double pos[3];std::memcpy(pos,args_,24);
            clear();std::memcpy(args_,pos,24);std::memcpy(args_+24,booth_rotation_,24);args_[304]=1;if(!call(b,booth_prop_,5)||!args_[305])return false;}
        const double p=rotation_[0]*3.141592653589793/180.,y=rotation_[1]*3.141592653589793/180.;
        const double forward[]={std::cos(p)*std::cos(y),std::cos(p)*std::sin(y),std::sin(p)};
        for(int j=0;j<3;++j)position_[j]=booth_center_[j]-forward[j]*booth_distance_;
        clear();std::memcpy(args_,rotation_,24);if(!call(b,ids_[0],23)||!camera_pose(b))return false;
        if(lighting){booth_lighting_=(booth_lighting_+1)%3;if(!booth_light(b))return false;}
        if(ids_[48].address){if(!visibility(b,ids_[48],true)||!label(b,"PREVIEW | Mouse orbit | W/S zoom | Numpad 8/2 pitch, 7/1 yaw, 9/3 roll | L lights | Esc return"))return false;}
        return true;
    }
    template<class Pool> bool booth_end(uint64_t b,uint64_t session,Pool& pool) {
        while(!booth_owned_.empty()){if(!clear_spawned(b,session,pool,booth_owned_.back()))return false;booth_owned_.pop_back();}
        booth_lights_.clear();
        if(booth_active_){std::memcpy(position_,booth_return_,24);std::memcpy(rotation_,booth_return_+3,24);
            clear();std::memcpy(args_,rotation_,24);if(!call(b,ids_[0],23)||!camera_pose(b))return false;}
        booth_active_=false;booth_prop_={};left_was_=true;return true;
    }
    template<class Pool> bool booth_begin(uint64_t b,uint64_t session,Pool& pool,CallIdentity actor) {
        if(booth_active_||!booth_owned_.empty()||!call_identity(b,actor))return false;
        const auto it=std::find_if(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.actor.address==actor.address&&row.actor.serial==actor.serial;});
        if(it==spawned_.end())return false;
        std::memcpy(booth_return_,position_,24);std::memcpy(booth_return_+3,rotation_,24);booth_prop_=actor;booth_active_=true;
        clear();if(!call(b,actor,47))return false;clear();if(!call(b,actor,58))return false;
        // Configure every primitive owned by this disposable actor, including
        // Blueprint children. Never touch components belonging to the level.
        const auto objectCount=local_read<int32_t>(b+0x9361b84);const auto chunks=local_read<uint64_t>(b+0x9361b70);
        if(objectCount<1||objectCount>4000000||!chunks)return false;
        int configured=0;
        for(int index=0;index<objectCount;++index){const auto chunk=local_read<uint64_t>(chunks+uint64_t(index>>16)*8);if(!chunk)continue;
            const auto object=local_read<uint64_t>(chunk+uint64_t(index&65535)*24);
            if(!object||local_read<uint64_t>(object+32)!=actor.address||(local_read<uint32_t>(object+8)&0x30)||!call_derives(b,local_read<uint64_t>(object+16),ids_[89].address))continue;
            if(++configured>256)return false;auto primitive=call_capture(b,object);clear();if(!call(b,primitive,18)||get<uint64_t>()!=actor.address)return false;
            clear();if(!call(b,primitive,59))return false;clear();args_[0]=2;if(!call(b,primitive,16))return false;
            clear();args_[1]=1;if(!call(b,primitive,52))return false;
        }
        clear();args_[56]=1;if(!call(b,actor,25))return false;std::memcpy(booth_center_,args_+8,24);
        booth_radius_=std::max(100.,std::sqrt(get<double>(32)*get<double>(32)+get<double>(40)*get<double>(40)+get<double>(48)*get<double>(48)));
        if(booth_radius_>50000)return false;booth_room_=std::max(2000.,booth_radius_*6.);booth_distance_=booth_radius_*2.8;
        std::fill(std::begin(booth_rotation_),std::end(booth_rotation_),0.);booth_lighting_=0;
        for(int axis=0;axis<3;++axis)for(int side=-1;side<=1;side+=2){
            double pos[3];std::memcpy(pos,booth_center_,24);pos[axis]+=side*booth_room_;uint8_t pose[96]{};transform(pose,pos);
            double scale[3]={booth_room_*2.2/100.,booth_room_*2.2/100.,booth_room_*2.2/100.};scale[axis]=2.;std::memcpy(pose+64,scale,24);
            CallIdentity wall{},root{};if(!spawn_asset(b,session,pool,ids_[88],ids_[84],pose,wall,root))return false;booth_owned_.push_back(wall);
            clear();if(!call(b,wall,47))return false;clear();args_[1]=1;if(!call(b,root,52))return false;
        }
        const double offsets[3][3]={{-.65,-.45,.65},{.6,.5,.3},{-.2,.65,.7}};
        for(int i=0;i<3;++i){double pos[3];for(int j=0;j<3;++j)pos[j]=booth_center_[j]+offsets[i][j]*booth_room_;uint8_t pose[96]{};transform(pose,pos);
            CallIdentity lamp{},root{};if(!spawn_asset(b,session,pool,{},ids_[87],pose,lamp,root))return false;booth_owned_.push_back(lamp);booth_lights_.push_back(root);
            clear();args_[1]=1;if(!call(b,root,53))return false;clear();const float white[]={1,1,1,1};std::memcpy(args_,white,16);if(!call(b,root,55))return false;
            clear();if(!call(b,root,57))return false;clear();put(0,float(booth_room_*4));if(!call(b,root,56))return false;
        }
        rotation_[0]=-15.;rotation_[1]=30.;rotation_[2]=0;dragging_=false;selected_={};hover_={};
        if(!glow(b,session,pool,{})||!booth_light(b))return false;
        return booth_motion(b,0,0,0,0,0,0,false);
    }
    template<class Pool> bool map_capture(uint64_t b,uint64_t session,Pool& pool) {
        if(!active_||booth_active_)return false;
        double pos[3]={position_[0],position_[1],position_[2]+100000};uint8_t pose[96]{};transform(pose,pos);
        CallIdentity helper{},component{},image{};
        if(!spawn_asset(b,session,pool,ids_[88],ids_[84],pose,helper,component))return false;
        const bool ready=preview(b,session,pool,helper,image);
        if(!clear_spawned(b,session,pool,helper)||!ready)return false;
        float mapFov=90.f;uint32_t mapFovBits;std::memcpy(&mapFovBits,&mapFov,4);
        if(!preview_setting(b,"FOVAngle",mapFovBits)||!preview_setting(b,"PrimitiveRenderMode",0)||!preview_setting(b,"CaptureSource",2))return false;
        clear();if(!call(b,preview_capture_,43))return false;
        clear();std::memcpy(args_,position_,24);std::memcpy(args_+24,rotation_,24);args_[304]=1;if(!call(b,preview_actor_,5)||!args_[305])return false;
        clear();return call(b,preview_capture_,41);
    }
