#pragma once
#include "sequence_origin_journal.h"
#include "sequence_origin_schema.h"
#include "target_pod_schema.h"
#include "retired_world_target.h"

// Exact executable profile, captured from origin-schema.json and
// origin-transform-schema.json. Only the factory actor's private subobject is
// writable; no asset, archetype, CDO, caller-selected object or pointer is used.
class SequenceOriginOwner {
    e33_sequence_origin::Journal journal_;
    e33_sequence_origin::TransformJournal transform_journal_;
    uint8_t mode_=0;
    uint64_t base_=0;
    CallIdentity actor_{},instance_{},controller_{};
    e33_retired_world::Snapshot context_{};
    uint8_t override_=0;
    double original_[12]{};
    bool current() const {
        e33_retired_world::TargetOps ops{base_};e33_retired_world::Snapshot now{};
        return valid(actor_) && valid(controller_) && ops.observe(now) &&
            e33_retired_world::same(now.engine,context_.engine) &&
            e33_retired_world::same(now.viewport,context_.viewport) &&
            e33_retired_world::same(now.world,context_.world) &&
            ops.controller_world(controller_,now.world) &&
            local_read<uint64_t>(actor_.address+32)==local_read<uint64_t>(controller_.address+32);
    }
    bool valid(const CallIdentity& id) const {
        return id.address && call_identity(base_,id)==id.address &&
            !(local_read<uint32_t>(id.address+8)&0x40018030U);
    }
    struct SchemaOps {
        uint64_t base;
        template<class T> T read(uint64_t address) const {return local_read<T>(address);}
        bool registered(uint64_t object) const {return call_capture(base,object).address!=0;}
        bool is_class(uint64_t object) const {return call_is_class(base,object);}
        bool name(uint64_t address,const char* value) const {return exact_name(base,address,value);}
    };
    bool named(uint64_t object,const char* name,const char* package) const {
        SchemaOps ops{base_};return SequenceOriginSchema<SchemaOps>(ops).named(object,name,package);
    }
    uint64_t field(uint64_t owner,const char* name,const char* type,uint32_t offset,
                   uint32_t width,uint64_t table,uint64_t flags) const {
        SchemaOps ops{base_};return SequenceOriginSchema<SchemaOps>(ops).field(owner,name,type,offset,width,table,flags);
    }
    bool transform(uint64_t object) const {
        SchemaOps ops{base_};return SequenceOriginSchema<SchemaOps>(ops).transform(object);
    }
    bool schema() const {
        if(!valid(actor_) || !valid(instance_)) return false;
        SchemaOps ops{base_};
        return SequenceOriginSchema<SchemaOps>(ops).private_instance(actor_.address,instance_.address);
    }
    struct Ops {
        SequenceOriginOwner& self;
        bool prove_private_fresh() {
            TargetPodSchemaOps context{self.base_};
            if(!context.context() || !self.current() || !self.schema()) return false;
            self.override_=local_read<uint8_t>(self.actor_.address+760);
            if(self.override_&2) return false;
            std::memcpy(self.original_,reinterpret_cast<const void*>(self.instance_.address+64),96);
            const unsigned zero[]={0,1,2,4,5,6};
            for(auto i:zero) if(self.original_[i]!=0.) return false;
            if(self.original_[3]!=1. || self.original_[8]!=1. || self.original_[9]!=1. || self.original_[10]!=1.) return false;
            return self.current() && self.schema() && context.context() &&
                local_read<uint8_t>(self.actor_.address+760)==self.override_ &&
                !std::memcmp(self.original_,reinterpret_cast<const void*>(self.instance_.address+64),96);
        }
        bool write_translation(const SequenceOriginPacket& p) {
            // Journal is already uncertain. Preserve quaternion, scale, padding,
            // and every unrelated packed bool bit.
            std::memcpy(reinterpret_cast<void*>(self.instance_.address+96),&p.x,24);
            *reinterpret_cast<uint8_t*>(self.actor_.address+760)=uint8_t(self.override_|2);
            return true;
        }
        bool verify_translation(const SequenceOriginPacket& p) {
            TargetPodSchemaOps context{self.base_};auto expected=self.original_;
            double value[12];std::memcpy(value,expected,96);value[4]=p.x;value[5]=p.y;value[6]=p.z;
            return context.context() && self.current() && self.schema() &&
                local_read<uint8_t>(self.actor_.address+760)==uint8_t(self.override_|2) &&
                !std::memcmp(value,reinterpret_cast<const void*>(self.instance_.address+64),96);
        }
        bool prove_private_current(const SequenceOriginPacket& p) {return verify_translation(p);}
        bool write_transform(const SequenceOriginTransformPacket& p) {
            double quaternion[4]{};sequence_origin_transform_quaternion(p,quaternion);
            std::memcpy(reinterpret_cast<void*>(self.instance_.address+64),quaternion,32);
            std::memcpy(reinterpret_cast<void*>(self.instance_.address+96),&p.x,24);
            *reinterpret_cast<uint8_t*>(self.actor_.address+760)=uint8_t(self.override_|2);
            return true;
        }
        bool verify_transform(const SequenceOriginTransformPacket& p) {
            TargetPodSchemaOps context{self.base_};
            double value[12];std::memcpy(value,self.original_,96);
            sequence_origin_transform_quaternion(p,value);
            value[4]=p.x;value[5]=p.y;value[6]=p.z;
            return context.context() && self.current() && self.schema() &&
                local_read<uint8_t>(self.actor_.address+760)==uint8_t(self.override_|2) &&
                !std::memcmp(value,reinterpret_cast<const void*>(self.instance_.address+64),96);
        }
        bool prove_transform_current(const SequenceOriginTransformPacket& p) {return verify_transform(p);}
    };
public:
    bool before_evaluation() {
        // Unconfigured owners preserve the existing sequence contract. Once
        // private origin context is captured, public evaluation cannot outlive
        // that controller/world. Internal cleanup uses separate exact admission.
        return (!actor_.address || current()) && journal_.before_evaluation() && transform_journal_.before_evaluation();
    }
    uint32_t configure(uint64_t base,const CallIdentity& actor,const CallIdentity& controller,const SequenceOriginPacket& p) {
        if(mode_!=0)return 1591;
        base_=base;actor_=actor;controller_=controller;
        e33_retired_world::TargetOps context{base};
        if(!valid(actor_) || !valid(controller_) || !context.observe(context_) || !current()) return 1591;
        instance_=call_capture(base,local_read<uint64_t>(actor.address+768));
        Ops ops{*this};const auto result=journal_.configure(ops,p);
        if(result!=e33_sequence_origin::Result::rejected)mode_=1;
        return result==e33_sequence_origin::Result::ok ? 0 :
            result==e33_sequence_origin::Result::unknown ? 1593 : 1591;
    }
    uint32_t update(const SequenceOriginPacket& p) {
        if(mode_!=1)return 1591;
        Ops ops{*this};const auto result=journal_.update(ops,p);
        return result==e33_sequence_origin::Result::ok ? 0 :
            result==e33_sequence_origin::Result::unknown ? 1593 : 1591;
    }
    uint32_t configure_transform(uint64_t base,const CallIdentity& actor,const CallIdentity& controller,const SequenceOriginTransformPacket& p) {
        if(mode_!=0)return 1591;
        base_=base;actor_=actor;controller_=controller;
        e33_retired_world::TargetOps context{base};
        if(!valid(actor_) || !valid(controller_) || !context.observe(context_) || !current())return 1591;
        instance_=call_capture(base,local_read<uint64_t>(actor.address+768));
        Ops ops{*this};const auto result=transform_journal_.configure(ops,p);
        if(result!=e33_sequence_origin::Result::rejected)mode_=2;
        return result==e33_sequence_origin::Result::ok ? 0 :
            result==e33_sequence_origin::Result::unknown ? 1593 : 1591;
    }
    uint32_t update_transform(const SequenceOriginTransformPacket& p) {
        if(mode_!=2)return 1591;
        Ops ops{*this};const auto result=transform_journal_.update(ops,p);
        return result==e33_sequence_origin::Result::ok ? 0 :
            result==e33_sequence_origin::Result::unknown ? 1593 : 1591;
    }
};
