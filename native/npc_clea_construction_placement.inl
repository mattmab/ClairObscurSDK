// Clea-only preallocation planning. Read original CDO geometry; no templates,
// component mobility, transforms, registrations or class defaults are written.
    bool default_capsule_bounds(uint64_t base,PreviewBounds& bounds){
        const auto capsule_at=picto_field(base,source_.cdo.address,"CapsuleComponent","ObjectProperty",808,8);
        const auto root_at=picto_field(base,source_.cdo.address,"RootComponent","ObjectProperty",416,8);
        const auto capsule=capsule_at?local_read<uint64_t>(capsule_at):0;
        if(!root_at||!capsule||local_read<uint64_t>(root_at)!=capsule||local_read<uint64_t>(capsule+32)!=source_.cdo.address||
           !e33_mesh::named(base,local_read<uint64_t>(capsule+16),"CapsuleComponent","/Script/Engine"))return false;
        const auto height=component_field(base,capsule,"CapsuleHalfHeight","FloatProperty",1344,4,"CapsuleComponent",0x6e11560,0x2808104000021dULL);
        const auto radius=component_field(base,capsule,"CapsuleRadius","FloatProperty",1348,4,"CapsuleComponent",0x6e11560,0x2808104000021dULL);
        const auto parent=component_field(base,capsule,"AttachParent","ObjectProperty",176,8,"SceneComponent",0x6e11d38,0x14c001100080228ULL);
        const auto mobility=component_field(base,capsule,"Mobility","ByteProperty",395,1,"SceneComponent",0x6e10420,0x18001040000235ULL);
        if(!height||!radius||!parent||!mobility||local_read<uint64_t>(parent)||local_read<uint8_t>(mobility)!=1)return false;
        const double h=local_read<float>(height),r=local_read<float>(radius);
        if(!std::isfinite(h)||!std::isfinite(r)||r<=0||h<r||h>1.e5)return false;
        for(const auto spec:{std::pair<const char*,int>{"RelativeLocation",296},{"RelativeRotation",320},{"RelativeScale3D",344}}){
            const auto at=picto_field(base,capsule,spec.first,"StructProperty",spec.second,24);
            if(!at)return false;
            for(unsigned i=0;i<3;++i)if(local_read<double>(at+i*8)!=(spec.second==344?1.:0.))return false;
        }
        std::memcpy(bounds.center,source_.transform+4,24);bounds.half[0]=r;bounds.half[1]=r;bounds.half[2]=h;return true;
    }
    bool plan_defaults_unchanged(uint64_t base){
        PreviewBounds authored_bounds{};if(!default_capsule_bounds(base,authored_bounds))return false;
        const auto at=picto_field(base,state_.actor.address,"CapsuleComponent","ObjectProperty",808,8);
        const auto capsule=at?local_read<uint64_t>(at):0;
        if(!capsule)return false;
        const auto mobility=component_field(base,capsule,"Mobility","ByteProperty",395,1,"SceneComponent",0x6e10420,0x18001040000235ULL);
        const auto height=component_field(base,capsule,"CapsuleHalfHeight","FloatProperty",1344,4,"CapsuleComponent",0x6e11560,0x2808104000021dULL);
        const auto radius=component_field(base,capsule,"CapsuleRadius","FloatProperty",1348,4,"CapsuleComponent",0x6e11560,0x2808104000021dULL);
        return mobility&&height&&radius&&local_read<uint8_t>(mobility)==1&&
            local_read<float>(height)==authored_bounds.half[2]&&local_read<float>(radius)==authored_bounds.half[0];
    }
    template<class Pool> struct ConstructionPlacementOps : PreviewOps<Pool> {
        ConstructionPlacementOps(CleaOwner& value,uint64_t base,uint64_t session,Pool& pool,const CallIdentity (&query)[10]):
            PreviewOps<Pool>{value,base,session,pool,query}{}
        bool context(){
            auto& held=this->owner;
            Guard<Pool> guard{held,this->base,this->session,this->pool};
            Ops<Pool> construction(this->base,held,this->session,this->pool,guard);
            return held.owned_&&!held.lifecycle_.construction().attempted&&guard.current_context()&&guard.battle_quiescent()&&
                construction.exact_original_admission()&&held.source_.transform[0]==0&&held.source_.transform[1]==0;
        }
        bool current(){
            if(!context())return false;
            for(const auto& id:this->query)if(!call_identity(this->base,id))return false;
            if(!e33_mesh::named(this->base,this->query[1].address,"Default__KismetSystemLibrary","/Script/Engine"))return false;
            alignas(16) uint8_t frame[464]{};
            if(!e33_engine_profile_call::invoke(this->base,this->query[9],this->owner.source_.controller,e33_engine_profiles::profiles[21],frame))return false;
            uint64_t pawn=0;std::memcpy(&pawn,frame,8);if(pawn!=this->query[0].address)return false;
            auto outer=pawn;unsigned walked=0;
            for(;outer&&outer!=this->owner.source_.world.address&&++walked<32;outer=local_read<uint64_t>(outer+32)){}
            return outer==this->owner.source_.world.address&&context();
        }
        bool invoke(unsigned index,CallIdentity recipient,const MeshFunction& profile,uint8_t* frame){
            return current()&&e33_engine_profile_call::invoke(this->base,this->query[index],recipient,profile,frame);
        }
        bool bounds(bool player,PreviewBounds& out){
            if(!current())return false;
            if(!player)return this->owner.default_capsule_bounds(this->base,out);
            const auto at=picto_field(this->base,this->query[0].address,"CapsuleComponent","ObjectProperty",808,8);
            const auto capsule=at?local_read<uint64_t>(at):0;
            const auto root=picto_field(this->base,this->query[0].address,"RootComponent","ObjectProperty",416,8);
            if(!capsule||!root||local_read<uint64_t>(root)!=capsule||local_read<uint64_t>(capsule+32)!=this->query[0].address)return false;
            const auto parent=picto_field(this->base,capsule,"AttachParent","ObjectProperty",176,8);
            if(!parent||local_read<uint64_t>(parent))return false;
            alignas(16) uint8_t frame[464]{};std::memcpy(frame,&capsule,8);
            if(!invoke(4,this->query[1],e33_engine_profiles::profiles[64],frame))return false;
            std::memcpy(out.center,frame+8,24);std::memcpy(out.half,frame+32,24);return true;
        }
        bool location(double (&out)[3]){if(!current())return false;std::memcpy(out,this->owner.source_.transform+4,24);return true;}
        bool rotation(double (&out)[3]){
            if(!current())return false;out[0]=out[2]=0;
            out[1]=2*std::atan2(this->owner.source_.transform[2],this->owner.source_.transform[3])*180./3.14159265358979323846;return true;
        }
        bool player_pose(e33_actor_pose::Pose& out){
            alignas(16) uint8_t frame[464]{};
            if(!invoke(5,this->query[0],e33_engine_profiles::profiles[3],frame))return false;
            std::memcpy(out.location,frame,24);std::memset(frame,0,sizeof(frame));
            if(!invoke(6,this->query[0],e33_engine_profiles::profiles[4],frame))return false;
            std::memcpy(out.rotation,frame,24);return true;
        }
        e33_surface_query::Result surface(const double* start,const double* end,e33_surface_query::Sample& out){
            const uint64_t ignored[]={this->query[0].address};
            return e33_surface_query::sample([&](unsigned stage,uint8_t* frame){
                return invoke(stage?3:2,stage?this->owner.source_.gameplay_statics:this->query[1],e33_engine_profiles::profiles[stage?15:14],frame);
            },this->owner.source_.world.address,start,end,ignored,1,out);
        }
        e33_volume_query::Result volume(const double* center,const double* half){
            const uint64_t ignored[]={this->query[0].address};
            return e33_volume_query::sample([&](uint8_t* frame){return invoke(8,this->query[1],e33_volume_query::box_profile,frame);},
                this->owner.source_.world.address,center,half,ignored,1);
        }
        bool teleport(const double (&)[3],const double (&)[3],bool&){return false;}
    };
