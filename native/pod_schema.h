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
// Exact finite hierarchy from evidence/v53-frame-time-schema.json. No client
// layouts, arbitrary recursion, owned storage, pointers, or engine mutation.
template<class Ops> bool validate_pod_schema(Ops& ops,PodValueKind kind,const CallIdentity& identity);
template<class Ops>
bool validate_frame_time_schema(Ops& ops,PodValueKind kind,const CallIdentity& identity) {
    if(!ops.context() || !ops.identity(identity)) return false;
    const char* name=nullptr; const char* fields[3]{};
    PodValueKind children[3]{}; uint32_t widths[3]{},offsets[3]{};
    uint64_t flags[3]{},tables[3]{}; const char* types[3]{}; unsigned count=0;
    switch(kind) {
    case PodValueKind::Timespan: name="Timespan"; count=0; break;
    case PodValueKind::FrameNumber:
        name="FrameNumber"; count=1; fields[0]="Value"; widths[0]=4;
        flags[0]=6755469234274821ULL; tables[0]=0x6e10a98; types[0]="IntProperty"; break;
    case PodValueKind::FrameRate:
        name="FrameRate"; count=2; fields[0]="Numerator"; fields[1]="Denominator";
        for(unsigned i=0;i<2;++i) { widths[i]=4; offsets[i]=4*i;
            flags[i]=6755469234274821ULL; tables[i]=0x6e10a98; types[i]="IntProperty"; } break;
    case PodValueKind::FrameTime:
        name="FrameTime"; count=2; fields[0]="FrameNumber"; fields[1]="SubFrame";
        widths[0]=widths[1]=4; offsets[1]=4; children[0]=PodValueKind::FrameNumber;
        flags[0]=6755468160532484ULL; flags[1]=20266268116386308ULL;
        tables[0]=0x6e136a0; tables[1]=0x6e11560; types[0]="StructProperty"; types[1]="FloatProperty"; break;
    case PodValueKind::QualifiedFrameTime:
        name="QualifiedFrameTime"; count=2; fields[0]="Time"; fields[1]="Rate";
        widths[0]=widths[1]=8; offsets[1]=8;
        children[0]=PodValueKind::FrameTime; children[1]=PodValueKind::FrameRate;
        flags[0]=6755468160532484ULL; flags[1]=6755469234274820ULL;
        tables[0]=tables[1]=0x6e136a0; types[0]=types[1]="StructProperty"; break;
    case PodValueKind::BindingID:
        name="MovieSceneObjectBindingID";count=3;fields[0]="Guid";fields[1]="SequenceID";fields[2]="ResolveParentIndex";
        widths[0]=16;widths[1]=widths[2]=4;offsets[1]=16;offsets[2]=20;children[0]=PodValueKind::Guid;
        flags[0]=20266268116386305ULL;flags[1]=flags[2]=20266268116386304ULL;
        tables[0]=0x6e136a0;tables[1]=tables[2]=0x6e10a98;
        types[0]="StructProperty";types[1]=types[2]="IntProperty";break;
    default: return false;
    }
    const auto object=identity.address;
    if(!pod_registered(ops,object) || !ops.name(object+0x18,name) ||
       !pod_package(ops,ops.template read<uint64_t>(object+0x20),kind==PodValueKind::BindingID?"/Script/MovieScene":"/Script/CoreUObject") ||
       ops.template read<uint64_t>(object+0x40) ||
       ops.template read<uint32_t>(object+0x58)!=pod_value_width(kind)) return false;
    const auto cls=ops.template read<uint64_t>(object+0x10);
    if(!pod_registered(ops,cls) || !ops.name(cls+0x18,"ScriptStruct") ||
       !pod_package(ops,ops.template read<uint64_t>(cls+0x20),"/Script/CoreUObject")) return false;
    auto field=ops.template read<uint64_t>(object+0x50);
    for(unsigned i=0;i<count;++i) {
        if(!field || ops.template read<uint64_t>(field)!=ops.base+tables[i] ||
           ops.template read<uint64_t>(field+0x10)!=(object|1) || !ops.name(field+0x20,fields[i]) ||
           !ops.name(ops.template read<uint64_t>(field+8),types[i]) ||
           ops.template read<uint32_t>(field+0x30)!=1 ||
           ops.template read<uint32_t>(field+0x34)!=widths[i] ||
           ops.template read<uint64_t>(field+0x38)!=flags[i] ||
           ops.template read<uint32_t>(field+0x44)!=offsets[i]) return false;
        if(static_cast<uint32_t>(children[i])) {
            const auto child=ops.template read<uint64_t>(field+0x70);
            if(!validate_pod_schema(ops,children[i],ops.capture(child))) return false;
        }
        field=ops.template read<uint64_t>(field+0x18);
    }
    return !field && ops.identity(identity) && ops.context();
}

template<class Ops>
bool validate_pod_schema(Ops& ops,PodValueKind kind,const CallIdentity& identity) {
    if(kind==PodValueKind::FrameNumber || kind==PodValueKind::FrameTime || kind==PodValueKind::FrameRate ||
       kind==PodValueKind::QualifiedFrameTime || kind==PodValueKind::Timespan || kind==PodValueKind::BindingID) return validate_frame_time_schema(ops,kind,identity);
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
    case PodValueKind::Guid:
        struct_name="Guid"; package="/Script/CoreUObject";
        fields[0]="A"; fields[1]="B"; fields[2]="C"; fields[3]="D"; count=4; component=4;
        table=0x6e10a98; flags=6755469251052033ULL; field_type="IntProperty"; break;
    case PodValueKind::Vector:
        struct_name="Vector"; package="/Script/CoreUObject";
        fields[0]="X"; fields[1]="Y"; fields[2]="Z"; count=3; component=8;
        table=0x6e11788; flags=6755469251052037ULL; field_type="DoubleProperty"; break;
    case PodValueKind::Rotator:
        struct_name="Rotator"; package="/Script/CoreUObject";
        fields[0]="Pitch";fields[1]="Yaw";fields[2]="Roll";count=3;component=8;
        table=0x6e11788;flags=6755469251052037ULL;field_type="DoubleProperty";break;
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
