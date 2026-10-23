    template<class Pool> uint32_t qualify_owned_helper(uint64_t b,uint64_t session,Pool& pool,Owner& helper,
            const CallIdentity (&query)[4],const double* relative,HelperSourceFrameReport& report){
        const bool paintress_source=named(b,helper.ids_[4].address,"BP_DummyEnemy_Paintress_C",
            "/Game/Characters/Enemies/HumanEnnemies/Aline/BP_DummyEnemy_Paintress");
        if(!arena_staging_||!owner_||!lease_||!arena_grounded_||!arena_ground_journal_.readback||
           !current(b,true)||!helper_battle_quiescent(b)||!call_identity(b,actor_)||
           !pool.owns_object(session,lease_,actor_.address)||!helper_relative_frame(relative,paintress_source)||
           helper.arena_staging_||!helper.visual_class(b)||!helper.preparing_world_||helper.placement_attempted_||helper.grounded_||
           helper.construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
           !helper.owner_||!helper.lease_||!helper.current(b,true)||!helper.helper_battle_quiescent(b)||
           !call_identity(b,helper.actor_)||!arena_live(b,helper.actor_.address)||
           !pool.owns_object(session,helper.lease_,helper.actor_.address)||
           query[0].index!=helper.actor_.index||query[0].serial!=helper.actor_.serial||query[0].address!=helper.actor_.address||
           helper.ids_[2].address!=ids_[2].address||helper.ids_[0].address!=ids_[0].address||
           !helper.arena_binding_state_.verified)return 3620;
        const auto bound=helper.arena_binding_.observed_arena();
        if(bound.index!=actor_.index||bound.serial!=actor_.serial||bound.address!=actor_.address||
           !helper.arena_binding_.preflight())return 3620;
        auto root_frame=[&](Owner& who,double* pose){
            const auto root=arena_reference(b,who.actor_.address,"RootComponent",416);
            const auto parent=root?picto_field(b,root,"AttachParent","ObjectProperty",176,8):0;
            if(!root||!parent||local_read<uint64_t>(parent)||!arena_scene(b,root,who.actor_.address))return false;
            std::memset(args_,0,sizeof(args_));if(!call(b,19,query[1],call_capture(b,root)))return false;
            std::memcpy(pose,args_,96);pose[7]=pose[11]=0;return unit_yaw_frame(pose,1.e7);
        };
        auto frame_ready=[&](){
            if(!current(b,true)||!helper.current(b,true)||!helper_battle_quiescent(b)||
               !root_frame(*this,report.arena)||!root_frame(helper,report.helper))return false;
            for(unsigned i=0;i<3;++i)if(std::abs(report.arena[4+i]-arena_ground_journal_.after.location[i])>.1)return false;
            std::memset(args_,0,sizeof(args_));if(!call(b,4,query[2],actor_))return false;
            double angles[3]{};std::memcpy(angles,args_,24);
            if(!e33_actor_pose::same_rotation(angles,arena_ground_journal_.after.rotation,.001))return false;
            return compose_helper_source_frame(report.arena,relative,report.expected,paintress_source)&&same_helper_world_frame(report.helper,report.expected);
        };
        auto exact_lookup=[&](){
            std::memset(helper.args_,0,sizeof(helper.args_));helper.put(0,helper.ids_[2].address);helper.put(8,helper.ids_[4].address);
            return helper.call(b,102,query[3],helper.ids_[3])&&
                local_read<uint64_t>(reinterpret_cast<uint64_t>(helper.args_+16))==helper.actor_.address;
        };
        auto flags=[&](bool hidden){
            uint64_t hdesc=0,cdesc=0;
            const auto h=picto_field(b,helper.actor_.address,"bHidden","BoolProperty",88,1,&hdesc);
            const auto c=picto_field(b,helper.actor_.address,"bActorEnableCollision","BoolProperty",92,1,&cdesc);
            return h&&hdesc&&c&&cdesc&&local_read<uint32_t>(hdesc+0x70)==0x80800001U&&
                local_read<uint32_t>(cdesc+0x70)==0x80800001U&&bool(local_read<uint8_t>(h)&0x80)==hidden&&!(local_read<uint8_t>(c)&0x80);
        };
        if(!frame_ready()||!exact_lookup()||!flags(true))return 3621;
        // No Python-written grounded flag: record the one-shot native reveal
        // intent only after both owned frames and arena receipt revalidate.
        helper.placement_attempted_=true;report.attempted=1;
        std::memset(helper.args_,0,sizeof(helper.args_));helper.args_[0]=1;
        if(!helper.call(b,58,helper.ids_[10],helper.actor_))return 3622;report.tick_acknowledged=1;
        std::memset(helper.args_,0,sizeof(helper.args_));
        if(!helper.call(b,100,helper.ids_[11],helper.actor_))return 3622;report.visibility_acknowledged=1;
        if(!frame_ready()||!exact_lookup()||!flags(false))return 3623;
        helper.grounded_=true;report.verified=1;return 0;
    }
