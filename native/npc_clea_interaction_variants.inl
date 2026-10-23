// Included inside CleaOwner public section. Only the owned NPC is modified.
    template<class Pool> uint32_t enable_solid_collision(uint64_t base,uint64_t session,Pool& pool,const CallIdentity (&query)[4]){
        using namespace e33_npc_interaction;
        if(collision_variant_.attempted)return 3501;
        uint64_t name=0;
        if(!owned_parameter_instance_name(base,session,pool,state_.actor,name)||!reveal_.visible)return 3500;
        const auto field=picto_field(base,state_.actor.address,"CapsuleComponent","ObjectProperty",808,8);
        const auto root=field?call_capture(base,local_read<uint64_t>(field)):CallIdentity{};
        if(!call_identity(base,root)||local_read<uint64_t>(root.address+32)!=state_.actor.address||
           !e33_mesh::named(base,local_read<uint64_t>(root.address+16),"CapsuleComponent","/Script/Engine"))return 3500;
        collision_variant_.attempted=1;
        auto call=[&](unsigned i,const MeshFunction& profile,uint8_t* frame){
            Guard<Pool> guard{*this,base,session,pool};Ops<Pool> ops(base,*this,session,pool,guard);
            return ops.exact_owned_actor()&&guard.battle_quiescent()&&e33_engine_profile_call::invoke(base,query[i],root,profile,frame);
        };
        alignas(16) uint8_t frame[464]{};
        if(!call(1,GetCollisionEnabled,frame))return 3502;
        collision_variant_.before_mode=frame[0];std::memset(frame,0,sizeof(frame));frame[0]=2; // ECC_Pawn
        if(!call(3,GetCollisionResponseToChannel,frame))return 3502;
        collision_variant_.before_response=frame[1];std::memset(frame,0,sizeof(frame));frame[0]=3; // QueryAndPhysics
        if(!call(0,SetCollisionEnabled,frame))return 3502;
        std::memset(frame,0,sizeof(frame));frame[0]=2;frame[1]=2; // Pawn -> Block
        if(!call(2,SetCollisionResponseToChannel,frame))return 3502;
        std::memset(frame,0,sizeof(frame));frame[0]=1;
        if(!e33_engine_profile_call::invoke(base,source_.collision,state_.actor,e33_engine_profiles::profiles[47],frame))return 3502;
        collision_variant_.acknowledged=1;
        std::memset(frame,0,sizeof(frame));if(!call(1,GetCollisionEnabled,frame))return 3503;
        collision_variant_.mode=frame[0];std::memset(frame,0,sizeof(frame));frame[0]=2;
        if(!call(3,GetCollisionResponseToChannel,frame))return 3503;
        collision_variant_.response=frame[1];
        const auto enabled=component_field(base,state_.actor.address,"bActorEnableCollision","BoolProperty",92,1,"Actor",0x6e119b0,0x48001000000000ULL);
        collision_variant_.actor_enabled=enabled&&(local_read<uint8_t>(enabled)&0x80)?1:0;
        collision_variant_.verified=collision_variant_.mode==3&&collision_variant_.response==2&&collision_variant_.actor_enabled;
        return collision_variant_.verified?0:3503;
    }
    template<class Pool> uint32_t observe_overlap(uint64_t base,uint64_t session,Pool& pool,const CallIdentity (&query)[11],uint32_t& overlaps){
        overlaps=0;if(!collision_variant_.verified)return 3504;
        CallIdentity poses[10]{};std::memcpy(poses,query,sizeof(poses));double positions[7]{};
        if(observe_proximity(base,session,pool,poses,positions))return 3504;
        const auto field=picto_field(base,query[0].address,"CapsuleComponent","ObjectProperty",808,8);
        const auto capsule=field?call_capture(base,local_read<uint64_t>(field)):CallIdentity{};
        if(!call_identity(base,capsule)||local_read<uint64_t>(capsule.address+32)!=query[0].address)return 3504;
        alignas(16) uint8_t frame[464]{};std::memcpy(frame,positions+4,24);
        const float radius=180;std::memcpy(frame+24,&radius,4);
        if(!e33_engine_profile_call::invoke(base,query[10],capsule,e33_npc_interaction::K2_SphereOverlapComponent,frame)||frame[336]>1)return 3504;
        overlaps=frame[336];return 0;
    }
