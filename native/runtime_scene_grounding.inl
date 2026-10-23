// Included in Owner's public section. Reuses the existing ground/clearance/pose
// transaction with a native skeletal root rather than an NPC capsule. No pawn
// transforms, component scales, collision modes or authored defaults are written.
    bool visual_ground_scale(double (&out)[3]){
        if(!valid(characters_[0]) || !valid(components_[0]))return false;
        const auto root=picto_field(base_,characters_[0].address,"RootComponent","ObjectProperty",416,8);
        const auto parent=picto_field(base_,components_[0].address,"AttachParent","ObjectProperty",176,8);
        const auto scale=picto_field(base_,components_[0].address,"RelativeScale3D","StructProperty",344,24);
        if(!root || local_read<uint64_t>(root)!=components_[0].address || !parent || local_read<uint64_t>(parent) || !scale)return false;
        for(unsigned i=0;i<3;++i){out[i]=local_read<double>(scale+8*i);
            if(!std::isfinite(out[i]) || std::abs(out[i])<1.e-9 || std::abs(out[i])>1.e5)return false;}
        return true;
    }
    struct VisualGroundOps {
        Owner& owner;const CallIdentity (&query)[10];
        bool current(){
            uint64_t name=0;double scale[3]{};
            if(!owner.visual_parameter_instance(owner.base_,owner.owner_,owner.characters_[0],name) ||
               !owner.visual_arena_state_.verified || !owner.valid(owner.visual_world_) ||
               !owner.same(query[0],owner.ids_[2]) || !owner.visual_ground_scale(scale) ||
               std::memcmp(scale,owner.visual_ground_scale_,sizeof(scale)))return false;
            for(const auto& id:query)if(!owner.valid(id))return false;
            if(!e33_mesh::named(owner.base_,query[1].address,"Default__KismetSystemLibrary","/Script/Engine"))return false;
            e33_npc_presentation::CurrentContextGuard context{owner.base_,owner.ids_[1],owner.visual_world_};
            return context.battle_quiescent();
        }
        bool invoke(unsigned index,CallIdentity recipient,const MeshFunction& profile,uint8_t* frame){
            return current() && e33_engine_profile_call::invoke(owner.base_,query[index],recipient,profile,frame);
        }
        bool bounds(bool player,e33_npc_presentation::PreviewBounds& out){
            if(!current())return false;
            uint64_t component=owner.components_[0].address;
            if(player){
                const auto root=picto_field(owner.base_,query[0].address,"RootComponent","ObjectProperty",416,8);
                component=root?local_read<uint64_t>(root):0;
                if(!call_capture(owner.base_,component).address || local_read<uint64_t>(component+32)!=query[0].address)return false;
                const auto parent=picto_field(owner.base_,component,"AttachParent","ObjectProperty",176,8);
                if(!parent || local_read<uint64_t>(parent))return false;
            }
            alignas(16) uint8_t frame[464]{};std::memcpy(frame,&component,8);
            if(!invoke(4,query[1],e33_engine_profiles::profiles[64],frame))return false;
            std::memcpy(out.center,frame+8,24);std::memcpy(out.half,frame+32,24);return true;
        }
        bool get(unsigned index,unsigned profile,CallIdentity actor,double (&out)[3]){
            alignas(16) uint8_t frame[464]{};
            if(!invoke(index,actor,e33_engine_profiles::profiles[profile],frame))return false;
            std::memcpy(out,frame,24);return true;
        }
        bool location(double (&out)[3]){return get(5,3,owner.characters_[0],out);}
        bool rotation(double (&out)[3]){return get(6,4,owner.characters_[0],out);}
        bool player_pose(e33_actor_pose::Pose& out){return get(5,3,query[0],out.location)&&get(6,4,query[0],out.rotation);}
        e33_surface_query::Result surface(const double* start,const double* end,e33_surface_query::Sample& out){
            const uint64_t ignored[]={owner.characters_[0].address,query[0].address};
            return e33_surface_query::sample([&](unsigned stage,uint8_t* frame){
                return invoke(stage?3:2,stage?owner.ids_[3]:query[1],e33_engine_profiles::profiles[stage?15:14],frame);
            },owner.visual_world_.address,start,end,ignored,2,out);
        }
        e33_volume_query::Result volume(const double* center,const double* half){
            const uint64_t ignored[]={owner.characters_[0].address,query[0].address};
            return e33_volume_query::sample([&](uint8_t* frame){return invoke(8,query[1],e33_volume_query::box_profile,frame);},
                owner.visual_world_.address,center,half,ignored,2);
        }
        bool teleport(const double (&to)[3],const double (&rot)[3],bool& accepted){
            alignas(16) uint8_t frame[464]{};std::memcpy(frame,to,24);std::memcpy(frame+24,rot,24);frame[304]=1;
            if(!invoke(7,owner.characters_[0],e33_engine_profiles::profiles[5],frame) || frame[305]>1)return false;
            accepted=frame[305]!=0;return true;
        }
    };
    uint32_t ground_visual(const CallIdentity (&query)[10]){
        if(visual_ground_requested_)return 2055;
        uint64_t name=0;CallIdentity arena{};
        if(!visual_parameter_instance(base_,owner_,characters_[0],name) ||
           !visual_parameter_arena(base_,owner_,characters_[0],arena))return 2050;
        // Full component bounds are sufficient for this initial one-root native
        // assembly. Do not silently treat a multipart character as root-only.
        for(unsigned i=1;i<6;++i)if(scene_parts[unsigned(plan_.roles[0])][i].name[0])return 2050;
        if(!visual_ground_scale(visual_ground_scale_))return 2050;
        visual_ground_requested_=true;
        VisualGroundOps ops{*this,query};
        visual_ground_result_=e33_npc_presentation::place_preview_nearby(ops,visual_ground_,visual_ground_candidates_);
        return visual_ground_result_==e33_npc_presentation::PreviewPlacementResult::Complete?0:
            2050+static_cast<uint32_t>(visual_ground_result_);
    }
    void ground_snapshot(uint8_t* bytes)const{
        std::memset(bytes,0,128);
        const uint32_t head[]={static_cast<uint32_t>(visual_ground_result_),visual_ground_.samples,
            visual_ground_.support?1U:0U,visual_ground_.clearance?1U:0U};
        std::memcpy(bytes,head,sizeof(head));
        std::memcpy(bytes+16,&visual_ground_.minimum,8);std::memcpy(bytes+24,&visual_ground_.maximum,8);
        std::memcpy(bytes+32,visual_ground_.destination,24);
        std::memcpy(bytes+56,visual_ground_.placement.before.location,24);
        std::memcpy(bytes+80,visual_ground_.placement.after.location,24);
        const auto& p=visual_ground_.placement;
        const uint32_t flags[]={p.attempted?1U:0U,p.acknowledged?1U:0U,p.engine_accepted?1U:0U,p.readback?1U:0U,
            visual_ground_.verified?1U:0U};
        std::memcpy(bytes+104,flags,sizeof(flags));
#if E33_RUNTIME_CINEMATIC_VERSION >= 175
        std::memcpy(bytes+124,&visual_ground_candidates_,4);
#endif
    }
