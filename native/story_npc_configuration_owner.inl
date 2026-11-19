// Public member of the existing retained Blueprint actor journal. No arbitrary
// actor may be configured: token, constructed actor, class and world must match.
template<class Pool> void configure_story_npc(uint64_t b,uint64_t session,Pool& pool,e33_story_npc::Packet& p,bool collision_enabled=true,bool validate_only=false){
    using namespace e33_story_npc;
    if(!valid(p)||!timeline_only_||owner_!=p.owner||!lease_||
       construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
       std::memcmp(&p.npc,&actor_,sizeof(actor_))||!current(b)||!call_identity(b,actor_)||
       !pool.owns_object(session,lease_,actor_.address)||local_read<uint64_t>(actor_.address+16)!=ids_[4].address||
       !named(b,ids_[4].address,"BP_NPC_Dialogue_Empty_FacelessBoyFinale_C","/Game/Characters/NPCs/Lumiere/DialogueNPCs/WalkToHarbour/BP_NPC_Dialogue_Empty_FacelessBoyFinale")){
        p.error=rejected;return;
    }
    const auto cls=call_identity(b,p.dialogue_class),speaker=call_identity(b,p.speaker),cdo=call_identity(b,p.system_cdo);
    if(!cls||!speaker||!cdo||!call_is_class(b,cls)||
       !named(b,cls,"BP_Dialogue_C","/Game/Gameplay/DialogueSystem/BP_Dialogue")||
       !named(b,local_read<uint64_t>(speaker+16),"BP_DataAsset_DialogueCharacter_C","/Game/Gameplay/DialogueSystem/BP_DataAsset_DialogueCharacter")||
       !named(b,cdo,"Default__KismetSystemLibrary","/Script/Engine")){
        p.error=rejected;return;
    }
    uint64_t class_field=0,speaker_field=0,bool_field=0;
    const auto class_slot=picto_field(b,actor_.address,"DialogueToPlay","ClassProperty",2080,8,&class_field);
    const auto speaker_slot=picto_field(b,actor_.address,"DialogueCharacter","ObjectProperty",2048,8,&speaker_field);
    const auto bool_slot=picto_field(b,actor_.address,"CanBeInteractedWith","BoolProperty",2288,1,&bool_field);
    if(!class_slot||!speaker_slot||!bool_slot||local_read<uint64_t>(class_field+0x78)!=cls||
       local_read<uint64_t>(speaker_field+0x70)!=local_read<uint64_t>(speaker+16)||local_read<uint32_t>(bool_field+0x70)!=0xff010001U){
        p.error=rejected;return;
    }
    struct Ops {
        uint64_t base,actor,cls,character,cdo,class_slot,speaker_slot,class_name,speaker_name,bool_name;
        const Packet& packet;
        bool preflight(){
            for(unsigned i=0;i<4;++i){
                const auto function=call_identity(base,packet.definitions[i]);
                e33_engine_profile_call::TargetOps ops{base,function,i==3?actor:cdo,functions[i],nullptr};
                if(!ops.context()||!ops.identities()||!ops.exact_profile()||!ops.recipient_derives()||!ops.dispatch_entry())return false;
            }
            return true;
        }
        bool set(unsigned index,uint64_t name,uint64_t value){
            alignas(16) uint8_t arguments[32]{};
            std::memcpy(arguments,&actor,8);std::memcpy(arguments+8,&name,8);std::memcpy(arguments+16,&value,8);
            return e33_engine_profile_call::invoke(base,packet.definitions[index],call_capture(base,cdo),functions[index],arguments);
        }
        bool interactable(bool enabled){return set(2,bool_name,enabled?1ULL:0ULL);}
        bool dialogue(){return set(0,class_name,cls);}
        bool speaker(){return set(1,speaker_name,character);}
        bool collision(bool enabled){
            uint8_t arguments[1]={enabled?uint8_t(1):uint8_t(0)};
            return e33_engine_profile_call::invoke(base,packet.definitions[3],call_capture(base,actor),functions[3],arguments);
        }
        bool matches(){return local_read<uint64_t>(class_slot)==cls&&local_read<uint64_t>(speaker_slot)==character;}
    } ops{b,actor_.address,cls,speaker,cdo,class_slot,speaker_slot,local_read<uint64_t>(class_field+32),
        local_read<uint64_t>(speaker_field+32),local_read<uint64_t>(bool_field+32),p};
    p.error=configure(story_npc_,p.activate!=0,ops,collision_enabled,validate_only);if(!p.error)p.state=1;
}
