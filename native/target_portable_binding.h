#pragma once
#include "portable_binding_frame.h"
#include "sequence_origin_schema.h"
#include "target_pod_schema.h"

template<class Pool> struct TargetPortableBindingOps:TargetPodSchemaOps {
    uint64_t session;Pool& leases;const e33_portable_binding::Packet& p;
    bool registered(uint64_t o)const{return o&&identity(capture(o));}
    bool is_class(uint64_t c)const{return call_is_class(base,c);}
    bool validate(){
        if(!context())return false;
        const CallIdentity ids[]={p.target,p.function,p.root,p.destination,p.source};
        for(unsigned i=0;i<5;++i)if(!identity(ids[i])||!leases.owns_object(session,p.tokens[i],ids[i].address))return false;
        SequenceOriginSchema<TargetPortableBindingOps> s(*this);
        const auto fn=p.function.address,owner=read<uint64_t>(fn+32),cls=read<uint64_t>(p.target.address+16);
        if(!is_class(owner)||owner!=cls||!s.named(owner,"MovieSceneSequenceExtensions","/Script/SequencerScripting")||
           !name(p.target.address+24,"Default__MovieSceneSequenceExtensions")||!(read<uint32_t>(p.target.address+8)&0x10)||
           !name(fn+24,"GetPortableBindingID")||read<uint64_t>(fn)!=base+0x6dea198||
           read<uint32_t>(fn+0xb0)!=71443457||read<uint16_t>(fn+0xb6)!=64||read<uint16_t>(fn+0xb8)!=40||
           read<uint32_t>(fn+0x58)!=64||read<uint64_t>(fn+0xd8)!=base+0x4aeccc0)return false;
        auto a=s.field(fn,"RootSequence","ObjectProperty",0,8,0x6e11d38,6755468160533120ULL);
        auto b=s.field(fn,"DestinationSequence","ObjectProperty",8,8,0x6e11d38,6755468160533120ULL);
        auto c=s.field(fn,"InBinding","StructProperty",16,24,0x6e136a0,6755468294750594ULL);
        auto d=s.field(fn,"ReturnValue","StructProperty",40,24,0x6e136a0,6755468160533888ULL);
        if(!a||!b||!c||!d||read<uint64_t>(fn+0x50)!=a||read<uint64_t>(a+24)!=b||read<uint64_t>(b+24)!=c||
           read<uint64_t>(c+24)!=d||read<uint64_t>(d+24))return false;
        const auto sequence=read<uint64_t>(a+0x70);
        if(!is_class(sequence)||!s.named(sequence,"MovieSceneSequence","/Script/MovieScene")||read<uint64_t>(b+0x70)!=sequence)return false;
        const uint64_t sequences[]={p.root.address,p.destination.address,p.source.address};
        for(const auto object:sequences){
            const auto type=read<uint64_t>(object+16);
            if(!is_class(type)||!call_derives(base,type,sequence)||(read<uint32_t>(object+8)&0x40018030U))return false;
        }
        const auto proxy=read<uint64_t>(c+0x70),binding=read<uint64_t>(d+0x70);
        if(!s.named(proxy,"MovieSceneBindingProxy","/Script/MovieScene")||read<uint32_t>(proxy+0x58)!=24||
           read<uint64_t>(proxy+0x40)||!s.named(read<uint64_t>(proxy+16),"ScriptStruct","/Script/CoreUObject")||
           !validate_pod_schema(*this,PodValueKind::BindingID,capture(binding)))return false;
        auto guid=s.field(proxy,"BindingID","StructProperty",0,16,0x6e136a0,6755469234274836ULL);
        auto ref=s.field(proxy,"Sequence","ObjectProperty",16,8,0x6e11d38,79938962105303572ULL);
        if(!guid||!ref||read<uint64_t>(proxy+0x50)!=guid||read<uint64_t>(guid+24)!=ref||read<uint64_t>(ref+24)||
           read<uint64_t>(ref+0x70)!=sequence||!validate_pod_schema(*this,PodValueKind::Guid,capture(read<uint64_t>(guid+0x70))))return false;
        const auto pe=read<uint64_t>(read<uint64_t>(p.target.address)+0x268);
        return (pe==base+0x1393330||pe==base+0x332bb90)&&context();
    }
    void dispatch(void* arguments)const{
        const auto pe=read<uint64_t>(read<uint64_t>(p.target.address)+0x268);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(p.target.address),
            reinterpret_cast<void*>(p.function.address),arguments);
    }
};

template<class Pool> void portable_binding_command(uint64_t base,uint64_t session,Pool& leases,
        e33_portable_binding::Packet& p,e33_portable_binding::Frame& frame){
    TargetPortableBindingOps<Pool> ops{{base},session,leases,p};
    const auto result=frame.query(ops,p);
    if(result==e33_portable_binding::Result::Rejected){p.error=3760;return;}
    if(result==e33_portable_binding::Result::Unknown){p.error=3763;p.state=p.outcome=2;return;}
    p.state=p.outcome=1;std::memcpy(p.binding,frame.result(),24);frame.reset();
}
