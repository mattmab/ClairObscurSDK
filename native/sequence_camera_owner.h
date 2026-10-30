#pragma once
#include "sequence_camera_journal.h"
#include "sequence_camera_protocol.h"
#include "strong_lease_pool.h"
#include "target_strong_reference.h"
#include "stable_identity.h"

// Build-specific, opt-in camera restoration. Reads ONLY the three reflected
// object references; never copies or writes the 2048-byte POV structure.
class SequenceCameraOwner {
    using Result=e33_camera::Result;
    StrongLeasePool<10> leases_; // 5 profile + controller/manager/level/saved_target + owned camera.
    e33_camera::Journal<CallIdentity> journal_;
    uint64_t base_=0,session_=0;
    CallIdentity pc_class_{},manager_class_{},view_struct_{},actor_class_{},setter_{};
    CallIdentity controller_{},manager_{},level_{},original_{},player_{},owned_{};
    CallPacket restore_{};
    bool (*owned_proof_)(uint64_t,const CallIdentity&,const CallIdentity&)=nullptr;
    bool pool_open_=false;
    static bool same(const CallIdentity& a,const CallIdentity& b) {return !std::memcmp(&a,&b,sizeof(a));}
    bool valid(const CallIdentity& id) const {
        return id.address && call_identity(base_,id)==id.address && !(local_read<uint32_t>(id.address+8)&0x40000000);
    }
    bool named(uint64_t object,const char* name,const char* package) const {
        auto id=call_capture(base_,object);if(!valid(id) || !exact_name(base_,object+24,name)) return false;
        auto outer=call_capture(base_,local_read<uint64_t>(object+32));
        return valid(outer) && exact_name(base_,outer.address+24,package);
    }
    uint64_t field(uint64_t owner,const char* name,uint32_t offset,uint32_t width,uint64_t table,uint64_t flags) const {
        auto p=local_read<uint64_t>(owner+0x50);
        for(unsigned i=0;p && i<128;++i,p=local_read<uint64_t>(p+0x18)) {
            if(!exact_name(base_,p+0x20,name)) continue;
            return local_read<uint64_t>(p)==base_+table && local_read<uint64_t>(p+0x10)==(owner|1) &&
                local_read<uint32_t>(p+0x30)==1 && local_read<uint32_t>(p+0x34)==width &&
                local_read<uint64_t>(p+0x38)==flags && local_read<uint32_t>(p+0x44)==offset ? p : 0;
        }
        return 0;
    }
    bool retain(CallIdentity& id) {
        TargetStrongReferenceOps ops{base_,id};uint64_t token{};
        return leases_.acquire(ops,session_,id.address,token)==StrongLeaseResult::Ok && stabilize_retained_identity(ops,id);
    }
    bool schema() const {
        if(!valid(pc_class_) || !valid(manager_class_) || !valid(view_struct_) || !valid(actor_class_) || !valid(setter_)) return false;
        if(!named(pc_class_.address,"PlayerController","/Script/Engine") || !call_is_class(base_,pc_class_.address) ||
           !named(manager_class_.address,"PlayerCameraManager","/Script/Engine") || !call_is_class(base_,manager_class_.address) ||
           !named(actor_class_.address,"Actor","/Script/Engine") || !call_is_class(base_,actor_class_.address) ||
           !named(view_struct_.address,"TViewTarget","/Script/Engine") ||
           !named(local_read<uint64_t>(view_struct_.address+16),"ScriptStruct","/Script/CoreUObject") ||
           local_read<uint32_t>(view_struct_.address+0x58)!=2080 || local_read<uint64_t>(view_struct_.address+0x40)) return false;
        auto manager=field(pc_class_.address,"PlayerCameraManager",840,8,0x6e11d38,79938962105303572ULL);
        auto view=field(manager_class_.address,"ViewTarget",800,2080,0x6e136a0,4503599627378688ULL);
        auto pending=field(manager_class_.address,"PendingViewTarget",2880,2080,0x6e136a0,4503599627378688ULL);
        auto target_field=field(view_struct_.address,"Target",0,8,0x6e11d38,79938962105303557ULL);
        return manager && view && pending && target_field &&
            local_read<uint64_t>(manager+0x70)==manager_class_.address &&
            local_read<uint64_t>(view+0x70)==view_struct_.address && local_read<uint64_t>(pending+0x70)==view_struct_.address &&
            local_read<uint64_t>(target_field+0x70)==actor_class_.address;
    }
    bool setter_plan(const CallPacket& c) {
        if(!camera_restore_packet(c) || !valid(c.target) || !valid(c.function)) return false;
        if(!exact_name(base_,c.function.address+24,"SetViewTargetWithBlend")) return false;
        pc_class_=call_capture(base_,local_read<uint64_t>(c.function.address+32));
        actor_class_=c.fields[0].constraint;setter_=c.function;
        if(!valid(pc_class_) || !call_is_class(base_,pc_class_.address) || !named(pc_class_.address,"PlayerController","/Script/Engine")) return false;
        auto manager=field(pc_class_.address,"PlayerCameraManager",840,8,0x6e11d38,79938962105303572ULL);
        if(!manager) return false;
        manager_class_=call_capture(base_,local_read<uint64_t>(manager+0x70));
        if(!valid(manager_class_)) return false;
        auto view=field(manager_class_.address,"ViewTarget",800,2080,0x6e136a0,4503599627378688ULL);
        if(!view) return false;view_struct_=call_capture(base_,local_read<uint64_t>(view+0x70));
        if(!schema()) return false;
        auto check=c;return !reflected_call(base_,check,nullptr,nullptr,nullptr,nullptr,true);
    }
    bool associated() const {
        return schema() && valid(controller_) && valid(manager_) && valid(level_) &&
            call_derives(base_,local_read<uint64_t>(controller_.address+16),pc_class_.address) &&
            call_derives(base_,local_read<uint64_t>(manager_.address+16),manager_class_.address) &&
            local_read<uint64_t>(controller_.address+32)==level_.address &&
            local_read<uint64_t>(controller_.address+840)==manager_.address;
    }
    struct Ops {
        SequenceCameraOwner& self;
        bool context() {TargetStrongReferenceOps ops{self.base_,{}};return ops.can_assign();}
        bool same(const CallIdentity&a,const CallIdentity&b) {return SequenceCameraOwner::same(a,b);}
        Result capture(CallIdentity& controller,CallIdentity& saved_target) {
            if(!context() || !self.valid(controller)) return Result::rejected;
            self.controller_=controller;
            self.level_=call_capture(self.base_,local_read<uint64_t>(controller.address+32));
            self.manager_=call_capture(self.base_,local_read<uint64_t>(controller.address+840));
            if(!self.associated() || local_read<uint64_t>(self.manager_.address+2880)) return Result::rejected;
            self.original_=call_capture(self.base_,local_read<uint64_t>(self.manager_.address+800));
            if(!self.valid(self.original_) || !call_derives(self.base_,local_read<uint64_t>(self.original_.address+16),self.actor_class_.address)) return Result::rejected;
            if(self.leases_.begin(self.session_)!=StrongLeaseResult::Ok) return Result::rejected;
            self.pool_open_=true;
            CallIdentity* held[]={&self.pc_class_,&self.manager_class_,&self.view_struct_,&self.actor_class_,&self.setter_,
                &self.controller_,&self.manager_,&self.level_,&self.original_};
            for(auto* id:held) if(!self.retain(*id)) return Result::unknown;
            if(!self.associated() || local_read<uint64_t>(self.manager_.address+800)!=self.original_.address ||
               local_read<uint64_t>(self.manager_.address+2880)) return Result::unknown;
            controller=self.controller_;saved_target=self.original_;
            self.restore_.target=controller;self.restore_.function=self.setter_;
            self.restore_.fields[0].constraint=self.actor_class_;
            return Result::ok;
        }
        Result current(const CallIdentity& controller,CallIdentity& current) {
            if(!context()) return Result::deferred;
            if(!same(controller,self.controller_) || !self.associated() || local_read<uint64_t>(self.manager_.address+2880)) return Result::rejected;
            current=call_capture(self.base_,local_read<uint64_t>(self.manager_.address+800));
            return self.valid(current) ? Result::ok : Result::rejected;
        }
        bool proven_owned(const CallIdentity& camera) {
            return context() && self.associated() && self.valid(camera) && self.valid(self.player_) && self.owned_proof_ &&
                self.owned_proof_(self.base_,self.player_,camera);
        }
        bool retain_owned(const CallIdentity& camera) {
            self.owned_=camera;return camera.serial>0 && self.retain(self.owned_) && same(camera,self.owned_);
        }
        Result restore(const CallIdentity& controller,const CallIdentity& saved_target) {
            if(!context()) return Result::deferred;
            if(!same(controller,self.controller_) || !same(saved_target,self.original_) || !self.associated() || !self.valid(saved_target)) return Result::rejected;
            auto call=self.restore_;call.object_count=1;call.objects[0]={0,saved_target};
            const auto error=reflected_call(self.base_,call);
            if(error==201 && call.outcome==CallNotDispatched) return Result::deferred;
            if(error || call.outcome!=CallDispatchReturned) return Result::unknown;
            CallIdentity actual{};
            return current(controller,actual)==Result::ok && same(actual,saved_target) ? Result::ok : Result::unknown;
        }
        Result release() {
            if(!self.pool_open_) return Result::ok;
            TargetStrongReferenceOps ops{self.base_,{}};auto result=self.leases_.close(ops,self.session_);
            if(result==StrongLeaseResult::Deferred) return Result::deferred;
            if(result!=StrongLeaseResult::Ok) return Result::unknown;
            self.pool_open_=false;return Result::ok;
        }
    };
public:
    bool permits_editor_camera(const CallIdentity& camera)const {
        return associated() && valid(camera) && valid(player_) && owned_proof_ && owned_proof_(base_,player_,camera);
    }
    uint32_t retire(bool positively_retired) {
        Ops ops{*this};const auto result=journal_.retire(ops,positively_retired);
        if(result==Result::deferred)return 407;
        if(result!=Result::ok)return 1573;
        owned_proof_=nullptr;player_={};return 0;
    }
    bool owns_camera(const CallIdentity& camera)const{return same(camera,owned_);}
    uint32_t focus_owned_view(){
        Ops ops{*this};CallIdentity current{};
        if(!ops.proven_owned(owned_) || ops.current(controller_,current)!=Result::ok)return 1793;
        if(same(current,owned_))return 0;
        auto view=restore_;view.object_count=1;view.objects[0]={0,owned_};
        return reflected_call(base_,view) || view.outcome!=CallDispatchReturned?1793:0;
    }
    uint32_t restore_view(){Ops ops{*this};return ops.restore(controller_,original_)==Result::ok?0:1793;}
    bool ready() const {return journal_.ready();}
    bool active() const {return journal_.active() || pool_open_;}
    uint32_t private_active() const {return leases_.active();}
    uint32_t private_peak() const {return leases_.peak();}
    uint32_t arm(uint64_t base,uint64_t owner,const CallIdentity& controller,const CallPacket& restore) {
        if(active() || !owner || controller.serial<=0) return 1571;
        base_=base;session_=owner;TargetStrongReferenceOps guard{base,{}};
        if(!guard.can_assign()) return 407;
        if(!same(controller,restore.target) || !setter_plan(restore)) return 1571;
        restore_=restore;Ops ops{*this};
        const auto result=journal_.arm(ops,controller);
        return result==Result::ok ? 0 : 1573;
    }
    bool created(const CallIdentity& player) {player_=player;return journal_.created();}
    // ONLY a native, positively profiled spawn/track adapter may supply proof.
    // No Python command accepts a purported camera or a proof callback address.
    uint32_t admit_owned(const CallIdentity& camera,bool (*proof)(uint64_t,const CallIdentity&,const CallIdentity&)) {
        if(!proof || owned_proof_) return 1571;
        owned_proof_=proof;Ops ops{*this};
        return journal_.admit_owned(ops,camera)==Result::ok ? 0 : 1573;
    }
    uint32_t close() {
        Ops ops{*this};const auto result=journal_.close(ops);
        if(result==Result::deferred) return 407;
        if(result!=Result::ok) return 1573;
        owned_proof_=nullptr;player_={};return 0;
    }
};
