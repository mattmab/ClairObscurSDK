#pragma once
#include "sequence_owner_protocol.h"
#include "sequence_settings_schema.h"
#ifdef E33_EMPTY_TITLE_SESSION
#include "cinematic_empty_title.h"
#endif

#ifdef E33_SEQUENCE_CAMERA_SESSION
#include "sequence_camera_owner.h"
#endif

#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
#include "sequence_binding_query_owner.h"
#endif

// Prepare native cleanup before factory dispatch. The runtime atomically adopts
// both returned objects before replying; a dead controller cannot strand a
// successfully created actor without an owner. Unknown mutation quarantines.
class SequenceOwner {
    uint64_t owner_=0, tokens_[2]{};
    CallPacket plans_[2]{};
    uint32_t state_=0,step_=0;
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
    SequenceBindingQueryOwner binding_query_;
    CallIdentity binding_asset_{};
    uint64_t binding_session_=0;
#endif
#ifdef E33_SEQUENCE_CAMERA_SESSION
    SequenceCameraOwner camera_;
#endif
#ifdef E33_EMPTY_TITLE_SESSION
    inline static SequenceOwner* empty_title_owner_=nullptr;
    CallIdentity empty_title_{};
    static uint32_t before_play(uint64_t base,const CallPacket& call) {
        auto* self=empty_title_owner_;
        if(!self || !self->empty_title_.address ||
           std::memcmp(&call.target,&self->plans_[0].target,sizeof(CallIdentity))) return 0;
        const auto fn=call_identity(base,call.function);
        if(!fn || !exact_name(base,fn+24,"Play")) return 0;
        const auto owner=local_read<uint64_t>(fn+32);
        if(!e33_empty_title::named(base,owner,"MovieSceneSequencePlayer","/Script/MovieScene")) return 0;
        return self->state_==1 && cinematic_empty_trap_armed && cinematic_empty_trap_armed(call.target) &&
            e33_empty_title::validate(base,self->empty_title_) ? 0 : 1474;
    }
#endif
    static bool empty(const void* p,size_t n) {
        auto b=static_cast<const uint8_t*>(p);
        for(size_t i=0;i<n;++i) if(b[i]) return false;
        return true;
    }
    static bool exact_class(uint64_t base,uint64_t object,const char* name,const char* package) {
        if(!call_capture(base,object).address) return false;
        const auto cls=local_read<uint64_t>(object+0x10);
        return call_is_class(base,cls) && exact_name(base,cls+0x18,name) &&
            exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,package);
    }
    static bool settings(uint64_t base,uint64_t property,const CallIdentity& id) {
        TargetPodSchemaOps ops{base};
        return property && local_read<uint64_t>(property)==base+0x6e136a0 &&
            local_read<uint64_t>(property+0x70)==id.address &&
            sequence_settings_schema(ops,id,"MovieSceneSequencePlaybackSettings");
    }
public:
    bool active() const { return state_!=0
#ifdef E33_SEQUENCE_CAMERA_SESSION
        || camera_.active()
#endif
        ; }
#ifdef E33_SEQUENCE_CAMERA_SESSION
    uint32_t camera_private_active() const {return camera_.private_active();}
    uint32_t camera_private_peak() const {return camera_.private_peak();}
    uint32_t admit_owned_camera(const CallIdentity& camera,
        bool (*proof)(uint64_t,const CallIdentity&,const CallIdentity&)) {
        return state_==1 ? camera_.admit_owned(camera,proof) : 1571;
    }
#endif
    bool owns_player(const CallIdentity& id) const {
        return state_==1 && !std::memcmp(&plans_[0].target,&id,sizeof(id));
    }
#ifdef E33_EMPTY_TITLE_SESSION
    bool owns_empty_title_player(const CallIdentity& id) const {
        return empty_title_.address && owns_player(id);
    }
