#pragma once
#include "npc_clea_owner.h"
namespace e33_npc_presentation {
struct ResearchStatus {
    uint32_t owned=0,construction=0,retirement=0,unreviewed=0;
    CallIdentity actor{};uint32_t guid[4]{};CallIdentity unexpected_controller{};
    uint64_t retained_targets=0;CallIdentity body{},face{},hair{};
    uint32_t step=0,reserved=0;
};
static_assert(sizeof(ResearchStatus)==128,"Bounded NPC research status extent");
struct PreviewStatus {
    uint32_t result=7,samples=0,support=0,clearance=0,verified=0;
    uint32_t attempted=0,acknowledged=0,accepted=0,readback=0,at_construction=0;
    double minimum=0,maximum=0,destination[3]{},before[6]{},after[6]{};
};
static_assert(sizeof(PreviewStatus)==176,"Bounded NPC placement status extent");
struct ArenaStatus {
    uint32_t requested=0,attempted=0,assigned=0,verified=0,temporary_live=0,leases=0,reserved[2]{};
    CallIdentity arena{};
};
static_assert(sizeof(ArenaStatus)==48,"Bounded NPC arena value status");
class ResearchService {
    CleaOwner owner_{};uint64_t token_=0;
    void output(MeshPacket& packet){
        ResearchStatus status{};status.owned=owner_.has_work()?1:0;
        status.construction=uint32_t(owner_.lifecycle().construction().phase);
        status.retirement=uint32_t(owner_.lifecycle().retirement());
        status.unreviewed=owner_.unreviewed_script_components();status.actor=owner_.state().actor;
        std::memcpy(status.guid,owner_.state().original_guid,16);status.unexpected_controller=owner_.unexpected_controller();
        status.retained_targets=owner_.retained_target_count();
        status.body=owner_.assembly().body.component;status.face=owner_.assembly().face.component;status.hair=owner_.assembly().hair.component;
        status.step=owner_.step();status.reserved=uint32_t(owner_.entry_phase());
        std::memcpy(reinterpret_cast<uint8_t*>(&packet)+4096,&status,sizeof(status));
        if(packet.operation>=139&&packet.operation<=142){
            const auto& p=owner_.preview();const auto& j=p.placement;PreviewStatus preview{};
            preview.result=owner_.preview_result();preview.samples=p.samples;preview.support=p.support?1:0;
            preview.clearance=p.clearance?1:0;preview.verified=p.verified?1:0;preview.attempted=j.attempted?1:0;
            preview.acknowledged=j.acknowledged?1:0;preview.accepted=j.engine_accepted?1:0;preview.readback=j.readback?1:0;
            preview.at_construction=p.at_construction?1:0;
            preview.minimum=p.minimum;preview.maximum=p.maximum;std::memcpy(preview.destination,p.destination,24);
            std::memcpy(preview.before,j.before.location,24);std::memcpy(preview.before+3,j.before.rotation,24);
            std::memcpy(preview.after,j.after.location,24);std::memcpy(preview.after+3,j.after.rotation,24);
            std::memcpy(reinterpret_cast<uint8_t*>(&packet)+4240,&preview,sizeof(preview));
        }
        if(packet.operation==142)std::memcpy(reinterpret_cast<uint8_t*>(&packet)+4416,&owner_.reveal_status(),sizeof(PreviewReveal));
        if(packet.operation==143||packet.operation==144){
            const auto& state=owner_.arena_state();ArenaStatus arena{};
            arena.requested=owner_.arena_requested()?1:0;arena.attempted=state.attempted?1:0;
            arena.assigned=state.assigned?1:0;arena.verified=state.verified?1:0;arena.temporary_live=state.temporary_live?1:0;
            arena.leases=uint32_t(owner_.arena_lease_count());arena.arena=owner_.bound_arena();
            std::memcpy(reinterpret_cast<uint8_t*>(&packet)+4432,&arena,sizeof(arena));
        }
    }
public:
    bool has_work()const{return owner_.has_work();}
    void poll_entry(uint64_t base){owner_.poll_entry(base);}
    template<class Pool> bool note_entry_dispatch(uint64_t base,uint64_t session,Pool& pool,uint64_t token,
            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function){
        return token&&token==token_&&owner_.note_entry_dispatch(base,session,pool,actor,manager,function);
    }
    template<class Pool> bool owned_parameter_instance_name(uint64_t base,uint64_t session,Pool& pool,uint64_t token,
            const CallIdentity& observed,uint64_t& name){
        name=0;
        return token&&token==token_&&owner_.owned_parameter_instance_name(base,session,pool,observed,name);
    }
    template<class Pool> bool owned_entry_context(uint64_t base,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,
            const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
        name=0;return token&&token==token_&&owner_.owned_entry_context(base,session,pool,actor,manager,function,name);
    }
    template<class Pool> bool owned_entry_arena(uint64_t base,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,CallIdentity& arena){
        arena={};return token&&token==token_&&owner_.owned_entry_arena(base,session,pool,actor,arena);
    }
    template<class Pool> bool copy_entry_arena(uint64_t base,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,
            const CallIdentity& arena,void* destination){
        return token&&token==token_&&owner_.copy_entry_arena(base,session,pool,actor,arena,destination);
    }
    void snapshot(MeshPacket& packet){output(packet);}
    template<class Pool> uint32_t close(uint64_t base,uint64_t session,Pool& pool){
        const auto error=owner_.close(base,session,pool);
        if(!owner_.has_work())token_=0;
        return error;
    }
    template<class Pool> void command(uint64_t base,uint64_t session,Pool& pool,MeshPacket& packet,bool enemy_owned){
        auto* raw=reinterpret_cast<uint8_t*>(&packet);
        const bool grounded=packet.operation==141,stage=packet.operation==136||grounded,status=packet.operation==137,retire=packet.operation==138;
        const bool place=packet.operation==139,placement_status=packet.operation==140,reveal=packet.operation==142;
        const bool arena=packet.operation==143,arena_status=packet.operation==144,proximity=packet.operation==145;
        const bool solid=packet.operation==146,overlap=packet.operation==147;
        if(packet.version!=3||packet.error||packet.state||!packet.owner||(!stage&&!status&&!retire&&!place&&!placement_status&&!reveal&&!arena&&!arena_status&&!proximity&&!solid&&!overlap)){
            packet.error=3450;return;
        }
        for(size_t i=24;i<sizeof(packet);++i){
            if(stage&&((i>=88&&i<376)||(i>=2000&&i<2096)))continue;
            if(grounded&&i>=376&&i<536)continue;
            if((place||proximity)&&i>=88&&i<248)continue;
            if((arena||solid)&&i>=88&&i<152)continue;
            if(overlap&&i>=88&&i<264)continue;
            if(raw[i]){packet.error=3450;return;}
        }
        if(owner_.has_work()&&packet.owner!=token_){packet.error=3451;return;}
        if(solid||overlap){
            if(enemy_owned||!owner_.has_work()||packet.owner!=token_){packet.error=3452;output(packet);return;}
            CallIdentity query[11]{};std::memcpy(query,raw+88,(solid?4:11)*sizeof(CallIdentity));
            for(unsigned i=0;i<(solid?4U:11U);++i)if(query[i].index<0||query[i].serial<0||query[i].address<0x10000){packet.error=3450;return;}
            if(solid){CallIdentity functions[4]{};std::memcpy(functions,query,sizeof(functions));packet.error=owner_.enable_solid_collision(base,session,pool,functions);}
            else{uint32_t result=0;packet.error=owner_.observe_overlap(base,session,pool,query,result);if(!packet.error)std::memcpy(raw+4568,&result,4);}
            std::memcpy(raw+4536,&owner_.collision_variant(),sizeof(CollisionVariant));
        }else if(proximity){
            if(enemy_owned||!owner_.has_work()||packet.owner!=token_){packet.error=3452;output(packet);return;}
            CallIdentity query[10]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(id.index<0||id.serial<0||id.address<0x10000){packet.error=3450;return;}
            double observed[7]{};packet.error=owner_.observe_proximity(base,session,pool,query,observed);
            if(!packet.error)std::memcpy(raw+4480,observed,sizeof(observed));
        }else if(arena){
            if(enemy_owned||!owner_.has_work()||packet.owner!=token_){packet.error=3452;output(packet);return;}
            CallIdentity query[4]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(id.index<0||id.serial<0||id.address<0x10000){packet.error=3450;return;}
            packet.error=owner_.bind_preview_arena(base,session,pool,query);
        }else if(reveal){
            if(enemy_owned||!owner_.has_work()||packet.owner!=token_){packet.error=3452;output(packet);return;}
            packet.error=owner_.reveal_preview(base,session,pool);
        }else if(place){
            if(enemy_owned||!owner_.has_work()||packet.owner!=token_){packet.error=3452;output(packet);return;}
            CallIdentity query[10]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(id.index<0||id.serial<0||id.address<0x10000){packet.error=3450;return;}
            const auto result=owner_.place_preview_grounded(base,session,pool,query);
            if(result!=PreviewPlacementResult::Complete)packet.error=3460+uint32_t(result);
        }else if(stage){
            if(enemy_owned||owner_.has_work()){packet.error=3452;output(packet);return;}
            CallIdentity ids[18]{};std::memcpy(ids,raw+88,sizeof(ids));
            for(const auto& id:ids)if(id.index<0||id.serial<0||id.address<0x10000){packet.error=3450;return;}
            ConstructionSource source{};
            source.controller=ids[0];source.world=ids[1];source.gameplay_statics=ids[2];source.actor_class=ids[3];
            source.cdo=ids[4];source.available=ids[5];source.begin=ids[6];source.finish=ids[7];source.destroy=ids[8];
            source.collision=ids[9];source.tick=ids[10];source.hidden=ids[11];source.movement=ids[12];
            std::memcpy(source.transform,raw+2000,96);
            RetirementBindings bindings{};bindings.interaction_system=ids[13];bindings.unregister_nearby=ids[14];bindings.unregister_distant=ids[15];
            token_=packet.owner; // persisted before any allocation/lease acquisition
            CallIdentity query[10]{};
            if(grounded){
                std::memcpy(query,raw+376,sizeof(query));
                for(const auto& id:query)if(id.index<0||id.serial<0||id.address<0x10000){packet.error=3450;return;}
            }
            packet.error=owner_.stage(base,session,pool,source,bindings,ids[16],ids[17],grounded?query:nullptr);
            if(!owner_.has_work())token_=0;
        }else if(retire){
            packet.error=close(base,session,pool);
        }
        output(packet);if(!packet.error)packet.state=1;
    }
};
}
