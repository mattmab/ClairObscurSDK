#pragma once
#include "authored_curve_patch.h"
#include "sequence_origin_schema.h"
#include "target_pod_schema.h"

template<class Pool> struct TargetAuthoredCurvePatchOps:TargetPodSchemaOps {
    using TargetPodSchemaOps::read;
    uint64_t session;Pool& leases;bool construction;
    bool registered(uint64_t value)const{return value&&identity(capture(value));}
    bool is_class(uint64_t value)const{return call_is_class(base,value);}
    bool under(uint64_t object,uint64_t ancestor)const{
        uint64_t seen[128]{};
        for(unsigned i=0;object&&i<128;++i,object=read<uint64_t>(object+32)){
            if(!registered(object))return false;
            if(object==ancestor)return true;
            for(unsigned j=0;j<i;++j)if(seen[j]==object)return false;
            seen[i]=object;
        }
        return false;
    }
    bool named(uint64_t value,const char* type,const char* package)const{
        SequenceOriginSchema<const TargetAuthoredCurvePatchOps> schema(*this);return schema.named(value,type,package);
    }
    bool struct_type(uint64_t value)const{return registered(value)&&named(read<uint64_t>(value+16),"ScriptStruct","/Script/CoreUObject");}
    uint64_t field(uint64_t owner,const char* wanted)const{
        uint64_t result=0;
        for(unsigned ancestor_depth=0;owner&&ancestor_depth<128;++ancestor_depth,owner=read<uint64_t>(owner+64)){
            if(!registered(owner))return 0;
            auto member=read<uint64_t>(owner+80);
            for(unsigned n=0;member&&n<4096;++n,member=read<uint64_t>(member+24)){
                if(!name(member+32,wanted))continue;
                if(result||read<uint64_t>(member+16)!=(owner|1))return 0;
                result=member;
            }
            if(member)return 0;
        }
        return owner?0:result;
    }
    uint64_t channel(uint64_t object,const e33_curve_patch::Packet& p,uint64_t& type)const{
        auto owner=read<uint64_t>(object+16),at=object;bool root=true;
        for(unsigned i=0;i<p.depth;++i){
            const auto member=field(owner,p.path[i].field);
            if(!member||read<uint64_t>(member)!=base+0x6e136a0||!name(read<uint64_t>(member+8),"StructProperty"))return 0;
            const auto declared=read<uint64_t>(member+16)&~1ULL;
            const auto offset=read<uint32_t>(member+68),size=read<uint32_t>(member+52),dim=read<uint32_t>(member+48);
            const auto flags=read<uint64_t>(member+56),table=read<uint64_t>(member);
            type=read<uint64_t>(member+112);
            if(!struct_type(type)||!registered(declared)||!dim||dim>64||!size||size!=read<uint32_t>(type+88)||
               (flags&(0x80ULL|0x20000ULL|0x20ULL))||offset<(root?40U:0U)||
               uint64_t(offset)+uint64_t(size)*dim>read<uint32_t>(declared+88)||
               read<uint64_t>(table+0x78)!=base+0x10044f0||read<uint64_t>(table+0x80)!=base+0x10044f0)return 0;
            const auto element=p.path[i].element;
            if((element==UINT32_MAX&&dim!=1)||(element!=UINT32_MAX&&element>=dim))return 0;
            at+=offset+uint64_t(element==UINT32_MAX?0:element)*size;owner=type;root=false;
        }
        return at;
    }
    uint64_t array(uint64_t owner,const char* wanted,uint32_t offset,uint64_t flags,
                   const char* inner_name,uint32_t inner_size,const char* inner_struct=nullptr)const{
        SequenceOriginSchema<const TargetAuthoredCurvePatchOps> schema(*this);
        const auto property=schema.field(owner,wanted,"ArrayProperty",offset,16,0x6e0de80,flags);
        if(!property||(read<uint8_t>(property+112)&1))return 0;
        const auto inner=read<uint64_t>(property+120);
        const uint64_t table=inner_struct?0x6e136a0:!std::strcmp(inner_name,"IntProperty")?0x6e10a98:
            !std::strcmp(inner_name,"BoolProperty")?0x6e119b0:0x6e10420;
        if(!inner||read<uint64_t>(inner)!=base+table||read<uint64_t>(inner+16)!=property||
           !name(read<uint64_t>(inner+8),inner_name)||read<uint32_t>(inner+48)!=1||
           read<uint32_t>(inner+52)!=inner_size||read<uint32_t>(inner+68))return 0;
        if(inner_struct){
            const auto type=read<uint64_t>(inner+112);
            if(!struct_type(type)||!named(type,inner_struct,!std::strcmp(inner_struct,"FrameNumber")?"/Script/CoreUObject":"/Script/MovieScene")||
               read<uint32_t>(type+88)!=inner_size)return 0;
            const auto value=field(type,"Value");
            const bool frame=!std::strcmp(inner_struct,"FrameNumber");
            const bool dbl=!std::strcmp(inner_struct,"MovieSceneDoubleValue");
            if(!value||read<uint64_t>(value)!=base+(frame?0x6e10a98:dbl?0x6e11788:0x6e11560)||
               read<uint32_t>(value+68)||read<uint32_t>(value+48)!=1||read<uint32_t>(value+52)!=(dbl?8U:4U))return 0;
        }else if(!std::strcmp(inner_name,"BoolProperty")&&read<uint32_t>(inner+112)!=0xff010001U)return 0;
        return property;
    }
    bool profile(uint64_t type,uint32_t kind,uint32_t& times,uint32_t& values)const{
        using namespace e33_curve_patch;
        const char* names[]={"","MovieSceneBoolChannel","MovieSceneByteChannel","MovieSceneIntegerChannel","MovieSceneFloatChannel","MovieSceneDoubleChannel"};
        if(!struct_type(type)||!named(type,names[kind],"/Script/MovieScene")||!channel_base(*this,type))return false;
        const unsigned size=kind==Float?272U:kind==Double?280U:264U;
        if(read<uint32_t>(type+88)!=size)return false;
        times=kind==Byte?80U:88U;values=kind==Boolean||kind==Integer?112U:104U;
        const auto flags=kind==Boolean?9015995347763712ULL:18014398509482496ULL;
        if(!array(type,"Times",times,flags,"StructProperty",4,"FrameNumber"))return false;
        const char* inner=kind==Boolean?"BoolProperty":kind==Byte?"ByteProperty":kind==Integer?"IntProperty":"StructProperty";
        return array(type,"Values",values,flags,inner,stride(kind),kind==Float?"MovieSceneFloatValue":kind==Double?"MovieSceneDoubleValue":nullptr)!=0;
    }
    bool resolve(const e33_curve_patch::Packet& p,e33_curve_patch::Storage& out)const{
        using namespace e33_curve_patch;
        if(!construction||!context())return false;
        const CallIdentity objects[]={p.source,p.target,p.sequence,p.outer};
        for(unsigned i=0;i<4;++i)if(!identity(objects[i])||!leases.owns_object(session,p.tokens[i],objects[i].address)||
            (read<uint32_t>(objects[i].address+8)&0x40018030U))return false;
        const auto cls=read<uint64_t>(p.target.address+16);
        if(cls!=read<uint64_t>(p.source.address+16)||!is_class(cls)||
           !named(read<uint64_t>(p.sequence.address+16),"LevelSequence","/Script/LevelSequence")||
           !named(read<uint64_t>(p.outer.address+16),"WidgetTree","/Script/UMG")||
           !under(p.target.address,p.sequence.address)||!under(p.sequence.address,p.outer.address)||under(p.source.address,p.outer.address))return false;
        uint64_t section_class=cls;
        for(unsigned i=0;section_class&&i<128;++i,section_class=read<uint64_t>(section_class+64))
            if(named(section_class,"MovieSceneSection","/Script/MovieScene"))break;
        if(!section_class||!named(section_class,"MovieSceneSection","/Script/MovieScene"))return false;
        const auto locked=field(cls,"bIsLocked");
        if(!locked||read<uint64_t>(locked)!=base+0x6e119b0||read<uint32_t>(locked+68)!=184||
           read<uint32_t>(locked+52)!=1||read<uint32_t>(locked+48)!=1||
           read<uint64_t>(locked+56)!=20266267042643969ULL||read<uint32_t>(locked+112)!=0x02020001U||
           (read<uint8_t>(p.target.address+184)&2U))return false;
        const auto signature=field(cls,"Signature"),compiled=field(read<uint64_t>(p.sequence.address+16),"CompiledData");
        if(!signature||read<uint64_t>(signature)!=base+0x6e136a0||read<uint32_t>(signature+68)!=44||
           read<uint32_t>(signature+52)!=16||read<uint32_t>(signature+48)!=1||
           read<uint64_t>(signature+56)!=20266268116386304ULL||
           !validate_pod_schema(*this,PodValueKind::Guid,capture(read<uint64_t>(signature+112)))||
           std::memcmp(reinterpret_cast<void*>(p.source.address+44),p.signature,16)||
           std::memcmp(reinterpret_cast<void*>(p.target.address+44),p.signature,16)||
           !compiled||read<uint64_t>(compiled)!=base+0x6e11d38||read<uint32_t>(compiled+68)!=88||
           read<uint32_t>(compiled+52)!=8||read<uint32_t>(compiled+48)!=1||
           read<uint64_t>(compiled+56)!=94012710941360648ULL||read<uint64_t>(p.sequence.address+88))return false;
        uint64_t source_type=0,target_type=0;
        const auto source=channel(p.source.address,p,source_type),channel_target=channel(p.target.address,p,target_type);
        uint32_t times=0,values=0;
        if(!source||!channel_target||source_type!=target_type||!profile(source_type,p.kind,times,values))return false;
        struct Array {uint64_t data;int32_t count,capacity;};
        const auto st=read<Array>(source+times),sv=read<Array>(source+values),tt=read<Array>(channel_target+times),tv=read<Array>(channel_target+values);
        const Array arrays[]={st,sv,tt,tv};
        for(const auto& array:arrays)if(array.count!=int32_t(p.key_count)||array.capacity<array.count||array.capacity>131072||
            !array.data||array.data>0x7fffffffffffULL)return false;
        out={st.data,sv.data,tt.data,tv.data,p.key_count,p.kind};return context();
    }
    bool read(uint64_t at,void* out,size_t size)const{std::memcpy(out,reinterpret_cast<void*>(at),size);return true;}
    bool equal(uint64_t at,const void* expected,size_t size)const{return !std::memcmp(reinterpret_cast<void*>(at),expected,size);}
    bool write(uint64_t at,const void* value,size_t size)const{std::memcpy(reinterpret_cast<void*>(at),value,size);return true;}
};

template<class Pool> void authored_curve_patch_command(uint64_t base,uint64_t session,Pool& leases,
        e33_curve_patch::Packet& p,e33_curve_patch::Frame& frame,bool construction){
    TargetAuthoredCurvePatchOps<Pool> ops{{base},session,leases,construction};
    const auto result=frame.patch(ops,p);
    if(result==e33_curve_patch::Result::Rejected){p.error=3780;return;}
    if(result==e33_curve_patch::Result::Unknown){p.error=3783;p.state=p.outcome=2;return;}
    p.state=p.outcome=1;frame.reset();
}
