#pragma once
#include "enum_schema.h"
#include "sequence_settings_profile.h"

// Exact reflection profile generated from this executable. Recursion is bounded
// to the two explicitly named child structures; no opaque bytes are accepted.
template<class Ops>
bool sequence_settings_schema(Ops& ops,const CallIdentity& id,const char* name,unsigned depth=0) {
    if(depth>1 || !ops.context() || !ops.identity(id)) return false;
    const SequenceSettingField* fields=nullptr; unsigned count=0,width=0;
    if(!std::strcmp(name,"MovieSceneSequencePlaybackSettings") && depth==0) {
        fields=fields_MovieSceneSequencePlaybackSettings;
        count=unsigned(sizeof(fields_MovieSceneSequencePlaybackSettings)/sizeof(*fields)); width=40;
    } else if(!std::strcmp(name,"MovieSceneSequenceLoopCount") && depth==1) {
        fields=fields_MovieSceneSequenceLoopCount; count=1; width=4;
    } else if(!std::strcmp(name,"MovieSceneSequenceTickInterval") && depth==1) {
        fields=fields_MovieSceneSequenceTickInterval; count=4; width=12;
    } else return false;
    const auto object=id.address;
    if(!pod_registered(ops,object) || !ops.name(object+0x18,name) ||
       !pod_package(ops,ops.template read<uint64_t>(object+0x20),"/Script/MovieScene") ||
       ops.template read<uint64_t>(object+0x40) || ops.template read<uint32_t>(object+0x58)!=width) return false;
    const auto cls=ops.template read<uint64_t>(object+0x10);
    if(!pod_registered(ops,cls) || !ops.name(cls+0x18,"ScriptStruct") ||
       !pod_package(ops,ops.template read<uint64_t>(cls+0x20),"/Script/CoreUObject")) return false;
    auto field=ops.template read<uint64_t>(object+0x50);
    for(unsigned i=0;i<count;++i) {
        const auto& f=fields[i];
        if(!field || ops.template read<uint64_t>(field)!=ops.base+f.table ||
           ops.template read<uint64_t>(field+0x10)!=(object|1) ||
           !ops.name(field+0x20,f.name) || !ops.name(ops.template read<uint64_t>(field+8),f.type) ||
           ops.template read<uint32_t>(field+0x30)!=1 || ops.template read<uint32_t>(field+0x34)!=f.width ||
           ops.template read<uint64_t>(field+0x38)!=f.flags || ops.template read<uint32_t>(field+0x44)!=f.offset) return false;
        if(f.boolean && ops.template read<uint32_t>(field+0x70)!=f.boolean) return false;
        if(!std::strcmp(f.type,"StructProperty")) {
            if(!sequence_settings_schema(ops,ops.capture(ops.template read<uint64_t>(field+0x70)),f.nested,depth+1)) return false;
        } else if(!std::strcmp(f.type,"EnumProperty")) {
            const auto e=ops.capture(ops.template read<uint64_t>(field+0x78));
            if(!validate_byte_enum_parameter(ops,field,e) || !ops.name(e.address+0x18,f.nested) ||
               !pod_package(ops,ops.template read<uint64_t>(e.address+0x20),"/Script/MovieScene")) return false;
            const char* members[]={"EMovieSceneCompletionModeOverride::None","EMovieSceneCompletionModeOverride::ForceKeepState",
                "EMovieSceneCompletionModeOverride::ForceRestoreState","EMovieSceneCompletionModeOverride::EMovieSceneCompletionModeOverride_MAX"};
            if(ops.template read<int32_t>(e.address+0x48)!=4) return false;
            auto data=ops.template read<uint64_t>(e.address+0x40);
            for(unsigned j=0;j<4;++j)
                if(!ops.name(data+16*j,members[j]) || ops.template read<int64_t>(data+16*j+8)!=j) return false;
        }
        field=ops.template read<uint64_t>(field+0x18);
    }
    return !field && ops.identity(id) && ops.context();
}
