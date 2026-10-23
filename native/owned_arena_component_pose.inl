    template<class Pool> uint32_t set_owned_component_pose(uint64_t b,uint64_t session,Pool& pool,
            const CallIdentity (&query)[3],const double* requested,e33_component_pose::Report& report,bool helper_pose=false){
        if(trigger_anchor_)return 3650;
        const bool route=helper_pose?(!arena_staging_&&preparing_world_&&!placement_attempted_&&!grounded_&&
            visual_class(b)&&helper_entry_.phase()==HelperEntryPhase::Empty&&
            construction_.phase==e33_owned_actor::ConstructionPhase::Complete):arena_staging_;
        if(!route||arena_ground_attempted_||!owner_||!lease_||!current(b,true)||!helper_battle_quiescent(b)||
           !call_identity(b,actor_)||!pool.owns_object(session,lease_,actor_.address)||
           !(helper_pose?e33_component_pose::scaled(requested):e33_component_pose::rigid(requested)))return 3604;
        auto inert=[&](){
            uint64_t hdesc=0,cdesc=0;
            const auto h=picto_field(b,actor_.address,"bHidden","BoolProperty",88,1,&hdesc);
            const auto c=picto_field(b,actor_.address,"bActorEnableCollision","BoolProperty",92,1,&cdesc);
            return h&&c&&hdesc&&cdesc&&local_read<uint32_t>(hdesc+0x70)==0x80800001U&&
                local_read<uint32_t>(cdesc+0x70)==0x80800001U&&(local_read<uint8_t>(h)&0x80)&&!(local_read<uint8_t>(c)&0x80);
        };
        if(helper_pose&&!inert())return 3604;
        const auto component=call_identity(b,query[0]);
        const auto root=arena_reference(b,actor_.address,"RootComponent",416);
        if(helper_pose&&(!root||!arena_scene(b,root,actor_.address)))return 3604;
        const auto parent_at=component?picto_field(b,component,"AttachParent","ObjectProperty",176,8):0;
        const auto parent=parent_at?local_read<uint64_t>(parent_at):0;
        if(!component||component==root||local_read<uint64_t>(component+32)!=actor_.address||
           !arena_scene(b,component,actor_.address)||!parent||
           !arena_scene(b,parent,actor_.address))return 3604;
        CallIdentity* reserved=nullptr;
        for(auto& component_target:component_pose_targets_){
            if(component_target.address==component)return 3605;
            if(!reserved&&!component_target.address)reserved=&component_target;
        }
        if(!reserved)return 3605;
        std::memset(args_,0,sizeof(args_));
        if(!e33_engine_profile_call::invoke(b,query[2],query[0],e33_component_transform::get_relative,args_))return 3607;
        std::memcpy(report.before,args_,96);report.before[7]=report.before[11]=0;
        if(!(helper_pose?e33_component_pose::preserves_scale(report.before,requested):e33_component_pose::rigid(report.before)))return 3606;
        // Persist before any setter dispatch. Failed/unknown writes are never
        // replayed; destruction of this owned arena is the rollback boundary.
        *reserved=query[0];report.attempted=1;
        std::memset(args_,0,sizeof(args_));std::memcpy(args_,requested,96);args_[352]=1;
        if(!e33_engine_profile_call::invoke(b,query[1],query[0],e33_component_transform::set_relative,args_))return 3608;
        report.acknowledged=1;
        if(!current(b,true)||!call_identity(b,query[0])||(helper_pose&&!inert())||
           local_read<uint64_t>(component+32)!=actor_.address||
           local_read<uint64_t>(parent_at)!=parent)return 3609;
        std::memset(args_,0,sizeof(args_));
        if(!e33_engine_profile_call::invoke(b,query[2],query[0],e33_component_transform::get_relative,args_))return 3609;
        std::memcpy(report.after,args_,96);report.after[7]=report.after[11]=0;report.readback=1;
        if(!(helper_pose?e33_component_pose::same_scaled(report.after,requested):e33_component_pose::same(report.after,requested)))return 3609;
        report.verified=1;return 0;
    }
