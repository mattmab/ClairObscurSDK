#pragma once
#include "sequencer_object_array.h"
#include "sequence_origin_schema.h"

template<class Ops> bool sequencer_array_schema(Ops& ops,const e33_sequencer_array::Packet& p) {
    if(!ops.context() || !ops.identity(p.target) || !ops.identity(p.subject) || !ops.identity(p.function))return false;
    SequenceOriginSchema<Ops> fields(ops);
    const auto function=p.function.address,owner=ops.template read<uint64_t>(function+32);
    const auto target_class=ops.template read<uint64_t>(p.target.address+16);
    const auto subject_class=ops.template read<uint64_t>(p.subject.address+16);
    const char* output_class=p.mode==1 ? "MovieSceneScriptingChannel" : "MovieSceneScriptingKey";
    if(!ops.is_class(owner) || !ops.is_class(target_class) || !ops.is_class(subject_class) ||
       ops.template read<uint64_t>(function)!=ops.base+0x6dea198 ||
       ops.template read<uint16_t>(function+0xb6)!=(p.mode==1 ? 24 : 16) ||
       ops.template read<uint16_t>(function+0xb8)!=(p.mode==1 ? 8 : 0) ||
       ops.template read<uint32_t>(function+0x58)!=(p.mode==1 ? 24U : 16U) ||
       ops.template read<uint32_t>(function+0xb0)!=(p.mode==1 ? 67249153U : 1409418240U) ||
       ops.template read<uint64_t>(function+0xd8)!=ops.base+(p.mode==1 ? 0x4ae93a0 : 0x3208d90))return false;
    auto first=ops.template read<uint64_t>(function+0x50);
    if(p.mode==1) {
        if(!fields.named(owner,"MovieSceneSectionExtensions","/Script/SequencerScripting") ||
           !fields.named(target_class,"MovieSceneSectionExtensions","/Script/SequencerScripting") ||
           !ops.name(p.target.address+24,"Default__MovieSceneSectionExtensions") ||
           !(ops.template read<uint32_t>(p.target.address+8)&0x10) || !ops.name(function+24,"GetAllChannels"))return false;
        const auto input=fields.field(function,"Section","ObjectProperty",0,8,0x6e11d38,6755468161057408ULL);
        const auto declared=input ? ops.template read<uint64_t>(input+0x70) : 0;
        if(!input || first!=input || !ops.is_class(declared) ||
           !fields.named(declared,"MovieSceneSection","/Script/MovieScene") || !ops.derives(subject_class,declared))return false;
        first=ops.template read<uint64_t>(input+24);
    } else {
        const char* classes[]={"MovieSceneScriptingBoolChannel","MovieSceneScriptingByteChannel",
            "MovieSceneScriptingDoubleChannel","MovieSceneScriptingFloatChannel","MovieSceneScriptingIntegerChannel"};
        bool admitted=false;for(const auto name:classes)if(fields.named(owner,name,"/Script/SequencerScripting"))admitted=true;
        if(!admitted || target_class!=owner || std::memcmp(&p.target,&p.subject,sizeof(CallIdentity)) ||
           (ops.template read<uint32_t>(p.target.address+8)&0x10) || !ops.name(function+24,"GetKeys"))return false;
    }
    const auto result=fields.field(function,"ReturnValue","ArrayProperty",p.mode==1 ? 8 : 0,16,0x6e0de80,4503599627372416ULL);
    if(!result || first!=result || ops.template read<uint64_t>(result+24) || (ops.template read<uint8_t>(result+0x70)&1))return false;
    const auto inner=ops.template read<uint64_t>(result+0x78);
    const auto output=inner ? ops.template read<uint64_t>(inner+0x70) : 0;
    if(!inner || ops.template read<uint64_t>(inner)!=ops.base+0x6e11d38 ||
       ops.template read<uint64_t>(inner+16)!=result || !ops.name(ops.template read<uint64_t>(inner+8),"ObjectProperty") ||
       !ops.name(inner+32,"ReturnValue") || ops.template read<uint32_t>(inner+0x30)!=1 ||
       ops.template read<uint32_t>(inner+0x34)!=8 || ops.template read<uint32_t>(inner+0x44) ||
       !ops.is_class(output) || !fields.named(output,output_class,"/Script/SequencerScripting"))return false;
    const auto dispatch=ops.template read<uint64_t>(ops.template read<uint64_t>(p.target.address)+0x268);
    return (dispatch==ops.base+0x1393330 || dispatch==ops.base+0x332bb90) && ops.context();
}
