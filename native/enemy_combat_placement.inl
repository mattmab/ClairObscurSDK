    struct CombatPlacement {
        CallIdentity actor{};
        e33_actor_pose::Placement pose;
        bool home_dispatched=false,home_acknowledged=false,home_verified=false;
    } combat_placements_[7]{};

    bool combat_placement_context(uint64_t b,const CallIdentity (&query)[7],int32_t& slot){
        if(!owner_||!initialized_||!arena_binding_state_.verified||!source_current(b))return false;
        for(const auto& id:query)if(!call_identity(b,id))return false;
        const auto manager=query[0].address,combatant=query[1].address,movement=query[2].address;
        const auto arena=arena_binding_.observed_arena();
        if(!call_identity(b,actor_)||!call_identity(b,arena)||
           !arena_class(b,manager,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
           local_read<uint64_t>(manager+32)!=ids_[0].address||
           arena_reference(b,manager,"BattleMapBP",728)!=arena.address||
           !arena_class(b,combatant,"BP_jRPG_Character_Battle_Base_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_Battle_Base")||
           !arena_world(b,combatant,ids_[2].address)||
           !arena_class(b,movement,"AC_jRPG_CombatMovement_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_CombatMovement")||
           local_read<uint64_t>(movement+32)!=combatant||
           arena_reference(b,combatant,"AC_jRPG_CombatMovement",2272)!=movement)return false;
        struct Flag {uint64_t object;const char* name;int offset;uint8_t expected;};
        const Flag flags[]={{actor_.address,"IsInBattle",2930,1},
            {manager,"IsBattleInitialized",168,1},{manager,"HasBattleStartedEndFlow",1961,0},
            {manager,"CurrentTurn_CanChooseAction",1216,1},
            {combatant,"IsTurnActive",4956,0},{movement,"MovementActive",304,0},{movement,"RotationActive",248,0}};
        for(const auto& flag:flags){
            const auto field=picto_field(b,flag.object,flag.name,"BoolProperty",flag.offset,1);
            if(!field||local_read<uint8_t>(field)!=flag.expected)return false;
        }
        const auto index=picto_field(b,combatant,"BattleSpotIndex","IntProperty",3360,4);
        const auto enemies=picto_field(b,manager,"Enemies","ArrayProperty",200,16);
        if(!index||!enemies)return false;
        slot=local_read<int32_t>(index);
        const auto data=local_read<uint64_t>(enemies);
        const auto count=local_read<int32_t>(enemies+8),capacity=local_read<int32_t>(enemies+12);
        if(slot<3||slot>9||count<=slot||count>10||capacity<count||capacity>4096||
           data<0x10000||(data&7)||local_read<uint64_t>(data+uint64_t(slot)*8)!=combatant)return false;
        const auto root=arena_reference(b,combatant,"RootComponent",416);
        if(!root||!arena_scene(b,root,combatant))return false;
        const auto parent=picto_field(b,root,"AttachParent","ObjectProperty",176,8);
        if(!parent||local_read<uint64_t>(parent))return false;
        return true;
    }

    uint32_t place_combatant(uint64_t b,const CallIdentity (&query)[7],
                            const double (&destination)[3],double (&output)[12]){
        int32_t slot=-1;
        if(!combat_placement_context(b,query,slot))return 3000;
        auto& journal=combat_placements_[slot-3];
        if(journal.pose.attempted)return 3001;
        // Validate original home-refresh function and property shapes before
        // moving anything. No raw home-position assignment or codec expansion.
        const auto fn=query[6].address,movement=query[2].address;
        if(!named(b,local_read<uint64_t>(fn+32),"AC_jRPG_CombatMovement_C",
                  "/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_CombatMovement")||
           !exact_name(b,fn+24,"UpdateInitialTransform")||local_read<uint32_t>(fn+0xb0)!=0xc000000||
           local_read<uint16_t>(fn+0xb6)!=0||local_read<uint16_t>(fn+0xb8)!=65535||
           local_read<int32_t>(fn+0x58)!=0||local_read<uint64_t>(fn+0xd8)!=b+0x13937a0||
           !fields(b,fn,nullptr,0))return 3002;
        uint64_t home[2]{};
        const char* names[]={"InitialLocation","InitialRotation"};
        const char* types[]={"Vector","Rotator"};
        for(unsigned i=0;i<2;++i){
            uint64_t descriptor=0;
            home[i]=picto_field(b,movement,names[i],"StructProperty",168+int(i)*24,24,&descriptor);
            const auto type=descriptor?local_read<uint64_t>(descriptor+0x70):0;
            if(!home[i]||!type||!named(b,type,types[i],"/Script/CoreUObject")||
               local_read<int32_t>(type+0x58)!=24)return 3002;
        }
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(movement)+0x268);
        if(pe!=b+0x1393330&&pe!=b+0x332bb90)return 3002;
        struct Ops {
            Owner& owner;uint64_t base;const CallIdentity (&ids)[7];
            bool current(){int32_t observed=-1;return owner.combat_placement_context(base,ids,observed);}
            bool location(double (&out)[3]){
                std::memset(owner.args_,0,sizeof(owner.args_));
                if(!owner.call(base,3,ids[3],ids[1]))return false;
                std::memcpy(out,owner.args_,24);return true;
            }
            bool rotation(double (&out)[3]){
                std::memset(owner.args_,0,sizeof(owner.args_));
                if(!owner.call(base,4,ids[4],ids[1]))return false;
                std::memcpy(out,owner.args_,24);return true;
            }
            bool teleport(const double (&position)[3],const double (&rotation)[3],bool& accepted){
                std::memset(owner.args_,0,sizeof(owner.args_));
                std::memcpy(owner.args_,position,24);std::memcpy(owner.args_+24,rotation,24);
                if(!owner.call(base,63,ids[5],ids[1]))return false;
                const auto value=owner.args_[48];if(value>1)return false;
                accepted=value!=0;return true;
            }
        } ops{*this,b,query};
        journal.actor=query[1];
        const auto placed=e33_actor_pose::place_preserving_rotation(ops,destination,2000.,1.,journal.pose);
        if(placed!=e33_actor_pose::Result::Placed&&
           !(placed==e33_actor_pose::Result::Adjusted&&e33_enemy_combat::collision_lift(journal.pose,destination)))
            return 3010+static_cast<uint32_t>(placed);
        if(!ops.current())return 3003;
        journal.home_dispatched=true;
        std::memset(args_,0,sizeof(args_));
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(movement),reinterpret_cast<void*>(fn),args_);
        journal.home_acknowledged=true;
        if(!ops.current())return 3003;
        double location[3]{},rotation[3]{};
        for(unsigned i=0;i<3;++i){location[i]=local_read<double>(home[0]+i*8);rotation[i]=local_read<double>(home[1]+i*8);}
        if(!e33_actor_pose::finite(location)||!e33_actor_pose::finite(rotation)||
           std::sqrt(e33_actor_pose::distance_squared(location,journal.pose.after.location))>1.||
           !e33_actor_pose::same_rotation(rotation,journal.pose.after.rotation,1.e-3))return 3004;
        journal.home_verified=true;
        std::memcpy(output,journal.pose.before.location,24);std::memcpy(output+3,journal.pose.before.rotation,24);
        std::memcpy(output+6,journal.pose.after.location,24);std::memcpy(output+9,journal.pose.after.rotation,24);
        return 0;
    }
