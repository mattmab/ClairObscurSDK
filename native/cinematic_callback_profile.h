#pragma once
#include "cinematic_track_profile.h"
#include "cinematic_callback_shapes.h"

// Only authorizes registration against a private component whose controls
// widget remains null. The unreachable controls-update body is NOT admitted.
// Caller must recheck private_controls_null() immediately before substitution.
inline bool private_controls_null(uint64_t base,const CallIdentity& component) {
    return call_identity(base,component) && !local_read<uint64_t>(component.address+552);
}
inline bool cinematic_callback_profile(uint64_t base,const CallIdentity& component,
                                        const CallIdentity& register_id,const CallIdentity& unregister_id,
                                        const CallIdentity& controls_id) {
    using namespace e33_cinematic;
    if(!private_controls_null(base,component)) return false;
    const auto cls=local_read<uint64_t>(component.address+0x10);
    if(!cinematic_named_object(base,cls,"BP_CinematicSystem_C","/Game/Gameplay/CinematicSystem/BP_CinematicSystem")) return false;
    const auto reg=call_identity(base,register_id),unreg=call_identity(base,unregister_id),controls=call_identity(base,controls_id);
    auto blueprint=[&](uint64_t fn,const char* name,uint32_t flags,uint16_t params,uint32_t extent,int32_t length) {
        return fn && local_read<uint64_t>(fn+0x20)==cls && exact_name(base,fn+0x18,name) &&
            local_read<uint32_t>(fn+0xb0)==flags && local_read<uint16_t>(fn+0xb6)==params &&
            local_read<uint16_t>(fn+0xb8)==65535 && local_read<uint32_t>(fn+0x58)==extent &&
            local_read<uint64_t>(fn+0xd8)==base+0x13937a0 && local_read<uint64_t>(fn+0x60) &&
            local_read<int32_t>(fn+0x68)==length && local_read<int32_t>(fn+0x6c)>=length &&
            local_read<int32_t>(fn+0x6c)<=65536;};
    if(!blueprint(reg,"RegisterSpawnedWidget",0xc020000,8,12,85) ||
       !blueprint(unreg,"UnregisterSpawnedWidget",0xc420000,8,9,77) ||
       !blueprint(controls,"UpdateCinematicControlsWidget",0xc040000,0,6,285)) return false;
    const auto array=music_field(base,cls,"SpawnedWidgets",800,16,0x6e0de80,0x8000010005ULL);
    const auto current=music_field(base,cls,"CurrentCinematicWidget",552,8,0x6e11d38,0x8001000090205ULL);
    if(!array || !current || (local_read<uint8_t>(array+0x70)&1)) return false;
    const auto inner=local_read<uint64_t>(array+0x78);
    if(!inner || local_read<uint64_t>(inner)!=base+0x6e11d38 || local_read<uint64_t>(inner+0x10)!=array ||
       local_read<uint32_t>(inner+0x30)!=1 || local_read<uint32_t>(inner+0x34)!=8 || local_read<uint32_t>(inner+0x44)) return false;
    const auto widget=local_read<uint64_t>(inner+0x70);
    if(!cinematic_named_object(base,widget,"UserWidget","/Script/UMG")) return false;
    const auto result_add=music_field(base,reg,"CallFunc_Array_AddUnique_ReturnValue",8,4,0x6e10a98,0x8001040000200ULL);
    const auto arg_add=music_field(base,reg,"Widget",0,8,0x6e11d38,0x8001000080294ULL);
    const auto result_remove=music_field(base,unreg,"CallFunc_Array_RemoveItem_ReturnValue",8,1,0x6e119b0,0x8001040000200ULL);
    const auto arg_remove=music_field(base,unreg,"Widget",0,8,0x6e11d38,0x8001008080396ULL);
    const auto valid_result=music_field(base,controls,"CallFunc_IsValid_ReturnValue",2,1,0x6e119b0,0x8001040000200ULL,2);
    if(!result_add || !arg_add || !result_remove || !arg_remove || !valid_result ||
       local_read<uint64_t>(arg_add+0x70)!=widget || local_read<uint64_t>(arg_remove+0x70)!=widget) return false;
    const auto a=local_read<uint64_t>(reg+0x60),r=local_read<uint64_t>(unreg+0x60),c=local_read<uint64_t>(controls+0x60);
    const auto defaults=local_read<uint64_t>(a+20),add=local_read<uint64_t>(a+41),remove=local_read<uint64_t>(r+33);
    const auto valid=local_read<uint64_t>(c+11);
    auto native=[&](uint64_t fn,const char* name,const char* owner,uint64_t entry,uint32_t flags,uint16_t size,uint16_t ret) {
        return call_capture(base,fn).address && exact_name(base,fn+0x18,name) &&
            cinematic_named_object(base,local_read<uint64_t>(fn+0x20),owner,"/Script/Engine") &&
            local_read<uint64_t>(fn+0xd8)==base+entry && local_read<uint32_t>(fn+0xb0)==flags &&
            local_read<uint16_t>(fn+0xb6)==size && local_read<uint16_t>(fn+0xb8)==ret;};
    if(!cinematic_named_object(base,defaults,"Default__KismetArrayLibrary","/Script/Engine") ||
       !(local_read<uint32_t>(defaults+8)&0x10) ||
       !native(add,"Array_AddUnique","KismetArrayLibrary",0x3828d70,0x4422403,24,20) ||
       !native(remove,"Array_RemoveItem","KismetArrayLibrary",0x382a310,0x4422403,21,20) ||
       !native(valid,"IsValid","KismetSystemLibrary",0x3857e20,0x14022403,9,8) ||
       local_read<uint64_t>(defaults+0x10)!=local_read<uint64_t>(add+0x20) ||
       local_read<uint64_t>(add+0x20)!=local_read<uint64_t>(remove+0x20) ||
       !exact_name(base,a+69,"UpdateCinematicControlsWidget") || local_read<uint32_t>(a+77) ||
       !exact_name(base,r+61,"UpdateCinematicControlsWidget") || local_read<uint32_t>(r+69)) return false;
    const uint64_t av[]={result_add,result_add,defaults,result_add,add,array,arg_add,local_read<uint64_t>(a+69)};
    const uint64_t rv[]={result_remove,defaults,result_remove,remove,array,arg_remove,local_read<uint64_t>(r+61)};
    const uint64_t cv[]={valid_result,valid,current,valid_result};
    auto read=[](uint64_t address,void* out,size_t size) {
        std::memcpy(out,reinterpret_cast<const void*>(address),size);return true;};
    // Prefix has JumpIfNot -> 282; null controls makes the remaining body
    // unreachable. Check that destination is exactly Return/Nothing/End.
    return exact_script_shape(read,a,widget_register_bytes,widget_register_offsets,av) &&
        exact_script_shape(read,r,widget_unregister_bytes,widget_unregister_offsets,rv) &&
        exact_script_shape(read,c,widget_controls_null_prefix_bytes,widget_controls_null_prefix_offsets,cv) &&
        local_read<uint8_t>(c+282)==4 && local_read<uint8_t>(c+283)==11 && local_read<uint8_t>(c+284)==83;
}
