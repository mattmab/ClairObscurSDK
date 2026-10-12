#pragma once
#include "cinematic_getter_profile.h"
#include "cinematic_track_shape.h"

// Reviewed Expedition 33 widget graph only. All dynamic operands are resolved
// from current reflected owners and checked; there are no wildcard byte ranges.
// The caller retains these objects and supplies the game-thread/SEH boundary.
inline bool cinematic_named_object(uint64_t base,uint64_t object,const char* name,const char* package) {
    return call_capture(base,object).address && exact_name(base,object+0x18,name) &&
        exact_name(base,local_read<uint64_t>(object+0x20)+0x18,package);
}
inline bool cinematic_track_profile(uint64_t base,const CallIdentity& graph_id,
                                    const CallIdentity& track_id,const CallIdentity& library_id,
                                    const CallIdentity& component_id,uint32_t* diagnostic=nullptr) {
    auto stage=[&](uint32_t value) { if(diagnostic) *diagnostic=value; };
    stage(1);
    using namespace e33_cinematic;
    const auto graph=call_identity(base,graph_id),track=call_identity(base,track_id);
    const auto library=call_identity(base,library_id),component=call_identity(base,component_id);
    if(!graph || !track || !library || !component || !call_is_class(base,track) ||
       !cinematic_named_object(base,track,"BP_WidgetSequencerTrackInstance_C",
            "/Game/Gameplay/UI/Sequencer/BP_WidgetSequencerTrackInstance") ||
       local_read<uint64_t>(graph+0x20)!=track ||
       !exact_name(base,graph+0x18,"ExecuteUbergraph_BP_WidgetSequencerTrackInstance") ||
       local_read<uint32_t>(graph+0xb0)!=0x808001 || local_read<uint16_t>(graph+0xb6)!=4 ||
       local_read<uint16_t>(graph+0xb8)!=65535 || local_read<uint32_t>(graph+0x58)!=296 ||
       local_read<uint64_t>(graph+0xd8)!=base+0x13937a0) return false;
    stage(2);
    const auto script=local_read<uint64_t>(graph+0x60);
    const auto capacity=local_read<int32_t>(graph+0x6c);
    if(!script || local_read<int32_t>(graph+0x68)!=690 || capacity<690 || capacity>65536) return false;
    stage(3);
    const auto interface_class=local_read<uint64_t>(script+173),section=local_read<uint64_t>(script+252);
    if(!call_is_class(base,interface_class) || !call_is_class(base,section) ||
       !cinematic_named_object(base,interface_class,"BPI_WidgetSequencerInterface_C",
            "/Game/Gameplay/UI/Sequencer/BPI_WidgetSequencerInterface") ||
       !cinematic_named_object(base,section,"BP_WidgetSequencerSection_C",
            "/Game/Gameplay/UI/Sequencer/BP_WidgetSequencerSection")) return false;
    const uint64_t owners[]={graph,track,section};
    uint64_t values[25]{};
    static_assert(sizeof(widget_fields)/sizeof(widget_fields[0])==12);
    for(size_t i=0;i<12;++i) {
        stage(uint32_t(10+i));
        const auto& field=widget_fields[i];
        if(field.owner>=3) return false;
        values[i]=music_field(base,owners[field.owner],field.name,field.offset,field.width,field.vtable,field.flags,field.name_number);
        if(!values[i]) return false;
    }
    stage(30);
    const auto component_class=local_read<uint64_t>(component+0x10);
    const auto library_class=local_read<uint64_t>(library+0x10);
    if(!call_is_class(base,component_class) ||
       !cinematic_named_object(base,component_class,"BP_CinematicSystem_C",
            "/Game/Gameplay/CinematicSystem/BP_CinematicSystem") ||
       !cinematic_named_object(base,library_class,"FL_jRPG_CustomFunctionLibrary_C",
            "/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary") ||
       !(local_read<uint32_t>(library+8)&0x10) ||
       local_read<uint64_t>(values[1]+0x70)!=component_class ||
       local_read<uint64_t>(values[9]+0x70)!=component_class ||
       local_read<uint64_t>(values[3]+0x70)!=interface_class ||
       local_read<uint64_t>(values[5]+0x70)!=section) return false;
    stage(31);
    const auto widget=local_read<uint64_t>(values[2]+0x70);
    const auto input=local_read<uint64_t>(values[6]+0x70),parameters=local_read<uint64_t>(values[8]+0x70);
    if(!call_is_class(base,widget) || !cinematic_named_object(base,widget,"UserWidget","/Script/UMG") ||
       local_read<uint64_t>(values[10]+0x70)!=widget || local_read<uint64_t>(values[11]+0x78)!=widget ||
       !cinematic_named_object(base,input,"SequencerTrackInstanceInput","/Script/CustomizableSequencerTracks") ||
       local_read<uint32_t>(input+0x58)!=112 ||
       !cinematic_named_object(base,parameters,"DataTableRowHandle","/Script/Engine") ||
       local_read<uint32_t>(parameters+0x58)!=16) return false;
    stage(32);
    const auto input_section=music_field(base,input,"Section",0,8,0x6e11d38,0x11c00100008021cULL);
    if(!input_section) return false;
    stage(33);
    const auto section_base=local_read<uint64_t>(input_section+0x70);
    if(!cinematic_named_object(base,section_base,"SequencerSectionBP","/Script/CustomizableSequencerTracks") ||
       !call_derives(base,section,section_base)) return false;
    stage(34);
    const auto add=local_read<uint64_t>(script+495),defaults=local_read<uint64_t>(script+600);
    const auto create=local_read<uint64_t>(script+621);
    if(!call_capture(base,add).address || !call_capture(base,create).address ||
       !cinematic_named_object(base,defaults,"Default__WidgetBlueprintLibrary","/Script/UMG") ||
       !(local_read<uint32_t>(defaults+8)&0x10) || local_read<uint64_t>(add+0x20)!=widget ||
       !exact_name(base,add+0x18,"AddToViewport") || local_read<uint64_t>(add+0xd8)!=base+0x31355b0 ||
       local_read<uint32_t>(add+0xb0)!=0x402040b || local_read<uint16_t>(add+0xb6)!=4 ||
       local_read<uint16_t>(add+0xb8)!=65535 || !exact_name(base,create+0x18,"Create") ||
       local_read<uint64_t>(create+0x20)!=local_read<uint64_t>(defaults+0x10) ||
       !cinematic_named_object(base,local_read<uint64_t>(create+0x20),"WidgetBlueprintLibrary","/Script/UMG") ||
       local_read<uint64_t>(create+0xd8)!=base+0x31361b0 || local_read<uint32_t>(create+0xb0)!=0x402240b ||
       local_read<uint16_t>(create+0xb6)!=32 || local_read<uint16_t>(create+0xb8)!=24) return false;
    stage(35);
    values[12]=library;values[13]=interface_class;values[14]=section;values[15]=input_section;
    values[16]=add;values[17]=defaults;values[18]=create;
    for(size_t i=0;i<6;++i) {
        stage(uint32_t(40+i));
        const auto at=script+widget_name_offsets[i];
        // This build's FScriptName is comparison index, zero display word,
        // zero number. exact_name validates the first two words; shape checks
        // the third word too, without freezing session-specific name indices.
        if(!exact_name(base,at,widget_names[i]) || local_read<uint32_t>(at+8)) return false;
        values[19+i]=local_read<uint64_t>(at);
    }
    stage(50);
    uint64_t bound[52]{};
    static_assert(sizeof(widget_binding_offsets)/sizeof(widget_binding_offsets[0])==52);
    for(size_t i=0;i<52;++i) {
        if(widget_binding_values[i]>=25) return false;
        bound[i]=values[widget_binding_values[i]];
    }
    stage(51);
    auto read=[](uint64_t address,void* out,size_t size) {
        std::memcpy(out,reinterpret_cast<const void*>(address),size);return true;};
    return exact_script_shape(read,script,widget_graph_bytes,widget_binding_offsets,bound);
}
