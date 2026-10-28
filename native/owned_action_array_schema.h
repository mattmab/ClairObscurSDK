#pragma once
#include "sequence_origin_schema.h"
// Exact shipping root/inner profile from selected readonly descriptors. Source
// identities, complete authored values, private destination and leases remain
// the containing owner's separate responsibilities.
template<class Ops> uint64_t simon_root_array_schema(Ops& ops,uint64_t cls) {
    SequenceOriginSchema<Ops> p(ops);
    if(!ops.is_class(cls) || !p.named(cls,"BP_GameAction_Sequential_C",
        "/Game/Gameplay/GameActionsSystem/SequentialGameAction/BP_GameAction_Sequential") ||
       ops.template read<uint32_t>(cls+0x58)!=64) return 0;
    const auto field=p.field(cls,"GameActionsToExecute","ArrayProperty",48,16,0x6e0de80,549755813893ULL);
    if(!field || ops.template read<uint64_t>(cls+0x50)!=field || ops.template read<uint64_t>(field+24)) return 0;
    const auto inner=ops.template read<uint64_t>(field+0x78);
    if(!inner || ops.template read<uint64_t>(inner)!=ops.base+0x6e136a0 ||
       ops.template read<uint64_t>(inner+16)!=field || !ops.name(inner+32,"GameActionsToExecute") ||
       !ops.name(ops.template read<uint64_t>(inner+8),"StructProperty") ||
       ops.template read<uint32_t>(inner+0x30)!=1 || ops.template read<uint32_t>(inner+0x34)!=16 ||
       ops.template read<uint32_t>(inner+0x44) || ops.template read<uint64_t>(inner+24)) return 0;
    const auto wrapper=ops.template read<uint64_t>(inner+0x70);
    if(!p.named(wrapper,"GameAction_Wrapper","/Script/SandFall") ||
       !p.named(ops.template read<uint64_t>(wrapper+16),"ScriptStruct","/Script/CoreUObject") ||
       ops.template read<uint32_t>(wrapper+0x58)!=16 || ops.template read<uint64_t>(wrapper+0x40)) return 0;
    const auto reference=p.field(wrapper,"GameActionReference","ObjectProperty",0,8,0x6e11d38,6755468160532997ULL);
    const auto inlined=p.field(wrapper,"GameActionInline","ObjectProperty",8,8,0x6e11d38,7318418114478605ULL);
    if(!reference || !inlined || ops.template read<uint64_t>(wrapper+0x50)!=reference ||
       ops.template read<uint64_t>(reference+24)!=inlined || ops.template read<uint64_t>(inlined+24)) return 0;
    const auto action=ops.template read<uint64_t>(reference+0x70);
    if(!ops.is_class(action) || !p.named(action,"GameAction","/Script/SandFall") ||
       ops.template read<uint64_t>(inlined+0x70)!=action) return 0;
    return field;
}
