    #include "builder_gpu_state.h"
    uint64_t gpu_property(uint64_t b,CallIdentity object,const char* name,const GpuProperty*& descriptor,uint64_t& owner) {
        descriptor=nullptr;if(!call_identity(b,object))return 0;
        for(const auto& p:gpu_properties)if(!std::strcmp(p.name,name)){descriptor=&p;break;}
        if(!descriptor)return 0;const auto& p=*descriptor;
        auto cls=local_read<uint64_t>(object.address+16);
        for(int sampleDepth=0;cls&&sampleDepth<64;++sampleDepth,cls=local_read<uint64_t>(cls+0x40)) {
            auto f=local_read<uint64_t>(cls+0x50);
            for(int n=0;f&&n<512;++n,f=local_read<uint64_t>(f+24)) {
                if(!exact_name(b,f+32,name))continue;
                if(local_read<uint64_t>(f+16)!=(cls|1)||local_read<uint64_t>(f)!=b+p.table||!exact_name(b,local_read<uint64_t>(f+8),p.type)||
                   local_read<uint32_t>(f+0x44)!=p.offset||local_read<uint32_t>(f+0x34)!=p.width||local_read<uint32_t>(f+0x30)!=1||local_read<uint64_t>(f+0x38)!=p.flags||
                   p.offset+p.width>uint32_t(local_read<int32_t>(cls+0x58))||(p.boolean&&local_read<uint32_t>(f+0x70)!=p.boolean))return 0;
                owner=cls;return f;
            }
        }
        return 0;
    }
    bool gpu_setting(uint64_t b,const char* name,uint64_t value) {
        // Only this mod's newly spawned capture component may be configured.
        if(!call_identity(b,gpu_actor_)||!call_identity(b,gpu_capture_))return false;
        clear();if(!call(b,gpu_capture_,18)||get<uint64_t>()!=gpu_actor_.address)return false;
        const GpuProperty* p=nullptr;uint64_t owner=0;const auto field=gpu_property(b,gpu_capture_,name,p,owner);if(!field)return false;
        if(!std::strcmp(p->type,"ObjectProperty")) {
            ObjectAssignment r{};r.target=gpu_capture_;r.owner=call_capture(b,owner);r.constraint=call_capture(b,local_read<uint64_t>(field+0x70));
            r.expected=call_capture(b,local_read<uint64_t>(gpu_capture_.address+p->offset));r.value=call_capture(b,value);r.flags=p->flags;r.offset=p->offset;r.dimension=1;strcpy_s(r.name,name);
            TargetObjectAssignmentOps ops{b};return assign_object_property(ops,r)==ObjectAssignmentResult::Ok;
        }
        auto* dest=reinterpret_cast<uint8_t*>(gpu_capture_.address+p->offset);
        if(p->boolean){const auto mask=uint8_t(p->boolean>>24),bit=uint8_t(p->boolean>>16);*dest=uint8_t((*dest&~mask)|(value?bit:0));}
        else if(p->width==1||p->width==4)std::memcpy(dest,&value,p->width);else return false;
        return true;
    }
    template<class Pool> bool gpu_setup(uint64_t b,uint64_t session,Pool& pool) {
        gpu_error_=0;gpu_pending_=gpu_completed_=gpu_last_capture_=gpu_ready_time_=0;gpu_query_active_=false;gpu_flights_.clear();gpu_candidates_.clear();gpu_ready_component_={};
        if(!gpu_bridge_.start(257,259,2)){gpu_error_=gpu_bridge_.error();return false;}
        clear();put(0,ids_[0].address);put(8,ids_[80].address);transform(args_+16,position_);args_[112]=1;
        if(!call(b,ids_[4],0))return false;gpu_actor_=call_capture(b,get<uint64_t>(136));
        if(!gpu_actor_.address)return false;
        TargetStrongReferenceOps actorOps{b,gpu_actor_};if(pool.acquire(actorOps,session,gpu_actor_.address,gpu_actor_lease_)!=StrongLeaseResult::Ok)return false;
        const GpuProperty* p=nullptr;uint64_t owner=0;if(!gpu_property(b,gpu_actor_,"CaptureComponent2D",p,owner))return false;
        gpu_capture_=call_capture(b,local_read<uint64_t>(gpu_actor_.address+p->offset));if(!gpu_capture_.address)return false;
        float fov=1.f,clip=1.f;uint32_t fovBits=0,clipBits=0;std::memcpy(&fovBits,&fov,4);std::memcpy(&clipBits,&clip,4);
        if(!gpu_setting(b,"bCaptureEveryFrame",0)||!gpu_setting(b,"bCaptureOnMovement",0)||!gpu_setting(b,"bUseRayTracingIfEnabled",0)||!gpu_setting(b,"CaptureSource",4)||!gpu_setting(b,"PrimitiveRenderMode",2)||!gpu_setting(b,"FOVAngle",fovBits)||!gpu_setting(b,"bOverride_CustomNearClippingPlane",1)||!gpu_setting(b,"CustomNearClippingPlane",clipBits))return false;
        clear();put(0,gpu_actor_.address);transform(args_+16,position_);if(!call(b,ids_[4],1))return false;
        clear();put(0,ids_[0].address);put(8,int32_t(257));put(12,int32_t(259));args_[16]=7;
        if(!call(b,ids_[83],44))return false;gpu_target_=call_capture(b,get<uint64_t>(40));if(!gpu_target_.address)return false;
        TargetStrongReferenceOps targetOps{b,gpu_target_};if(pool.acquire(targetOps,session,gpu_target_.address,gpu_target_lease_)!=StrongLeaseResult::Ok)return false;
        return gpu_setting(b,"TextureTarget",gpu_target_.address);
    }
    template<class Pool> bool gpu_stop(uint64_t b,uint64_t session,Pool& pool) {
        if(!gpu_bridge_.stop())return false;
        if(call_identity(b,gpu_actor_)){clear();if(!call(b,gpu_actor_,2))return false;}gpu_actor_={};gpu_capture_={};
        if(call_identity(b,gpu_target_)){clear();put(0,gpu_target_.address);if(!call(b,ids_[83],45))return false;}gpu_target_={};
        TargetStrongReferenceOps ops{b,{-1,0,0}};
        if(gpu_actor_lease_){if(pool.release(ops,session,gpu_actor_lease_)!=StrongLeaseResult::Ok)return false;gpu_actor_lease_=0;}
        if(gpu_target_lease_){if(pool.release(ops,session,gpu_target_lease_)!=StrongLeaseResult::Ok)return false;gpu_target_lease_=0;}
        gpu_pending_=0;gpu_query_active_=false;gpu_flights_.clear();gpu_candidates_.clear();gpu_ready_component_={};return true;
    }
    #include "builder_gpu_pick.h"
