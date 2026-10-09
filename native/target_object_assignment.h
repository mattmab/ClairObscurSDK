#pragma once
#include "object_assignment.h"
#include "session_protocol.h"
#include "fixed_invocation.h"
#include "reflected_invocation.h"

// Exact executable fingerprint is a prerequisite of the containing session.
// Only the live-observed ObjectProperty vtable is supported. No ClassProperty,
// weak references, instanced-object duplication, custom accessor or container
// ownership is inferred from a pointer-sized layout.
struct TargetObjectAssignmentOps {
    uint64_t base;
    bool context() const {
        return GetCurrentThreadId()==local_read<DWORD>(base+0x9272d30) &&
            !local_read<uint8_t>(base+0x9272cfc) &&
            !local_read<uint8_t>(base+0x934e968) &&
            !local_read<uint8_t>(base+0x9272cea);
    }
    bool identity(const CallIdentity& id) const {
        return id.address && call_identity(base,id)==id.address &&
            !(local_read<uint32_t>(id.address+8)&0x40000000);
    }
    uint64_t validate(const ObjectAssignment& r) const {
        if(!identity(r.target) || !identity(r.owner) || !identity(r.constraint) ||
           (r.expected.address && !identity(r.expected)) ||
           (r.value.address && !identity(r.value)) ||
           !call_is_class(base,r.owner.address) || !call_is_class(base,r.constraint.address)) return 0;
        auto target_class=local_read<uint64_t>(r.target.address+0x10);
        if(!call_derives(base,target_class,r.owner.address) ||
           (r.value.address && !call_derives(base,local_read<uint64_t>(r.value.address+0x10),r.constraint.address))) return 0;
        auto extent=local_read<int32_t>(target_class+0x58);
        if(extent<40 || extent>16777216 || uint64_t(r.offset)+uint64_t(r.dimension)*8>uint64_t(extent)) return 0;
        auto property=local_read<uint64_t>(r.owner.address+0x50);
        for(unsigned steps=0;property && steps<4096;++steps,property=local_read<uint64_t>(property+0x18)) {
            if(!exact_name(base,property+0x20,r.name)) continue;
            if(local_read<uint64_t>(property+0x10)!=(r.owner.address|1) ||
               !exact_name(base,local_read<uint64_t>(property+8),"ObjectProperty") ||
               local_read<uint64_t>(property)!=base+0x6e11d38 ||
               local_read<uint64_t>(property+0x70)!=r.constraint.address ||
               local_read<uint64_t>(property+0x38)!=r.flags ||
               local_read<uint32_t>(property+0x30)!=r.dimension ||
               local_read<uint32_t>(property+0x34)!=8 ||
               local_read<uint32_t>(property+0x44)!=r.offset) return 0;
            auto table=local_read<uint64_t>(property);
            // This vtable's HasSetter/HasGetter slots are constant false. Refuse
            // changed accessors rather than issuing an unverified callback.
            if(local_read<uint64_t>(table+0x78)!=base+0x10044f0 ||
               local_read<uint64_t>(table+0x80)!=base+0x10044f0 ||
               local_read<uint64_t>(table+0x1c0)!=base+0x138a7e0 ||
               local_read<uint64_t>(table+0x1d0)!=base+0x138aad0) return 0;
            return property;
        }
        return 0;
    }
    uint64_t read(const ObjectAssignment& r) const {
        return local_read<uint64_t>(r.target.address+r.offset+uint64_t(r.element)*8);
    }
    void assign(uint64_t property,const ObjectAssignment& r) const {
        // 14138aad0 assembly: RCX=property, RDX=container, R8=value,
        // R9D=array index. The engine computes the destination and handles its
        // conditional reference barrier through virtual+1c0 (14138a7e0).
        reinterpret_cast<void(__fastcall*)(uint64_t,uint64_t,uint64_t,int32_t)>
            (base+0x138aad0)(property,r.target.address,r.value.address,static_cast<int32_t>(r.element));
    }
};
