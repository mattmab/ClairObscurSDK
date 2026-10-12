#pragma once
#include "cinematic_callback_profile.h"

struct TitleAnimationProfile {
    CallIdentity user{},animation{},player{},stop{},unbind{};
    bool prepare(uint64_t base,const CallIdentity& user_class) {
        *this={};
        user=user_class;
        if(!call_identity(base,user) || !call_is_class(base,user.address) ||
           !cinematic_named_object(base,user.address,"UserWidget","/Script/UMG")) return false;
        auto array=[&](const char* name,uint32_t offset,uint64_t flags,const char* inner_type,
                       uint32_t width,const char* constraint) -> uint64_t {
            const auto field=music_field(base,user.address,name,offset,16,0x6e0de80,flags);
            if(!field || (local_read<uint8_t>(field+0x70)&1)) return 0;
            const auto inner=local_read<uint64_t>(field+0x78);
            if(!inner || !exact_name(base,local_read<uint64_t>(inner+8),inner_type) ||
               local_read<uint64_t>(inner+0x10)!=field || local_read<uint32_t>(inner+0x30)!=1 ||
               local_read<uint32_t>(inner+0x34)!=width || local_read<uint32_t>(inner+0x44)) return 0;
            const auto type=local_read<uint64_t>(inner+0x70);
            return cinematic_named_object(base,type,constraint,"/Script/UMG") ? type : 0;
        };
        const auto active=array("ActiveSequencePlayers",560,0x114000000002200ULL,"ObjectProperty",8,"UMGSequencePlayer");
        if(!active || array("StoppedSequencePlayers",584,0x114000000002200ULL,"ObjectProperty",8,"UMGSequencePlayer")!=active ||
           !array("QueuedWidgetAnimationTransitions",544,0x10000000002200ULL,"StructProperty",56,"QueuedWidgetAnimationTransition") ||
           !array("AnimationCallbacks",696,0x20088000202200ULL,"StructProperty",40,"AnimationEventBinding")) return false;
        player=call_capture(base,active);
        if(!call_is_class(base,player.address)) return false;
        // One bounded registry walk at preparation, never a frame-loop catalog.
        // Matching uses owner, UFunction identity, exact metadata and native RVA.
        const auto count=local_read<int32_t>(base+0x9361b84);
        const auto chunk_count=local_read<int32_t>(base+0x9361b8c);
        const auto chunks=local_read<uint64_t>(base+0x9361b70);
        if(count<0 || count>1048576 || !chunks || chunk_count<1 || chunk_count>16 ||
           (count && ((count-1)>>16)>=chunk_count)) return false;
        for(int32_t index=0;index<count;++index) {
            const auto chunk=local_read<uint64_t>(chunks+uint64_t(index>>16)*8);
            if(!chunk) return false;
            const auto object=local_read<uint64_t>(chunk+uint64_t(index&65535)*24);
            if(!object || local_read<uint64_t>(object+0x20)!=user.address ||
               local_read<uint64_t>(object)!=base+0x6dea198) continue;
            const bool is_stop=exact_name(base,object+0x18,"StopAnimation");
            const bool is_unbind=exact_name(base,object+0x18,"UnbindAllFromAnimationFinished");
            if(!is_stop && !is_unbind) continue;
            auto& id=is_stop ? stop : unbind;
            if(id.address || local_read<uint32_t>(object+0xb0)!=0x4020403 ||
               local_read<uint16_t>(object+0xb6)!=8 || local_read<uint16_t>(object+0xb8)!=65535 ||
               local_read<uint32_t>(object+0x58)!=8 ||
               local_read<uint64_t>(object+0xd8)!=base+(is_stop ? 0x3141fd0 : 0x3142720)) return false;
            const auto field=music_field(base,object,is_stop ? "InAnimation" : "Animation",0,8,0x6e11d38,
                is_stop ? 0x18001000000282ULL : 0x18001000000280ULL);
            if(!field || local_read<uint64_t>(field+0x18)) return false;
            const auto cls=local_read<uint64_t>(field+0x70);
            if(!call_is_class(base,cls) || !cinematic_named_object(base,cls,"WidgetAnimation","/Script/UMG") ||
               (animation.address && animation.address!=cls)) return false;
            animation=call_capture(base,cls);id=call_capture(base,object);
        }
        if(!stop.address || !unbind.address || local_read<uint32_t>(player.address+0x58)!=704) return false;
        const auto player_animation=music_field(base,player.address,"Animation",528,8,0x6e11d38,0x14c001000000200ULL);
        const auto root=music_field(base,player.address,"RootTemplateInstance",544,32,0x6e136a0,0x40000000000000ULL);
        if(!player_animation || local_read<uint64_t>(player_animation+0x70)!=animation.address || !root) return false;
        const auto root_type=local_read<uint64_t>(root+0x70);
        return cinematic_named_object(base,root_type,"MovieSceneRootEvaluationTemplateInstance","/Script/MovieScene") &&
            local_read<uint32_t>(root_type+0x58)==32;
    }
    bool title(uint64_t base,const CallIdentity& widget) const {
        if(!call_identity(base,widget)) return false;
        const auto cls=local_read<uint64_t>(widget.address+0x10);
        if(!call_is_class(base,cls) || !call_derives(base,cls,user.address) ||
           !cinematic_named_object(base,cls,"WBP_SequencerTitleWidget_C",
             "/Game/Gameplay/UI/Sequencer/Widget/TitleWidget/WBP_SequencerTitleWidget") ||
           local_read<uint64_t>(local_read<uint64_t>(widget.address)+0x348)!=base+0x3126290) return false;
        const auto field=music_field(base,cls,"CurrentPlayingAnimation",800,8,0x6e11d38,0x8001000010205ULL);
        return field && local_read<uint64_t>(field+0x70)==animation.address;
    }
    CallPacket call(const CallIdentity& widget,const CallIdentity& value,bool is_stop) const {
        CallPacket p{};p.version=1;p.parameter_size=p.allocation_extent=8;p.return_offset=65535;
        p.function_flags=0x4020403;p.entry_rva=is_stop ? 0x3141fd0 : 0x3142720;
        p.field_count=p.object_count=1;p.target=widget;p.function=is_stop ? stop : unbind;
        auto& field=p.fields[0];field.kind=CallObject;field.width=8;field.dimension=1;
        field.flags=is_stop ? 0x18001000000282ULL : 0x18001000000280ULL;
        const auto name=is_stop ? "InAnimation" : "Animation";
        std::memcpy(field.name,name,std::strlen(name)+1);field.constraint=animation;
        p.objects[0].identity=value;return p;
    }
};
