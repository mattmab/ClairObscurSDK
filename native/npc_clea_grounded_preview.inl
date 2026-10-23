// Included only inside CleaOwner. Fixed queries reuse SDK profiles and adapters.
// query: current pawn, Kismet CDO, line trace, break hit, bounds, location,
// rotation, SetActorLocationAndRotation, box trace, controller GetPawn.
// No WorldBuilder dependency. Preserve original stationary capsule mobility.
    template<class Pool> struct PreviewOps {
        CleaOwner& owner;uint64_t base,session;Pool& pool;const CallIdentity (&query)[10];
        bool context(){
            if(!owner.owned_||session!=owner.source_.session||!owner.targets_complete_||!owner.conditions_verified_||
               owner.unreviewed_script_components_||owner.unexpected_controller_.address||
               owner.lifecycle_.construction().phase!=e33_owned_actor::ConstructionPhase::Complete||
               owner.lifecycle_.retirement()!=RetirementPhase::Ready)return false;
            Guard<Pool> guard{owner,base,session,pool};Ops<Pool> construction(base,owner,session,pool,guard);
            if(!construction.exact_owned_actor()||!guard.battle_quiescent()||!guard.interaction_held()||!call_identity(base,owner.state_.movement))return false;
            const auto mode=picto_field(base,owner.state_.movement.address,"MovementMode","ByteProperty",513,1);
            return mode&&local_read<uint8_t>(mode)==0;
        }
        bool current(){
            if(!context())return false;
            for(const auto& id:query)if(!call_identity(base,id))return false;
            if(!e33_mesh::named(base,query[1].address,"Default__KismetSystemLibrary","/Script/Engine"))return false;
            alignas(16) uint8_t frame[464]{};
            if(!e33_engine_profile_call::invoke(base,query[9],owner.source_.controller,e33_engine_profiles::profiles[21],frame))return false;
            uint64_t pawn=0;std::memcpy(&pawn,frame,8);
            if(pawn!=query[0].address)return false;
            auto outer=pawn;unsigned walked=0;
            for(;outer&&outer!=owner.source_.world.address&&++walked<32;outer=local_read<uint64_t>(outer+32)){}
            return outer==owner.source_.world.address&&context();
        }
        bool invoke(unsigned index,CallIdentity recipient,const MeshFunction& profile,uint8_t* frame){
            return current()&&e33_engine_profile_call::invoke(base,query[index],recipient,profile,frame);
        }
        bool bounds(bool player,PreviewBounds& out){
            if(!current())return false;
            const auto actor=player?query[0]:owner.state_.actor;
            const auto at=picto_field(base,actor.address,"CapsuleComponent","ObjectProperty",808,8);
            const auto capsule=at?local_read<uint64_t>(at):0;
            const auto root=picto_field(base,actor.address,"RootComponent","ObjectProperty",416,8);
            if(!capsule||!root||local_read<uint64_t>(root)!=capsule||local_read<uint64_t>(capsule+32)!=actor.address||
               !e33_mesh::named(base,local_read<uint64_t>(capsule+16),"CapsuleComponent","/Script/Engine"))return false;
            const auto parent=picto_field(base,capsule,"AttachParent","ObjectProperty",176,8);
            if(!parent||local_read<uint64_t>(parent))return false;
            alignas(16) uint8_t frame[464]{};std::memcpy(frame,&capsule,8);
            if(!invoke(4,query[1],e33_engine_profiles::profiles[64],frame))return false;
            std::memcpy(out.center,frame+8,24);std::memcpy(out.half,frame+32,24);return true;
        }
        bool get(unsigned index,unsigned profile,CallIdentity actor,double (&out)[3]){
            alignas(16) uint8_t frame[464]{};
            if(!invoke(index,actor,e33_engine_profiles::profiles[profile],frame))return false;
            std::memcpy(out,frame,24);return true;
        }
        bool location(double (&out)[3]){return get(5,3,owner.state_.actor,out);}
        bool rotation(double (&out)[3]){return get(6,4,owner.state_.actor,out);}
        bool player_pose(e33_actor_pose::Pose& out){return get(5,3,query[0],out.location)&&get(6,4,query[0],out.rotation);}
        e33_surface_query::Result surface(const double* start,const double* end,e33_surface_query::Sample& out){
            const uint64_t ignored[]={owner.state_.actor.address,query[0].address};
            return e33_surface_query::sample([&](unsigned stage,uint8_t* frame){
                return invoke(stage?3:2,stage?owner.source_.gameplay_statics:query[1],e33_engine_profiles::profiles[stage?15:14],frame);
            },owner.source_.world.address,start,end,ignored,2,out);
        }
        e33_volume_query::Result volume(const double* center,const double* half){
            const uint64_t ignored[]={owner.state_.actor.address,query[0].address};
            return e33_volume_query::sample([&](uint8_t* frame){return invoke(8,query[1],e33_volume_query::box_profile,frame);},
                owner.source_.world.address,center,half,ignored,2);
        }
        bool teleport(const double (&to)[3],const double (&rot)[3],bool& accepted){
            alignas(16) uint8_t frame[464]{};std::memcpy(frame,to,24);std::memcpy(frame+24,rot,24);
            // Same exact SDK operation used by prepared world-enemy placement:
            // no sweep, teleport physics. Preflighted support/clearance is
            // mandatory; no fallback/retry of a rejected TeleportTo is made.
            frame[304]=1;
            if(!invoke(7,owner.state_.actor,e33_engine_profiles::profiles[5],frame))return false;
            if(frame[305]>1)return false;
            accepted=frame[305]!=0;return true;
        }
    };
