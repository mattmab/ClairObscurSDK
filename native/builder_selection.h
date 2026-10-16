    struct Candidate {CallIdentity actor,component;double low[3],high[3],pose[12];};
    std::vector<Candidate> candidates_;
    int32_t scan_index_=0;
    CallIdentity glowing_{};
    struct MaterialSlot {CallIdentity original;uint64_t lease;};
    std::vector<MaterialSlot> materials_;
    bool hidden_flag(uint64_t b,CallIdentity object,const char* owner,const char* name) {
        for(auto cls=local_read<uint64_t>(object.address+16);cls;cls=local_read<uint64_t>(cls+0x40)) {
            if(!named(b,cls,owner,"/Script/Engine"))continue;
            auto f=local_read<uint64_t>(cls+0x50);
            for(int n=0;f&&n<512;++n,f=local_read<uint64_t>(f+24)) {
                if(!exact_name(b,f+32,name))continue;
                const auto at=local_read<int32_t>(f+0x44);const auto encoding=local_read<uint32_t>(f+0x70);
                const auto width=local_read<int32_t>(f+0x34);const auto byteOffset=uint8_t(encoding>>8),mask=uint8_t(encoding>>24);
                if(local_read<uint64_t>(f+16)!=(cls|1)||!exact_name(b,local_read<uint64_t>(f+8),"BoolProperty")||
                   local_read<int32_t>(f+0x30)!=1||width!=1||byteOffset||!mask||at<0||at>=local_read<int32_t>(cls+0x58))return true;
                return (local_read<uint8_t>(object.address+at)&mask)!=0;
            }
            return true;
        }
        return true;
    }
    bool ambient(uint64_t b,CallIdentity actor,CallIdentity component) {
        if(!call_identity(b,actor)||!call_identity(b,component))return false;
        char ownerName[64]{};
        if(skin_name(b,local_read<uint64_t>(local_read<uint64_t>(actor.address+16)+24),ownerName)) {
            const std::string name=ownerName;
            if(name.find("Fog")!=std::string::npos||name.find("Cloud")!=std::string::npos||name.find("Sky")!=std::string::npos||name.find("Volumetric")!=std::string::npos)return true;
        }
        auto meshName=object_name(b,component);
        for(auto& ch:meshName)if(ch>='A'&&ch<='Z')ch=char(ch-'A'+'a');
        if(meshName.find("sm_sphere")!=std::string::npos||meshName.find("cloud")!=std::string::npos||meshName.find("fog")!=std::string::npos||meshName.find("sky")!=std::string::npos)return true;
        return false;
    }
    bool editable_mesh_class(uint64_t b,uint64_t cls) {
        // Instanced components are edited as a group, retaining the game's
        // instance transforms and the existing component undo/save identity.
        if(cls==ids_[63].address)return true;
        if(!call_derives(b,cls,ids_[63].address))return false;
        return
            named(b,cls,"InstancedStaticMeshComponent","/Script/Engine") ||
            named(b,cls,"HierarchicalInstancedStaticMeshComponent","/Script/Engine");
    }
    bool ordinary(uint64_t b,CallIdentity actor,CallIdentity component) {
        if(component.address&&component.address==gallery_floor_component_.address)return false;
        if(!call_identity(b,actor)||!call_identity(b,component))return false;
        if((local_read<uint32_t>(actor.address+8)&0x30)||
           call_derives(b,local_read<uint64_t>(actor.address+16),ids_[7].address)||
           !editable_mesh_class(b,local_read<uint64_t>(component.address+16)))return false;
        if(ambient(b,actor,component))return false;
        const auto level=call_capture(b,local_read<uint64_t>(actor.address+32));
        if(!level.address||!named(b,local_read<uint64_t>(level.address+16),"Level","/Script/Engine"))return false;
        if(hidden_flag(b,actor,"Actor","bHidden")||hidden_flag(b,component,"SceneComponent","bHiddenInGame"))return false;
        clear();if(!call(b,component,39)||!args_[0])return false;
        clear();return call(b,component,18)&&get<uint64_t>()==actor.address;
    }
    bool candidate_pose(uint64_t b,Candidate& c) {
        // Show-only capture and collision queries create weak references lazily.
        // Assign stable serials before caching identities across render frames.
        for(auto* id:{&c.actor,&c.component}) {
            if(!call_identity(b,*id))return false;
            if(!id->serial) {
                TargetStrongReferenceOps ops{b,*id};
                if(!ops.can_assign()||ops.allocate_serial(id->index)<=0)return false;
                *id=call_capture(b,id->address);
            }
        }
        if(local_read<uint64_t>(c.component.address+16)!=ids_[63].address) {
            // GetLocalBounds describes the source mesh, not its instances.
            // Cached component bounds cover the entire group at constant cost.
            // This box only schedules captures; GPU depth proves the mesh hit.
            clear();put(0,c.component.address);if(!call(b,ids_[5],64))return false;
            std::fill(std::begin(c.pose),std::end(c.pose),0.);
            c.pose[3]=c.pose[8]=c.pose[9]=c.pose[10]=1.;
            for(int j=0;j<3;++j){c.pose[4+j]=get<double>(8+8*j);c.low[j]=-get<double>(32+8*j);c.high[j]=-c.low[j];}
        } else {
            clear();if(!call(b,c.component,19))return false;std::memcpy(c.pose,args_,96);
            clear();if(!call(b,c.component,37))return false;
            std::memcpy(c.low,args_,24);std::memcpy(c.high,args_+24,24);
        }
        for(int j=0;j<3;++j)if(!std::isfinite(c.low[j])||!std::isfinite(c.high[j])||c.high[j]<=c.low[j]||std::abs(c.pose[8+j])<1.e-8)return false;
        return true;
    }
    void refresh_candidate(uint64_t b,CallIdentity component) {
        for(auto& c:candidates_)if(c.component.address==component.address&&c.component.serial==component.serial){candidate_pose(b,c);break;}
    }
    void scan_candidates(uint64_t b) {
        const auto count=local_read<int32_t>(b+0x9361b84);if(count<=0||count>4000000)return;
        const auto chunks=local_read<uint64_t>(b+0x9361b70);int added=0;LARGE_INTEGER start{},freq{};QueryPerformanceCounter(&start);QueryPerformanceFrequency(&freq);
        for(int budget=0;budget<1024&&added<64;++budget) {
            if((budget&63)==63){LARGE_INTEGER now{};QueryPerformanceCounter(&now);if(double(now.QuadPart-start.QuadPart)/double(freq.QuadPart)>.0003)break;}
            if(scan_index_>=count){scan_index_=0;candidates_.erase(std::remove_if(candidates_.begin(),candidates_.end(),[&](const Candidate& c){return !call_identity(b,c.component)||!call_identity(b,c.actor);}),candidates_.end());break;}
            const auto index=scan_index_++;
            const auto chunk=local_read<uint64_t>(chunks+uint64_t(index>>16)*8);if(!chunk)continue;
            const auto object=local_read<uint64_t>(chunk+uint64_t(index&65535)*24);if(!object||!editable_mesh_class(b,local_read<uint64_t>(object+16))||(local_read<uint32_t>(object+8)&0x30))continue;
            auto component=call_capture(b,object);if(!call_identity(b,component))continue;
            clear();if(!call(b,component,18))continue;auto actor=call_capture(b,get<uint64_t>());
            if(!ordinary(b,actor,component))continue;
            ++added;
            const auto mesh_name=object_name(b,component);
            if(mesh_name.find("Cloud")!=std::string::npos||mesh_name.find("Fog")!=std::string::npos||mesh_name.find("Sky")!=std::string::npos)continue;
            auto it=std::find_if(candidates_.begin(),candidates_.end(),[&](const Candidate& c){return c.component.address==component.address;});
            Candidate c{};c.actor=actor;c.component=component;if(!candidate_pose(b,c))continue;
            if(it!=candidates_.end())*it=c;else if(candidates_.size()<32768)candidates_.push_back(c);
            LARGE_INTEGER now{};QueryPerformanceCounter(&now);if(double(now.QuadPart-start.QuadPart)/double(freq.QuadPart)>.0003)break;
        }
    }
    // Transform the ray into the mesh's local box; no collision data is needed.
    static void inverse_rotate(const double* q,const double* v,double* out) {
        const double t[]={-2*(q[1]*v[2]-q[2]*v[1]),-2*(q[2]*v[0]-q[0]*v[2]),-2*(q[0]*v[1]-q[1]*v[0])};
        out[0]=v[0]+q[3]*t[0]-q[1]*t[2]+q[2]*t[1];
        out[1]=v[1]+q[3]*t[1]-q[2]*t[0]+q[0]*t[2];
        out[2]=v[2]+q[3]*t[2]-q[0]*t[1]+q[1]*t[0];
    }
    void bounds_pick(uint64_t b,const double* rayOrigin,const double* dir,CallIdentity& actor,CallIdentity& component,double& distance) {
        for(const auto& c:candidates_) {
            double relative[3];for(int j=0;j<3;++j)relative[j]=rayOrigin[j]-c.pose[4+j];
            double origin[3],direction[3];inverse_rotate(c.pose,relative,origin);inverse_rotate(c.pose,dir,direction);
            double entryDistance=0,exitDistance=distance;bool valid=true;
            for(int j=0;j<3;++j) {
                origin[j]/=c.pose[8+j];direction[j]/=c.pose[8+j];
                if(std::abs(direction[j])<1.e-10){if(origin[j]<c.low[j]||origin[j]>c.high[j])valid=false;continue;}
                double a=(c.low[j]-origin[j])/direction[j],z=(c.high[j]-origin[j])/direction[j];if(a>z)std::swap(a,z);
                entryDistance=std::max(entryDistance,a);exitDistance=std::min(exitDistance,z);if(entryDistance>exitDistance)valid=false;
            }
            if(!valid||entryDistance<1.||entryDistance>=distance||!call_identity(b,c.actor)||!call_identity(b,c.component))continue;
            actor=c.actor;component=c.component;distance=entryDistance;
        }
    }
    template<class Pool> bool glow(uint64_t b,uint64_t session,Pool& pool,CallIdentity next) {
        if(next.address==glowing_.address&&next.serial==glowing_.serial)return true;
        while(!materials_.empty()) {
            auto& slot=materials_.back();const int32_t index=int32_t(materials_.size()-1);
            if(call_identity(b,glowing_)) {
                clear();put(0,index);if(!call(b,glowing_,36))return false;
                if(get<uint64_t>(8)==ids_[59].address){clear();put(0,index);put(8,call_identity(b,slot.original));if(!call(b,glowing_,35))return false;}
            }
            if(slot.lease){TargetStrongReferenceOps ops{b,{-1,0,0}};if(pool.release(ops,session,slot.lease)!=StrongLeaseResult::Ok)return false;}
            materials_.pop_back();
        }
        glowing_={};
        if(!call_identity(b,next))return true;
        if(!call_identity(b,ids_[59]))return false;
        clear();if(!call(b,next,38))return false;const auto count=get<int32_t>();if(count<1||count>32)return true;
        glowing_=next;
        for(int32_t index=0;index<count;++index) {
            clear();put(0,index);if(!call(b,next,36))return false;MaterialSlot slot{call_capture(b,get<uint64_t>(8)),0};
            if(slot.original.address){TargetStrongReferenceOps ops{b,slot.original};if(pool.acquire(ops,session,slot.original.address,slot.lease)!=StrongLeaseResult::Ok)return false;}
            materials_.push_back(slot);clear();put(0,index);put(8,ids_[59].address);if(!call(b,next,35))return false;
        }
        return true;
    }
