#pragma once
#include "session_protocol.h"
#include "fixed_invocation.h"
#include "reflected_invocation.h"
#include "pod_schema.h"

// Requires the containing session's exact executable fingerprint gate and SEH
// containment. No live pointers or metadata are cached between calls.
struct TargetPodSchemaOps {
    uint64_t base;
    bool context() const {
        return GetCurrentThreadId()==local_read<DWORD>(base+0x9272d30) &&
            !local_read<uint8_t>(base+0x9272cfc) &&
            !local_read<uint8_t>(base+0x934e968) &&
            !local_read<uint8_t>(base+0x9272cea);
    }
    template<class T> T read(uint64_t address) const { return local_read<T>(address); }
    bool name(uint64_t address,const char* expected) const { return exact_name(base,address,expected); }
    CallIdentity capture(uint64_t object) const { return call_capture(base,object); }
    bool identity(const CallIdentity& id) const {
        return id.address && call_identity(base,id)==id.address &&
            !(local_read<uint32_t>(id.address+8)&0x40000000);
    }
};
