// Fixed CharacterName setter on a leased data asset whose Outer is this
// retained story carrier. Never mutates shared assets, CDOs or game actors.
template<class Pool,class Dispatcher> void configure_story_speaker(uint64_t b,uint64_t session,Pool& pool,e33_story_speaker::Packet& p,Dispatcher& dispatcher){
 using namespace e33_story_speaker;
 if(!valid(p)||story_speaker_named_||story_npc_.configure_attempted||!timeline_only_||owner_!=p.owner||!lease_||
    construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
    std::memcmp(&p.npc,&actor_,sizeof(actor_))||!current(b)||!call_identity(b,actor_)||
    !pool.owns_object(session,lease_,actor_.address)||
    !named(b,local_read<uint64_t>(actor_.address+16),"BP_NPC_Dialogue_Empty_FacelessBoyFinale_C","/Game/Characters/NPCs/Lumiere/DialogueNPCs/WalkToHarbour/BP_NPC_Dialogue_Empty_FacelessBoyFinale")){
  p.error=rejected;return;
 }
 const auto speaker=call_identity(b,p.speaker),cdo=call_identity(b,p.system_cdo),setter=call_identity(b,p.setter);
 if(!speaker||!cdo||!setter||!pool.owns_object(session,p.speaker_lease,speaker)||
    local_read<uint64_t>(speaker+32)!=actor_.address||(local_read<uint32_t>(speaker+8)&0x40000030U)||
    !named(b,local_read<uint64_t>(speaker+16),"BP_DataAsset_DialogueCharacter_C","/Game/Gameplay/DialogueSystem/BP_DataAsset_DialogueCharacter")||
    !named(b,cdo,"Default__KismetSystemLibrary","/Script/Engine")||!dispatcher.empty()){
  p.error=rejected;return;
 }
 uint64_t field=0;
 const auto name_slot=picto_field(b,speaker,"CharacterName","TextProperty",48,16,&field);
 if(!name_slot){p.error=rejected;return;}
 static const MeshField fields[]={
  {"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
  {"PropertyName","NameProperty",8,8,6755469234274944ULL,0x6e13040ULL,"","",0,"",0U,""},
  {"Value","TextProperty",16,16,4503599761588610ULL,0x6e1ba00ULL,"","",0,"",0U,""},
 };
 static const MeshFunction function={"KismetSystemLibrary","SetTextPropertyByName",71443459,32,32,65535,0x387d880ULL,fields,3};
 e33_engine_profile_call::TargetOps call{b,setter,cdo,function,nullptr};
 if(!call.context()||!call.exact_profile()||!call.recipient_derives()||!call.dispatch_entry()){
  p.error=rejected;return;
 }
 TargetOwnedTextOps text_ops{b};
 auto& frame=dispatcher.frame;
 frame.count=0;frame.state=e33_dialogue_text::State::Empty;
 e33_dialogue_text::Input input{p.text,p.count};
 if(!frame.prepare(text_ops,&input,1)||!frame.begin(text_ops)){p.error=uncertain;return;}
 auto& args=dispatcher.arguments;std::memset(args,0,sizeof(args));
 std::memcpy(args,&speaker,8);
 const auto name=local_read<uint64_t>(field+32);std::memcpy(args+8,&name,8);
 std::memcpy(args+16,&frame.elements[0],16);call.arguments=args;
 story_speaker_named_=true;call.dispatch_once();
 if(!frame.returned()){p.error=uncertain;return;}
 // Verify copied display text, without treating the asset's FText as ours.
 auto value=local_read<TargetTextValue>(name_slot);
 if(!text_ops.known_text(value)){p.error=uncertain;return;}
 const auto display=text_ops.display_string(value);
 if(display.count!=int32_t(p.count)||display.capacity<display.count||!display.data||
    std::memcmp(reinterpret_cast<const void*>(display.data),p.text,p.count*2)){
  p.error=uncertain;return;
 }
 if(!frame.cleanup(text_ops)){p.error=uncertain;return;}
 std::memset(args,0,sizeof(args));p.state=1;
}
