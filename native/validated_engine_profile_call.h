#pragma once
#include "mesh_owner.h"
#include "engine_profile_invocation_policy.h"

// Shared exact native-engine profile invocation. Only the containing owned
// service decides which fixed profile, class and recipient it may operate on.
// Extracted from enemy_spawn_owner.h without widening accepted schemas.
namespace e33_engine_profile_call {
struct TargetOps {
    uint64_t base,function,recipient;const MeshFunction& profile;void* arguments;
    uint64_t process_event=0;
    bool context(){return TargetPodSchemaOps{base}.context();}
    bool identities(){return function&&recipient;}
    bool exact_profile(){
        const auto& p=profile;
        return e33_mesh::named(base,local_read<uint64_t>(function+32),p.owner,"/Script/Engine")&&
            exact_name(base,function+24,p.name)&&local_read<uint32_t>(function+0xb0)==p.flags&&
            local_read<uint16_t>(function+0xb6)==p.params&&local_read<uint16_t>(function+0xb8)==p.returned&&
            local_read<int32_t>(function+0x58)==int(p.extent)&&local_read<uint64_t>(function+0xd8)==base+p.entry&&
            e33_mesh::fields(base,function,p.fields,p.count);
    }
    bool recipient_derives(){return call_derives(base,local_read<uint64_t>(recipient+16),local_read<uint64_t>(function+32));}
    bool dispatch_entry(){
        process_event=local_read<uint64_t>(local_read<uint64_t>(recipient)+0x268);
        return process_event==base+0x1393330||process_event==base+0x332bb90;
    }
    void dispatch_once(){reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(process_event)(
        reinterpret_cast<void*>(recipient),reinterpret_cast<void*>(function),arguments);}
};
inline bool invoke(uint64_t base,CallIdentity function,CallIdentity recipient,const MeshFunction& profile,void* arguments){
    TargetOps ops{base,call_identity(base,function),call_identity(base,recipient),profile,arguments};
    return invoke_validated(ops);
}
}
