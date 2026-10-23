    template<class Pool> uint32_t ground_owned_arena(uint64_t b,uint64_t session,Pool& pool,
            const CallIdentity (&query)[9],ArenaGroundReport& report,bool forward_approach=false,ArenaGroundDiagnostics* diagnostics=nullptr,bool require_corridor=true){
        if(diagnostics&&!forward_approach)return 3610;
        if(!require_corridor&&(!forward_approach||!diagnostics))return 3610;
        if(!arena_staging_||!owner_||!lease_||arena_ground_attempted_||!current(b,true)||!helper_battle_quiescent(b)||
           !call_identity(b,actor_)||!pool.owns_object(session,lease_,actor_.address)||
           construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
           !named(b,query[0].address,"Default__KismetSystemLibrary","/Script/Engine"))return 3610;
        ArenaAssemblyObservation assembly{};
        if(observe_arena_assembly(b,ids_[2].address,actor_.address,assembly)||assembly.streaming_enabled)return 3610;
        uint64_t hidden_descriptor=0,collision_descriptor=0;
        const auto hidden=picto_field(b,actor_.address,"bHidden","BoolProperty",88,1,&hidden_descriptor);
        const auto collision=picto_field(b,actor_.address,"bActorEnableCollision","BoolProperty",92,1,&collision_descriptor);
        // Actor bHidden's offset/bit schema is checked by the construction
        // visibility operation. Confirm its value via the supported schema.
        if(!hidden||!hidden_descriptor||local_read<uint32_t>(hidden_descriptor+0x70)!=0x80800001U||
           !(local_read<uint8_t>(hidden)&0x80)||!collision||!collision_descriptor||
           local_read<uint32_t>(collision_descriptor+0x70)!=0x80800001U||(local_read<uint8_t>(collision)&0x80))return 3610;
        arena_ground_attempted_=true;
        const char* names[]={"BP_jRPG_EnemyBattleSpot0","BP_jRPG_EnemyBattleSpot1","BP_jRPG_EnemyBattleSpot2","BP_jRPG_EnemyBattleSpot3",
            "BP_jRPG_CharacterBattleSpot","BP_jRPG_CharacterBattleSpot1","BP_jRPG_CharacterBattleSpot2"};
        const int offsets[]={792,840,832,824,864,856,848};
        CallIdentity positions[7]{};double slot_before[7][3]{},root_pose[12]{},rotation[3]{},pawn[3]{},facing[3]{},half[3]{};
        const auto root=arena_reference(b,actor_.address,"RootComponent",416);
        if(!root||!arena_scene(b,root,actor_.address))return 3611;
        auto component_world=[&](CallIdentity component,double* pose){
            std::memset(args_,0,sizeof(args_));if(!call(b,19,query[3],component))return false;
            std::memcpy(pose,args_,96);
            for(unsigned j=0;j<12;++j)if(j!=7&&j!=11&&(!std::isfinite(pose[j])||std::abs(pose[j])>1.e7))return false;
            double norm=0;for(unsigned j=0;j<4;++j)norm+=pose[j]*pose[j];if(std::abs(norm-1)>1.e-6)return false;
            for(unsigned j=8;j<11;++j)if(std::abs(pose[j]-1)>1.e-6)return false;
            return true;
        };
        if(!component_world(call_capture(b,root),root_pose))return 3611;
        std::memcpy(report.before,root_pose+4,24);
        std::memset(args_,0,sizeof(args_));if(!call(b,4,query[5],actor_))return 3611;std::memcpy(rotation,args_,24);
        for(double v:rotation)if(!std::isfinite(v)||std::abs(v)>1.e7)return 3611;
        if(std::abs(rotation[0])>1.e-6||std::abs(rotation[2])>1.e-6)return 3611;
        std::memset(args_,0,sizeof(args_));if(!call(b,3,query[4],ids_[1]))return 3611;std::memcpy(pawn,args_,24);
        std::memset(args_,0,sizeof(args_));if(!call(b,4,query[5],ids_[1]))return 3611;std::memcpy(facing,args_,24);
        for(unsigned j=0;j<3;++j)if(!std::isfinite(pawn[j])||std::abs(pawn[j])>1.e7||!std::isfinite(facing[j]))return 3611;
        const auto capsule=arena_reference(b,ids_[1].address,"CapsuleComponent",808);
        if(!arena_class(b,capsule,"CapsuleComponent","/Script/Engine")||local_read<uint64_t>(capsule+32)!=ids_[1].address)return 3611;
        std::memset(args_,0,sizeof(args_));put(0,capsule);if(!call(b,64,query[7],query[0]))return 3611;std::memcpy(half,args_+32,24);
        for(double v:half)if(!std::isfinite(v)||v<=0||v>1000)return 3611;
        for(unsigned i=0;i<7;++i){
            const auto component=arena_reference(b,actor_.address,names[i],offsets[i]);
            const auto child=component?arena_reference(b,component,"ChildActor",568):0;
            const auto position=child?arena_reference(b,child,"SpawnPosition",664):0;
            if(!position||!arena_scene(b,position,child))return 3611;
            positions[i]=call_capture(b,position);double pose[12]{};
            if(!component_world(positions[i],pose))return 3611;
            std::memcpy(slot_before[i],pose+4,24);
        }
        const uint64_t ignored[]={actor_.address,ids_[1].address};
        bool accepted=false;uint32_t rejection=3612;
        // Direct fights need no walking corridor. Keep the original nine nearby
        // candidates first, then search three complete bounded rings (32/64/96m)
        // without relaxing support spread or party clearance.
        const unsigned count=forward_approach?3:57;
        for(unsigned candidate=0;candidate<count;++candidate){
            ++report.candidates;report.samples=0;report.supported=report.clearance=0;
            report.approach_samples=0;
            ArenaCandidateDiagnostic* detail=nullptr;
            if(diagnostics){detail=&diagnostics->candidates[candidate];++diagnostics->count;
                detail->distance=e33_arena_approach::distances[candidate];detail->stage=1;}
            // Preserve each candidate's last observation even on an early
            // refusal. This never changes the placement decision or queries.
            struct SaveDiagnostic {
                ArenaGroundReport& report;ArenaCandidateDiagnostic* detail;
                ~SaveDiagnostic(){if(detail){detail->samples=report.samples;detail->approach_samples=report.approach_samples;}}
            } save_diagnostic{report,detail};
            const double heading=forward_approach?0.:(candidate<9?e33_enemy_ground::heading_offsets[candidate]:
                static_cast<double>((candidate-9)%16)*22.5);
            const double distance=forward_approach||candidate<9?1600.:3200.*(1.+static_cast<double>((candidate-9)/16));
            const double angle=(facing[1]+heading)*3.14159265358979323846/180.;
            // The battle area's origin, not the huge visual helper's bounds,
            // stays16m ahead. Rigid authored slot/focus transforms are preserved.
            double xy[]={pawn[0]+std::cos(angle)*distance,pawn[1]+std::sin(angle)*distance};
            if(forward_approach){
                const double offset[]={slot_before[0][0]-report.before[0],slot_before[0][1]-report.before[1]};
                // The arena was staged with the requested player-facing yaw.
                // Keep that direction if the player turns during asset loads;
                // mixing a new heading with the original arena yaw recreates
                // the sideways approach/visible-body mismatch.
                if(!e33_arena_approach::origin(pawn,rotation[1],e33_arena_approach::distances[candidate],offset,xy))return 3613;
            }
            double minimum=1.e8,maximum=-1.e8;bool supported=true;
            for(unsigned i=0;i<7&&supported;++i){
                const double x=xy[0]+slot_before[i][0]-report.before[0],y=xy[1]+slot_before[i][1]-report.before[1];
                // Three party footprints use the actual exploration pawn's
                // observed capsule bounds. Enemy points certify support only,
                // not a fabricated humanoid boss collision envelope.
                const int radius=i>=4?1:0;
                for(int sy=-radius;sy<=radius&&supported;++sy)for(int sx=-radius;sx<=radius&&supported;++sx){
                    const double start[]={x+sx*half[0],y+sy*half[1],pawn[2]+5000.};
                    const double end[]={start[0],start[1],pawn[2]-10000.};e33_surface_query::Sample sample{};
                    ++report.samples;
                    const auto sampled=e33_surface_query::sample([&](unsigned stage,uint8_t* frame){
                        std::memcpy(args_,frame,sizeof(args_));const bool ok=stage?call(b,15,query[2],ids_[3]):call(b,14,query[1],query[0]);
                        std::memcpy(frame,args_,sizeof(args_));return ok;
                    },ids_[2].address,start,end,ignored,2,sample);
                    if(detail)detail->last_surface=static_cast<uint32_t>(sampled)+1;
                    if(sampled==e33_surface_query::Result::Invalid||sampled==e33_surface_query::Result::Rejected)return 3613;
                    if(sampled!=e33_surface_query::Result::Hit){supported=false;break;}
                    minimum=std::min(minimum,sample.point[2]);maximum=std::max(maximum,sample.point[2]);
                    if(detail){detail->minimum=minimum;detail->maximum=maximum;}
                    if(!sx&&!sy)report.heights[i]=sample.point[2];
                }
                report.positions[i][0]=x;report.positions[i][1]=y;
            }
            report.minimum=minimum;report.maximum=maximum;
            if(!supported||maximum-minimum>100.)continue;
            if(detail)detail->stage=2;
            report.supported=1;bool clear=true;
            for(unsigned i=4;i<7&&clear;++i){
                const double center[]={report.positions[i][0],report.positions[i][1],maximum+half[2]+15.};
                const auto result=e33_volume_query::sample([&](uint8_t* frame){
                    std::memcpy(args_,frame,sizeof(args_));const bool ok=call(b,101,query[8],query[0]);std::memcpy(frame,args_,sizeof(args_));return ok;
                },ids_[2].address,center,half,ignored,2);
                if(result==e33_volume_query::Result::Invalid||result==e33_volume_query::Result::Rejected)return 3613;
                clear=result==e33_volume_query::Result::Clear;
            }
            if(!clear){rejection=3614;continue;}
            if(forward_approach){
                if(detail)detail->stage=3;
                struct CorridorOps {
                    Owner& owner;uint64_t base,world;const CallIdentity* queries;const uint64_t* ignored;
                    e33_surface_query::Result surface(const double* start,const double* end,e33_surface_query::Sample& output){
                        if(!owner.current(base,true)||!owner.helper_battle_quiescent(base))return e33_surface_query::Result::Rejected;
                        return e33_surface_query::sample([&](unsigned stage,uint8_t* frame){
                            std::memcpy(owner.args_,frame,sizeof(owner.args_));
                            const bool ok=stage?owner.call(base,15,queries[2],owner.ids_[3]):owner.call(base,14,queries[1],queries[0]);
                            std::memcpy(frame,owner.args_,sizeof(owner.args_));return ok;
                        },world,start,end,ignored,2,output);
                    }
                    e33_volume_query::Result volume(const double* center,const double* extent){
                        if(!owner.current(base,true)||!owner.helper_battle_quiescent(base))return e33_volume_query::Result::Rejected;
                        return e33_volume_query::sample([&](uint8_t* frame){
                            std::memcpy(owner.args_,frame,sizeof(owner.args_));const bool ok=owner.call(base,101,queries[8],queries[0]);
                            std::memcpy(frame,owner.args_,sizeof(owner.args_));return ok;
                        },world,center,extent,ignored,2);
                    }
                } corridor_ops{*this,b,ids_[2].address,query,ignored};
                const double entry_position[]={report.positions[0][0],report.positions[0][1],report.heights[0]};
                const auto approach=e33_arena_approach::corridor(corridor_ops,pawn,entry_position,half,report.heights[0],report.approach_samples,detail?&detail->approach:nullptr);
                if(approach==e33_arena_approach::Result::Rejected)return 3613;
                if(!e33_arena_approach::permits_placement(approach,require_corridor)){rejection=3617;continue;}
            }
            if(detail)detail->stage=4;
            report.clearance=1;report.destination[0]=xy[0];report.destination[1]=xy[1];report.destination[2]=maximum+5.;accepted=true;break;
        }
        if(!accepted)return rejection;
        for(unsigned i=0;i<7;++i)report.positions[i][2]=report.destination[2]+slot_before[i][2]-report.before[2];
        struct PoseOps {
            Owner& owner;uint64_t base;const CallIdentity* queries;
            bool current(){return owner.current(base,true)&&owner.helper_battle_quiescent(base)&&call_identity(base,owner.actor_);}
            bool location(double* out){std::memset(owner.args_,0,sizeof(owner.args_));if(!owner.call(base,3,queries[4],owner.actor_))return false;std::memcpy(out,owner.args_,24);return true;}
            bool rotation(double* out){std::memset(owner.args_,0,sizeof(owner.args_));if(!owner.call(base,4,queries[5],owner.actor_))return false;std::memcpy(out,owner.args_,24);return true;}
            bool teleport(const double* xyz,const double* angles,bool& accepted){
                std::memset(owner.args_,0,sizeof(owner.args_));std::memcpy(owner.args_,xyz,24);std::memcpy(owner.args_+24,angles,24);owner.args_[304]=1;
                if(!owner.call(base,5,queries[6],owner.actor_))return false;accepted=owner.args_[305]!=0;return true;
            }
        } ops{*this,b,query};
        const auto placed=e33_actor_pose::place_preserving_rotation(ops,report.destination,100000.,.1,arena_ground_journal_);
        report.attempted=arena_ground_journal_.attempted;report.acknowledged=arena_ground_journal_.acknowledged;
        report.engine_accepted=arena_ground_journal_.engine_accepted;report.readback=arena_ground_journal_.readback;
        std::memcpy(report.after,arena_ground_journal_.after.location,24);
        if(placed!=e33_actor_pose::Result::Placed)return 3615;
        for(unsigned i=0;i<7;++i){double pose[12]{};if(!component_world(positions[i],pose))return 3616;
            for(unsigned j=0;j<3;++j)if(std::abs(pose[4+j]-report.positions[i][j])>.1)return 3616;}
        arena_ground_frame_function_=query[3];arena_ground_rotation_function_=query[5];
        arena_grounded_=true;report.verified=1;return 0;
    }
