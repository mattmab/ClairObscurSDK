#pragma once
#include "retired_world_target.h"
#include "music_audio_profile.h"
#include "audio_pause_journal.h"

namespace e33_cinematic {
inline bool current_music_gi(uint64_t base,e33_retired_world::Snapshot& snapshot,CallIdentity& gi) {
    e33_retired_world::TargetOps ops{base};e33_retired_world::Snapshot first{},second{};
    if(!ops.observe(first)||!ops.observe(second)||
       !e33_retired_world::same(first.engine,second.engine)||
       !e33_retired_world::same(first.viewport,second.viewport)||
       !e33_retired_world::same(first.world,second.world))return false;
    const auto value=ops.reference(second.world.address,"World","OwningGameInstance");
    if(!ops.live(value)||!picto_class(base,value,"BP_jRPG_GI_Custom_C",
       "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom"))return false;
    gi=call_capture(base,value);snapshot=second;
    return gi.address&&ops.current_binding(second.engine,second.viewport,second.world)&&
        ops.reference(second.world.address,"World","OwningGameInstance")==value;
}
inline AudioPauseCertificate current_original_audio(uint64_t base,const CallIdentity& expected_gi,
        const CallIdentity& original_system,const CallIdentity& audio,const CallIdentity& component) {
    e33_retired_world::Snapshot snapshot{};CallIdentity gi{};
    if(!current_music_gi(base,snapshot,gi))return AudioPauseCertificate::Pending;
    if(!e33_retired_world::same(gi,expected_gi))return AudioPauseCertificate::Foreign;
    e33_retired_world::TargetOps ops{base};
    if(zone_ref(base,gi.address,"InteractiveMusicSystem")!=original_system.address||
       !ops.live(original_system.address)||!call_identity(base,original_system))return AudioPauseCertificate::Foreign;
    MusicAudioReferences now{};
    if(!music_audio_references(base,original_system,audio,now))return AudioPauseCertificate::Unknown;
    bool found=false;
    for(unsigned i=0;i<now.count;++i)found|=e33_retired_world::same(now.items[i],component);
    if(!found||!call_identity(base,component)||!ops.live(component.address))return AudioPauseCertificate::Foreign;
    e33_retired_world::Snapshot after{};CallIdentity after_gi{};
    if(!current_music_gi(base,after,after_gi))return AudioPauseCertificate::Pending;
    if(!e33_retired_world::same(snapshot.world,after.world)||
       !e33_retired_world::same(gi,after_gi))return AudioPauseCertificate::Pending;
    return zone_ref(base,gi.address,"InteractiveMusicSystem")==original_system.address ?
        AudioPauseCertificate::Current : AudioPauseCertificate::Foreign;
}
}
