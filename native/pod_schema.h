#pragma once
#include "invocation_protocol.h"
#include "pod_value_codec.h"

// Exact build-specific schema gate. Ops supplies checked registry observations,
// names, reads and the game-thread/GC/shutdown guard. The caller must contain
// access faults. This performs no engine dispatch, allocation or mutation.
template<class Ops>
bool pod_registered(Ops& ops,uint64_t object) {
    return object && ops.capture(object).address==object &&
        !(ops.template read<uint32_t>(object+8)&0x40000000);
}
template<class Ops>
bool pod_package(Ops& ops,uint64_t object,const char* name) {
    if(!pod_registered(ops,object) || !ops.name(object+0x18,name) ||
       ops.template read<uint64_t>(object+0x20)) return false;
    auto cls=ops.template read<uint64_t>(object+0x10);
    return pod_registered(ops,cls) && ops.name(cls+0x18,"Package");
}
template<class Ops>
bool validate_pod_schema(Ops& ops,PodValueKind kind,const CallIdentity& identity) {
    const auto width=pod_value_width(kind);
    if(!width || !ops.context() || !ops.identity(identity)) return false;
    const auto object=identity.address;
    const char* struct_name=nullptr;
    const char* package=nullptr;
    const char* fields[4]{};
    uint32_t count=0, component=0;
    uint64_t table=0, flags=0;
    const char* field_type=nullptr;
    switch(kind) {
    case PodValueKind::Vector2D:
        struct_name="Vector2D"; package="/Script/CoreUObject";
        fields[0]="X"; fields[1]="Y"; count=2; component=8;
        table=0x6e11788; flags=6755469251052037ULL; field_type="DoubleProperty"; break;
    case PodValueKind::LinearColor:
        struct_name="LinearColor"; package="/Script/CoreUObject";
        fields[0]="R"; fields[1]="G"; fields[2]="B"; fields[3]="A";
        count=4; component=4; table=0x6e11560; flags=6755469251052037ULL;
        field_type="FloatProperty"; break;
    case PodValueKind::Margin:
        struct_name="Margin"; package="/Script/SlateCore";
        fields[0]="Left"; fields[1]="Top"; fields[2]="Right"; fields[3]="Bottom";
        count=4; component=4; table=0x6e11560; flags=6755469234274821ULL;
        field_type="FloatProperty"; break;
    case PodValueKind::Anchors:
        struct_name="Anchors"; package="/Script/Slate";
        fields[0]="Minimum"; fields[1]="Maximum"; count=2; component=16;
        table=0x6e136a0; flags=6755469234274821ULL; field_type="StructProperty"; break;
    default: return false;
    }
    if(!pod_registered(ops,object) || !ops.name(object+0x18,struct_name) ||
       !pod_package(ops,ops.template read<uint64_t>(object+0x20),package) ||
       ops.template read<uint64_t>(object+0x40) ||
       ops.template read<uint32_t>(object+0x58)!=width) return false;
    auto cls=ops.template read<uint64_t>(object+0x10);
    if(!pod_registered(ops,cls) || !ops.name(cls+0x18,"ScriptStruct") ||
       !pod_package(ops,ops.template read<uint64_t>(cls+0x20),"/Script/CoreUObject")) return false;
    auto field=ops.template read<uint64_t>(object+0x50);
    uint64_t nested_vector=0;
    for(uint32_t i=0;i<count;++i) {
        if(!field || ops.template read<uint64_t>(field)!=ops.base+table ||
           ops.template read<uint64_t>(field+0x10)!=(object|1) ||
           !ops.name(field+0x20,fields[i]) ||
           !ops.name(ops.template read<uint64_t>(field+8),field_type) ||
           ops.template read<uint32_t>(field+0x30)!=1 ||
           ops.template read<uint32_t>(field+0x34)!=component ||
           ops.template read<uint64_t>(field+0x38)!=flags ||
           ops.template read<uint32_t>(field+0x44)!=i*component) return false;
        if(kind==PodValueKind::Anchors) {
            auto nested=ops.template read<uint64_t>(field+0x70);
            if(!nested || (nested_vector && nested_vector!=nested) ||
               !validate_pod_schema(ops,PodValueKind::Vector2D,ops.capture(nested))) return false;
            nested_vector=nested;
        }
        field=ops.template read<uint64_t>(field+0x18);
    }
    // Reject extra fields and cycles; recursion is only Anchors -> Vector2D.
    return !field && ops.identity(identity) && ops.context();
}

template<class Ops>
bool validate_pod_parameter(Ops& ops,uint64_t property,PodValueKind kind,const CallIdentity& identity) {
    // The invocation gate separately checks parameter owner, flags, dimensions,
    // offset and extent. This binds its struct reference to the verified profile.
    return property && ops.context() &&
        ops.template read<uint64_t>(property)==ops.base+0x6e136a0 &&
        ops.name(ops.template read<uint64_t>(property+8),"StructProperty") &&
        ops.template read<uint64_t>(property+0x70)==identity.address &&
        ops.template read<uint32_t>(property+0x34)==pod_value_width(kind) &&
        validate_pod_schema(ops,kind,identity);
}
