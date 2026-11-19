// Called only in the same game-thread transaction as FinishSpawningActor.
// This is the existing arena staging flag discipline, scoped to the exact
// disposable story source. No class default or unrelated source is changed.
template<class Pool> uint32_t stage_story_streaming_source(uint64_t b,uint64_t session,Pool& pool){
    struct Ops {
        Owner& owner;uint64_t base,session;Pool& pool;
        bool observe(e33_story_source_staging::Observation& out){
            if(!owner.timeline_only_||!owner.preparing_world_||!owner.owner_||!owner.lease_||
               owner.construction_.phase!=e33_owned_actor::ConstructionPhase::FinalizationPending||
               !owner.current(base)||!call_identity(base,owner.actor_)||
               !pool.owns_object(session,owner.lease_,owner.actor_.address)||
               local_read<uint64_t>(owner.actor_.address+16)!=owner.ids_[4].address||
               !named(base,owner.ids_[4].address,"BP_WP_StreamingSourceComponent_C",
                   "/Game/Gameplay/GameplayElement/Content/StreamingSource/BP_WP_StreamingSourceComponent"))return false;
            const auto player=zone_ref(base,owner.ids_[0].address,"Player"),viewport=zone_ref(base,player,"ViewportClient");
            if(!call_capture(base,player).address||!call_capture(base,viewport).address||
               zone_ref(base,player,"PlayerController")!=owner.ids_[0].address||
               zone_ref(base,viewport,"World")!=owner.ids_[2].address)return false;
            for(const auto value:{owner.actor_.address,owner.ids_[0].address,owner.ids_[2].address,player,viewport})
                if(local_read<uint32_t>(value+8)&0x40018030U)return false;
            // zone_ref proves the exact reflected ObjectProperty owner/type,
            // bounded field extent and fresh reference; no actor offset guess.
            const auto component=zone_ref(base,owner.actor_.address,"WorldPartitionStreamingSource");
            if(!call_capture(base,component).address||local_read<uint64_t>(component+32)!=owner.actor_.address||
               local_read<uint32_t>(component+8)&0x40018030U)return false;
            const auto cls=local_read<uint64_t>(component+16);
            if(!call_is_class(base,cls)||!named(base,cls,"WorldPartitionStreamingSourceComponent","/Script/Engine")||
               local_read<int32_t>(cls+0x58)!=256)return false;
            uint64_t descriptor=0;
            const auto flag=picto_field(base,component,"bStreamingSourceEnabled","BoolProperty",249,1,&descriptor);
            if(!flag||local_read<uint64_t>(descriptor)!=base+0x6e119b0||local_read<uint64_t>(descriptor+16)!=(cls|1)||
               local_read<uint64_t>(descriptor+0x38)!=20266276706320901ULL||
               local_read<uint32_t>(descriptor+0x70)!=0xff010001U)return false;
            out={component,flag,local_read<uint8_t>(flag)};return out.enabled<=1;
        }
        bool write(const e33_story_source_staging::Observation& expected){
            e33_story_source_staging::Observation fresh{};
            if(!observe(fresh)||fresh.component!=expected.component||fresh.field!=expected.field||fresh.enabled!=expected.enabled)return false;
            const uint8_t disabled=0;
            std::memcpy(reinterpret_cast<void*>(fresh.field),&disabled,1);return true;
        }
    } ops{*this,b,session,pool};
    return e33_story_source_staging::disable(story_streaming_staging_,ops);
}
