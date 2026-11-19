#pragma once
#include "dialogue_text_packet.h"
#include "dialogue_text_profiles.h"
#include "target_owned_text.h"

namespace e33_dialogue_text {
constexpr uint32_t rejected=3860,unavailable=3861,uncertain=3862;
struct Dispatcher {
    uint64_t alignment_padding=0;
    Frame frame;
    alignas(16) uint8_t arguments[104]{};
    uint64_t last_owner=0;
    bool quarantined()const{return frame.state==State::DispatchUnknown||frame.state==State::Quarantined;}
    bool empty()const{return frame.state==State::Empty||frame.state==State::Cleaned;}
    uint64_t object_field(uint64_t b,uint64_t object,const char* name)const{
        auto cls=local_read<uint64_t>(object+16);
        for(unsigned n=0;cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40)){
            if(!call_capture(b,cls).address)return 0;
            auto f=local_read<uint64_t>(cls+0x50);
            for(unsigned i=0;f&&i<2048;++i,f=local_read<uint64_t>(f+24)){
                if(!exact_name(b,f+32,name))continue;
                const auto offset=local_read<int32_t>(f+0x44);
                if(local_read<uint64_t>(f+16)!=(cls|1)||!exact_name(b,local_read<uint64_t>(f+8),"ObjectProperty")||
                   local_read<int32_t>(f+0x30)!=1||local_read<int32_t>(f+0x34)!=8||offset<0||offset>65536)return 0;
                const auto value=local_read<uint64_t>(object+offset);
                return value&&call_capture(b,value).address?value:0;
            }
        }
        return 0;
    }
    uint64_t world(uint64_t b,uint64_t object)const{
        for(unsigned n=0;object&&n<32;++n,object=local_read<uint64_t>(object+32)){
            if(!call_capture(b,object).address)return 0;
            if(e33_mesh::named(b,local_read<uint64_t>(object+16),"World","/Script/Engine"))return object;
        }
        return 0;
    }
    bool schema(uint64_t b,uint64_t function,uint32_t mode)const{
        const auto owner=local_read<uint64_t>(function+32);
        if(!e33_mesh::named(b,owner,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||
           !exact_name(b,function+24,mode==2?"EndDialogue":mode?"StartChoice":"StartDialogLines")||local_read<uint32_t>(function+0xb0)!=(mode==2?201457664U:214040576U)||
           local_read<uint16_t>(function+0xb6)!=(mode==2?10:mode?104:32)||local_read<uint16_t>(function+0xb8)!=65535||
           local_read<uint64_t>(function+0xd8)!=b+0x13937a0||local_read<int32_t>(function+0x68)<=0)return false;
        const auto expected=mode==2?parameters_2:mode?parameters_1:parameters_0;const unsigned count=mode==2?2:mode?4:3;
        unsigned found=0,steps=0;
        for(auto f=local_read<uint64_t>(function+0x50);f&&steps++<2048;f=local_read<uint64_t>(f+24)){
            const auto flags=local_read<uint64_t>(f+0x38);if(!(flags&128))continue;
            if(found>=count)return false;const auto& p=expected[found++];
            if(local_read<uint64_t>(f+16)!=(function|1)||!exact_name(b,f+32,p.name)||
               !exact_name(b,local_read<uint64_t>(f+8),p.type)||local_read<int32_t>(f+0x30)!=1||
               local_read<int32_t>(f+0x34)!=p.width||local_read<int32_t>(f+0x44)!=p.offset||flags!=p.flags)return false;
            if(!std::strcmp(p.type,"ArrayProperty")){
                const auto inner=local_read<uint64_t>(f+0x78);
                if((local_read<uint8_t>(f+0x70)&1)||!inner||local_read<uint64_t>(inner+16)!=f||
                   !exact_name(b,local_read<uint64_t>(inner+8),"TextProperty")||
                   local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=16)return false;
            }else{
                const auto related=local_read<uint64_t>(f+0x70);
                if(!call_capture(b,related).address||!exact_name(b,related+24,p.related))return false;
                if(!std::strcmp(p.type,"ObjectProperty")&&!call_is_class(b,related))return false;
                if(!std::strcmp(p.type,"StructProperty")&&local_read<int32_t>(related+0x58)!=p.width)return false;
            }
        }
        return found==count&&steps<2048;
    }
    template<class Pool> void run(uint64_t b,uint64_t session,Pool& leases,Packet& p,
        bool(*before_end)(uint64_t,uint64_t,CallIdentity,CallIdentity)=nullptr,
        bool(*admit_original)(uint64_t,uint64_t,const CallIdentity&,const CallIdentity&)=nullptr){
        if(!valid_packet(p)||p.owner==last_owner||!TargetPodSchemaOps{b}.context()||!empty()){
            p.error=quarantined()?uncertain:rejected;return;
        }
        const auto system=call_identity(b,p.system),dialogue=call_identity(b,p.dialogue),function=call_identity(b,p.function);
        if(!system||!dialogue||!function||!leases.owns_object(session,p.dialogue_lease,dialogue)||
           !e33_mesh::named(b,local_read<uint64_t>(system+16),"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||
           (!e33_mesh::named(b,local_read<uint64_t>(dialogue+16),"BP_Dialogue_C","/Game/Gameplay/DialogueSystem/BP_Dialogue")&&
            !(admit_original&&admit_original(b,session,p.system,p.dialogue)))||
           (local_read<uint32_t>(dialogue+8)&0x40000030U)||object_field(b,system,"ActiveDialogue")!=dialogue||!schema(b,function,p.mode)){
            p.error=rejected;return;
        }
        const auto controller=local_read<uint64_t>(system+32),player=object_field(b,controller,"Player");
        if(!player||!e33_mesh::named(b,local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine")||
           object_field(b,player,"PlayerController")!=controller||!world(b,controller)||world(b,controller)!=world(b,dialogue)){
            p.error=unavailable;return;
        }
        const auto speaker=p.mode?0:call_identity(b,p.speaker);
        if(!p.mode&&(!speaker||!e33_mesh::named(b,local_read<uint64_t>(speaker+16),"BP_DataAsset_DialogueCharacter_C","/Game/Gameplay/DialogueSystem/BP_DataAsset_DialogueCharacter"))){
            p.error=rejected;return;
        }
        uint64_t complete_field=0;
        const auto complete=picto_field(b,dialogue,"IsComplete","BoolProperty",680,1,&complete_field);
        if(!complete||local_read<uint32_t>(complete_field+0x70)!=0xff010001U){p.error=rejected;return;}
        const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(system)+0x268);
        if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=rejected;return;}
        // Reuse only a fully cleaned frame. No live FText is overwritten.
        frame.count=0;frame.state=State::Empty;last_owner=p.owner;
        if(p.mode==2){
            if(before_end&&!before_end(b,session,p.system,p.dialogue)){p.error=uncertain;return;}
            std::memset(arguments,0,sizeof(arguments));std::memcpy(arguments,&dialogue,8);
            arguments[8]=1;arguments[9]=1; // Native camera blend and music restore.
            frame.state=State::DispatchUnknown;
            reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(system),reinterpret_cast<void*>(function),arguments);
            frame.state=State::Cleaned;std::memset(arguments,0,sizeof(arguments));p.state=1;return;
        }

        Input inputs[capacity]{};for(unsigned i=0;i<p.count;++i)inputs[i]={p.units+p.starts[i],p.lengths[i]};
        TargetOwnedTextOps ops{b};
        if(!frame.prepare(ops,inputs,p.count)){p.error=unavailable;frame.cleanup(ops);return;}
        std::memset(arguments,0,sizeof(arguments));std::memcpy(arguments,&dialogue,8);
        std::memcpy(arguments+8,&frame.array,16);if(!p.mode)std::memcpy(arguments+24,&speaker,8);
        if(!frame.begin(ops)){p.error=unavailable;frame.cleanup(ops);return;}
        // The native line/choice callbacks set this flag. It must be cleared
        // for this presentation; LastChoice intentionally survives in vanilla.
        *reinterpret_cast<uint8_t*>(complete)=0;

        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(system),reinterpret_cast<void*>(function),arguments);
        // Inspect the actual borrowed header in the argument buffer too.
        if(std::memcmp(arguments+8,&frame.array,16)){frame.state=State::Quarantined;p.error=uncertain;return;}
        if(!frame.returned()||!frame.cleanup(ops)){p.error=uncertain;return;}
        std::memset(arguments,0,sizeof(arguments));p.state=1;
    }
};
}
