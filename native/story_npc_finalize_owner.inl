// Only existing hidden owned actors may be finalized. Construction and pose
// qualification remain separate; no arbitrary command or actor batch exists.
template<class Pool> void finalize_story_npc(uint64_t b,uint64_t session,Pool& pool,
        e33_story_npc_finalize::Packet& p,Owner* visual){
    using namespace e33_story_npc_finalize;
    if(!valid(p)){p.error=rejected;return;}
    struct Ops {
        Owner& carrier;Owner* visual;uint64_t base,session;Pool& pool;const Packet& packet;
        e33_story_npc::Packet configuration{};
        bool current(){
            if(!carrier.proves_story_resource(base,session,pool,packet.owner,packet.npc))return false;
            const auto player=zone_ref(base,carrier.ids_[0].address,"Player"),viewport=zone_ref(base,player,"ViewportClient");
            if(!player||!viewport||zone_ref(base,player,"PlayerController")!=carrier.ids_[0].address||
               zone_ref(base,viewport,"World")!=carrier.ids_[2].address)return false;
            if(!packet.show_visual)return visual==nullptr;
            if(!visual||visual==&carrier||!visual->timeline_only_||!visual->preparing_world_||
               visual->owner_!=packet.visual_owner||!visual->lease_||
               visual->construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
               std::memcmp(&packet.visual,&visual->actor_,16)||!call_identity(base,visual->actor_)||
               !pool.owns_object(session,visual->lease_,visual->actor_.address)||
               !visual->current(base)||std::memcmp(carrier.ids_,visual->ids_,3*sizeof(CallIdentity)))return false;
            const auto cls=local_read<uint64_t>(visual->actor_.address+16);
            if(cls!=visual->ids_[4].address||local_read<uint32_t>(visual->actor_.address+8)&0x40018030U)return false;
            for(const auto& row:e33_timeline_blueprint::profiles){
                // Presentation characters only, never portals/cameras/walls.
                if((!std::strncmp(row.name,"BP_Cine_",8)||
                    !std::strcmp(row.name,"BP_JRPG_NPC_Dialog_NPC_Sophie_NoInteraction_C")||
                    !std::strcmp(row.name,"BP_jRPG_NPC_Dialog_SpiritClea_C")||
                    !std::strcmp(row.name,"BP_jRPG_NPC_Dialog_RenoirSpirit_C"))&&named(base,cls,row.name,row.package))return true;
            }
            return false;
        }
        bool validate(){
            if(!current()||carrier.timeline_reveal_.attempted||
               (visual&&visual->timeline_reveal_.attempted))return false;
            configuration.owner=packet.owner;configuration.npc=packet.npc;configuration.dialogue_class=packet.dialogue_class;
            configuration.speaker=packet.speaker;configuration.system_cdo=packet.system_cdo;
            std::memcpy(configuration.definitions,packet.definitions,sizeof(configuration.definitions));configuration.activate=1;
            carrier.configure_story_npc(base,session,pool,configuration,packet.interaction!=0,true);
            const bool ready=!configuration.error&&configuration.state==1;
            configuration.error=0;configuration.state=0;return ready;
        }
        bool perform(uint32_t step){
            if(step==4){
                carrier.configure_story_npc(base,session,pool,configuration,packet.interaction!=0);
                return !configuration.error&&configuration.state==1;
            }
            auto& owner=step==1?carrier:*visual;
            MeshPacket request{};request.version=3;request.operation=221;request.owner=owner.owner_;
            owner.command(base,session,pool,request);return !request.error&&request.state==1;
        }
        bool shown(Owner& owner,bool collision){
            uint64_t hidden_field=0,collision_field=0;
            const auto hidden=picto_field(base,owner.actor_.address,"bHidden","BoolProperty",88,1,&hidden_field);
            const auto enabled=picto_field(base,owner.actor_.address,"bActorEnableCollision","BoolProperty",92,1,&collision_field);
            return hidden&&enabled&&local_read<uint32_t>(hidden_field+0x70)==0x80800001U&&
                local_read<uint32_t>(collision_field+0x70)==0x80800001U&&!(local_read<uint8_t>(hidden)&0x80)&&
                bool(local_read<uint8_t>(enabled)&0x80)==collision;
        }
        bool verify(){return current()&&carrier.story_npc_.active&&shown(carrier,packet.interaction!=0)&&(!visual||shown(*visual,false));}
    } ops{*this,visual,b,session,pool,p};
    const auto result=run(story_finalize_,p.show_visual!=0,ops);
    p.error=result.error;p.completed=result.completed;p.attempted=result.attempted;
    if(!p.error)p.state=1;
}