#endif
    bool protects(uint64_t token) const { return active() && (state_==2 || token==tokens_[0] || token==tokens_[1]); }
    uint32_t close(uint64_t base) {
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
        // Never destroy the player beneath an uncertain query allocation.
        if(binding_query_.uncertain()) return 1583;
        if(auto error=binding_query_.close()) return error;
#endif
        if(!state_) {
#ifdef E33_SEQUENCE_CAMERA_SESSION
            return camera_.close();
#else
            return 0;
#endif
        }
        if(state_==2) return 1473;
        if(state_==3) {
#ifdef E33_SEQUENCE_CAMERA_SESSION
            if(auto error=camera_.close()) return error;
#endif
            state_=0; return 0;
        }
        while(step_<2) {
#ifdef E33_SEQUENCE_CAMERA_SESSION
            // Stop has returned. Restore or positively confirm original view
            // before destroying our sequence actor and releasing camera holds.
            if(step_==1 && camera_.active()) {if(auto error=camera_.close()) return error;}
#endif
            auto call=plans_[step_];
            state_=2;
            const auto error=reflected_call(base,call);
            if(error==201 && call.outcome==CallNotDispatched) { state_=1; return 407; }
            if(error || call.outcome!=CallDispatchReturned) return 1473;
            ++step_; state_=1;
        }
#ifdef E33_EMPTY_TITLE_SESSION
        if(empty_title_owner_==this) empty_title_owner_=nullptr;
        empty_title_={};
#endif
        state_=0; return 0;
    }
    void command(uint64_t base,const TargetMenuStorage& menu,SequenceOwnerPacket& p) {
        if(p.version!=1 || !p.owner || p.reserved || p.error || p.state || p.operation<1 || p.operation>
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
            5
#elif defined(E33_SEQUENCE_CAMERA_SESSION)
            4
#else
            3
#endif
            ) { p.error=1470; return; }
        p.state=state_;
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
        if(p.operation==5) {
            SequenceBindingQueryPacket query{};std::memcpy(&query,&p.stop,sizeof(query));
            const auto* payload=reinterpret_cast<const uint8_t*>(&p.stop);
            if(state_!=1 || p.owner!=owner_ || query.magic!=0x51423345 || query.version!=1 ||
               (query.profile!=1 && query.profile!=2) || query.reserved ||
               !empty(&query.completed,32) || !empty(payload+64,sizeof(p.stop)+sizeof(p.destroy)-64)) {p.error=1581;return;}
            p.error=binding_query_.run(base,binding_session_,plans_[0].target,plans_[1].target,binding_asset_,query);
            std::memcpy(&p.stop,&query,sizeof(query));return;
        }
#endif
#ifdef E33_SEQUENCE_CAMERA_SESSION
        if(p.operation==4) {
            if(state_!=3 || p.owner!=owner_ || !menu.menu.active() || !empty(&p.stop,sizeof(p.stop))) {p.error=1571;return;}
            p.error=camera_.arm(base,p.owner,menu.player,p.destroy);p.state=state_;return;
        }
#endif
        if(p.operation!=1) {
            if(p.owner!=owner_ || !empty(&p.stop,sizeof(p.stop)) || !empty(&p.destroy,sizeof(p.destroy))) { p.error=1471; return; }
            if(p.operation==2) p.error=close(base);
            p.state=state_; return;
        }
        if(active() || !menu.menu.active()) { p.error=1471; return; }
        const CallPacket* plans[]={&p.stop,&p.destroy};
        for(unsigned i=0;i<2;++i) {
            const auto& c=*plans[i];
            const auto fn=call_identity(base,c.function), cleanup_target=call_identity(base,c.target);
            const auto owner=fn ? local_read<uint64_t>(fn+0x20) : 0;
            if(validate_call_packet(c) || c.parameter_size || c.allocation_extent || c.field_count || c.object_count ||
               c.return_offset!=65535 || !fn || !cleanup_target || !(local_read<uint32_t>(cleanup_target+8)&0x10) ||
               !exact_class(base,cleanup_target,i ? "LevelSequenceActor" : "LevelSequencePlayer","/Script/LevelSequence") ||
               !exact_name(base,fn+0x18,i ? "K2_DestroyActor" : "Stop") ||
               !exact_name(base,owner+0x18,i ? "Actor" : "MovieSceneSequencePlayer") ||
               !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,i ? "/Script/Engine" : "/Script/MovieScene")) { p.error=1471; return; }
            auto copy=c;
            if(reflected_call(base,copy,nullptr,nullptr,nullptr,nullptr,true)) { p.error=1472; return; }
        }
        plans_[0]=p.stop; plans_[1]=p.destroy; tokens_[0]=tokens_[1]=0;
        owner_=p.owner; step_=0; state_=p.state=3;
    }
    template<class Pool>
    uint32_t create(uint64_t base,uint64_t session,Pool& leases,const TargetMenuStorage& menu,
                    RetainedCallPacket& packet,const CallRetention* retention,const CallPodValidation* pod,
                    const CallEntryValidation* entry) {
        if(state_!=3 || !menu.menu.active()) return 1471;
#ifdef E33_SEQUENCE_CAMERA_SESSION
        if(camera_.active() && !camera_.ready()) return 1573;
#endif
        if(auto error=validate_sequence_call(packet)) return error;
        // This candidate uses the owned menu's live player as world context.
        // That connects creation to the same input/world lifecycle as the panel.
        if(std::memcmp(&packet.call.objects[0].identity,&menu.player,sizeof(CallIdentity))) return 1471;
        CallSequenceValidation validation{&packet,settings};
        RetainedCallPacket check=packet; validation.packet=&check;
        if(auto error=reflected_call(base,check.call,retention,pod,nullptr,nullptr,true,entry,false,nullptr,&validation)) return error;
        validation.packet=&packet;
#ifdef E33_EMPTY_TITLE_SESSION
        const auto candidate=packet.call.objects[1].identity;
        const bool empty_title=e33_empty_title::is_back_at_camp(base,candidate);
        if(empty_title && !e33_empty_title::validate(base,candidate)) return 1474;
#endif
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
        const auto binding_asset=packet.call.objects[1].identity;
#endif
        state_=2;
        const auto error=reflected_call(base,packet.call,retention,pod,nullptr,nullptr,false,entry,false,nullptr,&validation);
        if(packet.call.outcome==CallNotDispatched) { state_=3; return error; }
        if(error || packet.call.outcome!=CallDispatchReturned) return error ? error : 1473;
        CallIdentity actor{-1,0,0},player{-1,0,0};
        for(unsigned i=0;i<packet.call.object_count;++i) {
            const auto& o=packet.call.objects[i];
            if(o.offset==56) actor=o.identity;
            if(o.offset==64) player=o.identity;
        }
        if(!actor.address && !player.address && !packet.count) { state_=3; return 0; }
        for(unsigned i=0;i<packet.count;++i) {
            if(packet.leases[i].offset==64) tokens_[0]=packet.leases[i].token;
            if(packet.leases[i].offset==56) tokens_[1]=packet.leases[i].token;
        }
        if(!call_identity(base,actor) || !call_identity(base,player) ||
           !exact_class(base,actor.address,"LevelSequenceActor","/Script/LevelSequence") ||
           !exact_class(base,player.address,"LevelSequencePlayer","/Script/LevelSequence") ||
           local_read<uint64_t>(player.address+0x20)!=actor.address ||
           !tokens_[0] || !tokens_[1] || !leases.owns_object(session,tokens_[0],player.address) ||
           !leases.owns_object(session,tokens_[1],actor.address)) return 1473;
        plans_[0].target=player; plans_[1].target=actor;
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
        binding_asset_=binding_asset;binding_session_=session;
#endif
        for(auto& plan:plans_) {
            auto check_plan=plan;
            if(reflected_call(base,check_plan,nullptr,nullptr,nullptr,nullptr,true)) return 1473;
        }
#ifdef E33_EMPTY_TITLE_SESSION
        empty_title_=empty_title ? candidate : CallIdentity{};
        empty_title_owner_=empty_title ? this : nullptr;
        cinematic_play_preflight=&before_play;
#endif
#ifdef E33_SEQUENCE_CAMERA_SESSION
        if(camera_.active() && !camera_.created(player)) return 1573;
#endif
        state_=1; return 0;
    }
};
