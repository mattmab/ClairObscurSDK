// Included in owned-enemy Owner; reuses WorldBuilder profiles and shared queries.
    bool hold_prepared(uint64_t b){
        if(!movement_.address){
            const auto value=arena_reference(b,actor_.address,"CharacterMovement",800);
            if(!arena_class(b,value,"CharacterMovementComponent","/Script/Engine")||local_read<uint64_t>(value+32)!=actor_.address)return false;
            const auto mode=picto_field(b,value,"MovementMode","ByteProperty",513,1);
            const auto custom=picto_field(b,value,"CustomMovementMode","ByteProperty",514,1);
            if(!mode||!custom||local_read<uint8_t>(mode)>6)return false;
            movement_=call_capture(b,value);movement_mode_=local_read<uint8_t>(mode);movement_custom_=local_read<uint8_t>(custom);
        }
        std::memset(args_,0,sizeof(args_));return call(b,10,movement_function_,movement_);
    }
    bool hide_prepared(uint64_t b){
        std::memset(args_,0,sizeof(args_));if(!call(b,47,ids_[9],actor_))return false;
        std::memset(args_,0,sizeof(args_));if(!call(b,58,ids_[10],actor_))return false;
        std::memset(args_,0,sizeof(args_));args_[0]=1;return call(b,100,ids_[11],actor_);
    }
    bool release_prepared(uint64_t b){
        if(!grounded_||!arena_binding_state_.verified||!call_identity(b,movement_))return false;
        std::memset(args_,0,sizeof(args_));args_[0]=movement_mode_;args_[1]=movement_custom_;
        if(!call(b,10,movement_function_,movement_))return false;
        std::memset(args_,0,sizeof(args_));args_[0]=1;if(!call(b,47,ids_[9],actor_))return false;
        std::memset(args_,0,sizeof(args_));args_[0]=1;if(!call(b,58,ids_[10],actor_))return false;
        std::memset(args_,0,sizeof(args_));return call(b,100,ids_[11],actor_);
    }
    uint32_t place_grounded(uint64_t b,const CallIdentity* query,double* output){
        if(!hold_prepared(b)||!hide_prepared(b))return 2970;
        if(!named(b,query[0].address,"Default__KismetSystemLibrary","/Script/Engine"))return 2970;
        const auto capsule=arena_reference(b,actor_.address,"CapsuleComponent",808);
        const auto mesh=arena_reference(b,actor_.address,"Mesh",792);
        const auto player_capsule=arena_reference(b,ids_[1].address,"CapsuleComponent",808);
        if(!arena_class(b,capsule,"CapsuleComponent","/Script/Engine")||local_read<uint64_t>(capsule+32)!=actor_.address||
           !arena_class(b,mesh,"SkeletalMeshComponent","/Script/Engine")||local_read<uint64_t>(mesh+32)!=actor_.address||
           !arena_class(b,player_capsule,"CapsuleComponent","/Script/Engine")||local_read<uint64_t>(player_capsule+32)!=ids_[1].address)return 2970;
        if(arena_reference(b,actor_.address,"RootComponent",416)!=capsule)return 2970;
        uint64_t initial_descriptor=0;
        const auto initial=picto_field(b,actor_.address,"InitialTransform","StructProperty",2976,96,&initial_descriptor);
        if(!initial||!initial_descriptor||!e33_mesh::structure(b,local_read<uint64_t>(initial_descriptor+0x70),"Transform",96))return 2970;
        double centers[3][3]{},extents[3][3]{},old[3]{},rotation[3]{},facing[3]{};
        const uint64_t components[]={capsule,mesh,player_capsule};
        for(unsigned i=0;i<3;++i){
            std::memset(args_,0,sizeof(args_));put(0,components[i]);
            if(!call(b,64,query[3],query[0]))return 2970;
            std::memcpy(centers[i],args_+8,24);std::memcpy(extents[i],args_+32,24);
            for(unsigned j=0;j<3;++j)if(!std::isfinite(centers[i][j])||std::abs(centers[i][j])>1.e7||
                !std::isfinite(extents[i][j])||extents[i][j]<=0||extents[i][j]>1.e5)return 2971;
        }
        std::memset(args_,0,sizeof(args_));if(!call(b,3,query[4],actor_))return 2970;std::memcpy(old,args_,24);
        std::memset(args_,0,sizeof(args_));if(!call(b,4,query[5],actor_))return 2970;std::memcpy(rotation,args_,24);
        std::memset(args_,0,sizeof(args_));if(!call(b,4,query[5],ids_[1]))return 2970;std::memcpy(facing,args_,24);
        for(unsigned i=0;i<3;++i)if(!std::isfinite(old[i])||!std::isfinite(rotation[i])||!std::isfinite(facing[i]))return 2971;
        const auto radius=std::max(std::hypot(extents[0][0],extents[0][1]),
            std::hypot(extents[1][0],extents[1][1])+std::hypot(centers[1][0]-centers[0][0],centers[1][1]-centers[0][1]));
        const auto distance=std::max(1600.,radius+std::hypot(extents[2][0],extents[2][1])+500.);
        if(!std::isfinite(distance)||distance>200000.)return 2971;
        const auto yaw=facing[1]*3.14159265358979323846/180.;
        const double target_xy[]={centers[2][0]+std::cos(yaw)*distance,centers[2][1]+std::sin(yaw)*distance};
        const uint64_t ignored[]={actor_.address,ids_[1].address};double maximum=-1.e8,minimum=1.e8;
        for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x){
            const double start[]={target_xy[0]+x*extents[0][0],target_xy[1]+y*extents[0][1],centers[2][2]+5000.};
            const double end[]={start[0],start[1],centers[2][2]-10000.};e33_surface_query::Sample sample{};
            const auto result=e33_surface_query::sample([&](unsigned stage,uint8_t* frame){
                std::memcpy(args_,frame,sizeof(args_));
                const bool ok=stage?call(b,15,query[2],ids_[3]):call(b,14,query[1],query[0]);
                std::memcpy(frame,args_,sizeof(args_));return ok;
            },ids_[2].address,start,end,ignored,2,sample);
            if(result!=e33_surface_query::Result::Hit)return 2972;
            maximum=std::max(maximum,sample.point[2]);minimum=std::min(minimum,sample.point[2]);
        }
        if(maximum-minimum>100.)return 2973;
        const double target_center[]={target_xy[0],target_xy[1],maximum+extents[0][2]+15.};
        const auto clearance=e33_volume_query::sample([&](uint8_t* frame){
            std::memcpy(args_,frame,sizeof(args_));const bool ok=call(b,101,query[7],query[0]);
            std::memcpy(frame,args_,sizeof(args_));return ok;
        },ids_[2].address,target_center,extents[0],ignored,2);
        if(clearance!=e33_volume_query::Result::Clear)return 2974;
        double destination[3]{};
        for(unsigned i=0;i<3;++i){destination[i]=old[i]+target_center[i]-centers[0][i];if(!std::isfinite(destination[i])||std::abs(destination[i])>1.e7)return 2971;}
        placement_attempted_=true;
        std::memset(args_,0,sizeof(args_));std::memcpy(args_,destination,24);std::memcpy(args_+24,rotation,24);args_[304]=1;
        if(!call(b,5,query[6],actor_)||!args_[305])return 2975;
        std::memset(args_,0,sizeof(args_));put(0,capsule);if(!call(b,64,query[3],query[0]))return 2975;
        double checked[3]{};std::memcpy(checked,args_+8,24);
        for(unsigned i=0;i<3;++i)if(!std::isfinite(checked[i])||std::abs(checked[i]-target_center[i])>.1)return 2975;
        // Original OnEnemyBattleStateLoaded/ResetState restores this owned
        // BeginPlay cache. Rebase it to the verified placement, not staging.
        std::memset(args_,0,sizeof(args_));
        if(!call(b,19,query[8],call_capture(b,capsule)))return 2975;
        double transform[12]{};std::memcpy(transform,args_,96);double norm=0;
        for(unsigned i=0;i<4;++i){if(!std::isfinite(transform[i]))return 2975;norm+=transform[i]*transform[i];}
        if(norm<.999||norm>1.001)return 2975;
        for(unsigned i=0;i<3;++i)if(!std::isfinite(transform[4+i])||std::abs(transform[4+i]-destination[i])>.1||
            !std::isfinite(transform[8+i])||std::abs(transform[8+i])<1.e-9||std::abs(transform[8+i])>1.e5)return 2975;
        std::memcpy(reinterpret_cast<void*>(initial),args_,96);
        grounded_=true;
        std::memcpy(output,destination,24);std::memcpy(output+3,old,24);
        for(unsigned i=0;i<3;++i){std::memcpy(output+6+i*6,centers[i],24);std::memcpy(output+9+i*6,extents[i],24);}
        output[24]=maximum;output[25]=minimum;output[26]=radius;output[27]=distance;output[28]=9;output[29]=1;
        return 0;
    }
