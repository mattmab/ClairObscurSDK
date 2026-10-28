#pragma once
#if defined(E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION) && (!defined(E33_SEQUENCE_ORIGIN_SESSION) || !defined(E33_SEQUENCE_ORIGIN_UPDATE_SESSION) || !defined(E33_SEQUENCE_FLIGHT_SESSION))
#error Sequence origin transforms require the origin, update and flight protocols
#endif
#include "sequence_owner_protocol.h"
#include "sequence_settings_schema.h"
#ifdef E33_SEQUENCE_FLIGHT_SESSION
#include "sequence_flight_owner.h"
#endif
#ifdef E33_SEQUENCE_SEEK_SESSION
#include "target_sequence_seek.h"
#if !defined(E33_RETIRED_WORLD_SESSION) || !defined(E33_SEQUENCE_ORIGIN_SESSION) || E33_RUNTIME_CINEMATIC_VERSION<217
#error Sequence seek requires current-world and origin ownership contracts
#endif
#endif
#if defined(E33_RETIRED_WORLD_SESSION) && E33_RUNTIME_CINEMATIC_VERSION>=216
#define E33_SEQUENCE_RETIREMENT_SESSION 1
#include "sequence_retirement.h"
#include "retired_world_target.h"
#endif
#ifdef E33_SEQUENCE_ORIGIN_SESSION
#include "sequence_origin_owner.h"
#include "sequence_cleanup_admission.h"
#endif
#ifdef E33_EMPTY_TITLE_SESSION
#include "cinematic_empty_title.h"
#endif

#ifdef E33_SEQUENCE_CAMERA_SESSION
#include "sequence_camera_owner.h"
#endif

#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
#include "sequence_binding_query_owner.h"
#endif
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
#if !defined(E33_SEQUENCE_BINDING_QUERY_SESSION) || !defined(E33_SEQUENCE_RETIREMENT_SESSION)
#error Authored binding diagnostics require retained sequence and world ownership
#endif
#include <optional>
#include "target_authored_binding_operation.h"
#pragma pack(push,1)
struct SequenceAuthoredBindingPacket {
    uint32_t magic,version,reserved,outcome;
    CallIdentity query_function,target,resolver,root,source;
    uint64_t query_token,target_token,resolver_token,root_token,source_token;
    uint32_t guid[4],count,zeros;
    CallIdentity objects[8];
};
#pragma pack(pop)
static_assert(sizeof(SequenceAuthoredBindingPacket)==288);
#endif

// Prepare native cleanup before factory dispatch. The runtime atomically adopts
// both returned objects before replying; a dead controller cannot strand a
// successfully created actor without an owner. Unknown mutation quarantines.
class SequenceOwner {
    uint64_t owner_=0, tokens_[2]{};
    CallPacket plans_[2]{};
    uint32_t state_=0,step_=0;
#ifdef E33_SEQUENCE_FLIGHT_SESSION
    SequenceFlightOwner flight_;
#endif
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
    e33_retired_world::Snapshot epoch_{};
    CallIdentity epoch_controller_{};
    uint64_t epoch_menu_owner_=0;
    bool retiring_=false;
    bool capture_epoch(uint64_t base,const CallIdentity& controller) {
        e33_retired_world::TargetOps ops{base};e33_retired_world::Snapshot a{},b{};
        if(!ops.observe(a) || a.world.serial<=0 || !ops.controller_world(controller,a.world) || !ops.observe(b) ||
           !e33_retired_world::same(a.engine,b.engine) || !e33_retired_world::same(a.viewport,b.viewport) ||
           !e33_retired_world::same(a.world,b.world)) return false;
        epoch_=a;epoch_controller_=controller;return true;
    }
    bool epoch_current(uint64_t base) const {
        e33_retired_world::TargetOps ops{base};
        return epoch_.world.address && ops.current_binding(epoch_.engine,epoch_.viewport,epoch_.world) &&
            ops.controller_world(epoch_controller_,epoch_.world);
    }
#endif
#ifdef E33_SEQUENCE_ORIGIN_SESSION
    SequenceOriginOwner origin_;
    CallIdentity origin_context_{};
    SequenceCleanupAdmission<CallPacket> cleanup_admission_;
    uint32_t cleanup_stop(uint64_t base,CallPacket& call) {
        if(!cleanup_admission_.begin(call,plans_[0])) return 1593;
        __try {return reflected_call(base,call);}
        __finally {cleanup_admission_.end();}
    }
    inline static SequenceOwner* origin_owner_=nullptr;
    static uint32_t before_origin_play(uint64_t base,const CallPacket& call) {
        auto* self=origin_owner_;
        if(!self || std::memcmp(&call.target,&self->plans_[0].target,sizeof(CallIdentity))) return 0;
        if(self->cleanup_admission_.allows(call)) return 0;
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        if(self->retiring_ || !self->epoch_current(base)) return 1595;
#endif
        const auto fn=call_identity(base,call.function);
        if(!fn) return 1593;
        const auto owner=local_read<uint64_t>(fn+32);
        // Every invocation against the owned player closes configuration,
        // including reverse/loop/seek/evaluate methods and future methods.
        // Merely observing status may conservatively close it too. Python
        // configures immediately after creation, before exposing the player.
        (void)owner;
        return self->state_==1 && self->origin_.before_evaluation() ? 0 : 1593;
    }
#endif
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
    SequenceBindingQueryOwner binding_query_;
    CallIdentity binding_asset_{};
    uint64_t binding_session_=0;
#endif
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
    std::optional<TargetAuthoredBindingOperation<StrongLeasePool<>>> authored_binding_;
    uint64_t authored_base_=0;
    static bool authored_factory(void* owner,uint64_t session,const CallIdentity& player,
                                 const CallIdentity& actor,const CallIdentity& root) {
        auto& self=*static_cast<SequenceOwner*>(owner);
        return self.state_==1 && !self.retiring_ && self.binding_session_==session &&
            self.epoch_current(self.authored_base_) &&
            !std::memcmp(&player,&self.plans_[0].target,sizeof(player)) &&
            !std::memcmp(&actor,&self.plans_[1].target,sizeof(actor)) &&
            !std::memcmp(&root,&self.binding_asset_,sizeof(root));
    }
    uint32_t close_authored_binding() {
        if(!authored_binding_)return 0;
        const auto result=authored_binding_->close();
        if(result==e33_camera_binding::QueryResult::deferred)return 407;
        if(result!=e33_camera_binding::QueryResult::ok)return 1583;
        authored_binding_.reset();authored_base_=0;return 0;
    }
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
    bool protects(uint64_t token) const { return active() && (state_==2 || token==tokens_[0] || token==tokens_[1]
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
        || (authored_binding_ && authored_binding_->protects(token))
#endif
        ); }
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
    void authored_fault(SequenceOwnerPacket& p) {state_=p.state=2;p.error=1583;}
    // Research-gated command: 16 starts a single retained read; 17 releases
    // its private results. The session dispatcher must keep this SequenceOwner
    // alive after any uncertain result and never replay the request.
    void authored_command(uint64_t base,uint64_t session,StrongLeasePool<>& leases,
                          const TargetMenuStorage& menu,SequenceOwnerPacket& p) {
        const auto requested_state=p.state;
        p.state=state_;
        if(p.version!=1 || !p.owner || p.owner!=owner_ || p.reserved || p.error ||
           requested_state || (p.operation!=16 && p.operation!=17) || p.state!=1 || retiring_ ||
           !menu.menu.active() || menu.owner!=epoch_menu_owner_ || !epoch_current(base)) {
            p.error=p.operation==16 ? 1601 : 1581;return;
        }
        const auto* raw=reinterpret_cast<const uint8_t*>(&p.stop);
        if(p.operation==17) {
            if(!empty(raw,sizeof(p.stop)+sizeof(p.destroy))) {p.error=1581;return;}
            p.error=close_authored_binding();return;
        }
        SequenceAuthoredBindingPacket request{};std::memcpy(&request,raw,sizeof(request));
        if(authored_binding_ || request.magic!=0x41423345 || request.version!=1 || request.reserved ||
           request.outcome || request.count || request.zeros || !empty(request.objects,sizeof(request.objects)) ||
           !empty(raw+sizeof(request),sizeof(p.stop)+sizeof(p.destroy)-sizeof(request)) ||
           !(request.guid[0]||request.guid[1]||request.guid[2]||request.guid[3]) ||
           std::memcmp(&request.root,&binding_asset_,sizeof(request.root)) || session!=binding_session_) {
            p.error=1602;return;
        }
        const CallIdentity identities[]{request.query_function,request.target,request.resolver,request.root,request.source};
        const uint64_t proof_tokens[]{request.query_token,request.target_token,request.resolver_token,request.root_token,request.source_token};
        for(unsigned i=0;i<5;++i)
            if(!call_identity(base,identities[i]) || !leases.owns_object(session,proof_tokens[i],identities[i].address)) {
                p.error=1603;return;
            }
        if(!leases.owns_object(session,tokens_[0],plans_[0].target.address) ||
           !leases.owns_object(session,tokens_[1],plans_[1].target.address)) {p.error=1604;return;}
        e33_authored_binding::PortableInputs inputs{request.target,request.resolver,request.root,request.source,
            request.target_token,request.resolver_token,request.root_token,request.source_token};
        authored_base_=base;
        authored_binding_.emplace(base,session,leases,plans_[0].target,plans_[1].target,request.query_function,
            tokens_[0],tokens_[1],request.query_token,inputs,this,authored_factory);
        const auto result=authored_binding_->run(request.guid);
        if(result==e33_camera_binding::QueryResult::unknown || authored_binding_->uncertain()) {
            request.outcome=2;p.error=1583;state_=p.state=2;
        } else if(result==e33_camera_binding::QueryResult::ok || result==e33_camera_binding::QueryResult::empty) {
            uint32_t count=0;const auto* objects=authored_binding_->identities(count);
            if(!objects || count>8 || (result==e33_camera_binding::QueryResult::ok && !count) ||
               (result==e33_camera_binding::QueryResult::empty && count)) {
                request.outcome=2;p.error=1583;state_=p.state=2;
            } else {
                request.outcome=1;request.count=count;
                for(uint32_t i=0;i<count;++i)request.objects[i]=objects[i];
            }
        } else p.error=result==e33_camera_binding::QueryResult::deferred ? 407 :
            (authored_binding_->rejection_stage()==4 && authored_binding_->occurrence_failure() ?
             1700+authored_binding_->occurrence_failure() :
             authored_binding_->rejection_stage() ? 1610+authored_binding_->rejection_stage() : 1581);
        std::memcpy(&p.stop,&request,sizeof(request));
    }
#endif
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
    uint32_t current_state()const{return state_;}
    const e33_retired_world::Snapshot& captured_epoch()const{return epoch_;}
    uint64_t captured_menu_owner()const{return epoch_menu_owner_;}
    bool valid_retirement_request(const SequenceOwnerPacket& p)const {
        return p.version==1 && p.operation==7 && p.owner && p.owner==owner_ && !p.reserved && !p.error && !p.state &&
            empty(&p.stop,sizeof(p.stop)+sizeof(p.destroy));
    }
    template<class Pool> uint32_t retirement_authority(uint64_t base,uint64_t session,Pool& leases,uint64_t owner,
            e33_retired_world::Snapshot& out,CallIdentity& player) {
        out={};player={};
        if(!owner || owner!=owner_ || !leases.owns(session) || state_==2)return 1596;
        e33_retired_world::TargetOps proof{base};e33_retired_world::Snapshot a{},b{};
        if(!proof.observe(a) || !proof.observe(b))return 407;
        if(!e33_sequence_retirement::different_world(epoch_,a,b))return 1595;
        if(state_!=0 && state_!=1 && state_!=3)return 1596;
        if(state_!=3 && (!tokens_[0] || !tokens_[1] ||
           !leases.owns_retirement_storage(session,tokens_[0],plans_[0].target.address) ||
           !leases.owns_retirement_storage(session,tokens_[1],plans_[1].target.address)))return 1596;
        retiring_=true;out=epoch_;player=state_==3 ? CallIdentity{} : plans_[0].target;return 0;
    }
    template<class Pool> void retire(uint64_t base,uint64_t session,Pool& leases,SequenceOwnerPacket& p) {
        if(!valid_retirement_request(p)) {p.error=1471;p.state=state_;return;}
        p.state=state_;
        if(!state_ && !active())return;
        if(state_==2) {p.error=1473;return;}
        e33_retired_world::TargetOps proof{base};e33_retired_world::Snapshot a{},b{};
        e33_retired_world::Snapshot admitted{};CallIdentity player{};
        if(auto error=retirement_authority(base,session,leases,p.owner,admitted,player)){p.error=error;return;}
        // No dispatcher call is permitted below. These exact factory objects
        // remain game-owned members of the positively retired World. Releasing
        // SDK holds allows its ordinary GC; it does not destroy either object.
        const auto previous=state_;retiring_=true;state_=2;
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
        if(auto error=close_authored_binding()) {p.error=error;if(error==407)state_=previous;p.state=state_;return;}
#endif
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
        if(auto error=binding_query_.close()) {p.error=error;if(error==407)state_=previous;p.state=state_;return;}
#endif
#ifdef E33_SEQUENCE_CAMERA_SESSION
        if(auto error=camera_.retire(true)) {p.error=error;if(error==407)state_=previous;p.state=state_;return;}
#endif
        if(!proof.observe(a) || !proof.observe(b) || !e33_sequence_retirement::different_world(epoch_,a,b)) {
            p.error=1596;p.state=state_;return;
        }
#ifdef E33_SEQUENCE_ORIGIN_SESSION
        if(origin_owner_==this)origin_owner_=nullptr;
#endif
#ifdef E33_EMPTY_TITLE_SESSION
        if(empty_title_owner_==this)empty_title_owner_=nullptr;empty_title_={};
#endif
        state_=p.state=0;step_=2;
    }
#endif
    uint32_t close(uint64_t base) {
#ifdef E33_SEQUENCE_FLIGHT_SESSION
        flight_.cancel();
#endif
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        if(retiring_)return state_ ? 407 : 0;
        if(active() && epoch_.world.address && !epoch_current(base))return 407;
#endif
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
        if(auto error=close_authored_binding())return error;
#endif
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
            const auto error=
#ifdef E33_SEQUENCE_ORIGIN_SESSION
                step_==0 ? cleanup_stop(base,call) :
#endif
                reflected_call(base,call);
            if(error==201 && call.outcome==CallNotDispatched) { state_=1; return 407; }
            if(error || call.outcome!=CallDispatchReturned) return 1473;
            ++step_; state_=1;
        }
#ifdef E33_EMPTY_TITLE_SESSION
        if(empty_title_owner_==this) empty_title_owner_=nullptr;
        empty_title_={};
#endif
#ifdef E33_SEQUENCE_ORIGIN_SESSION
        if(origin_owner_==this) origin_owner_=nullptr;
#endif
        state_=0; return 0;
    }
    void command(uint64_t base,const TargetMenuStorage& menu,SequenceOwnerPacket& p,const CallPodValidation* pod=nullptr) {
#ifndef E33_SEQUENCE_FLIGHT_SESSION
        (void)pod;
#endif
        if(p.version!=1 || !p.owner || p.reserved || p.error || p.state || p.operation<1 || p.operation>
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
            15
#elif defined(E33_SEQUENCE_FLIGHT_SESSION)
            13
#elif defined(E33_SEQUENCE_ORIGIN_UPDATE_SESSION)
            9
#elif defined(E33_SEQUENCE_SEEK_SESSION)
            8
#elif defined(E33_SEQUENCE_ORIGIN_SESSION)
            6
#elif defined(E33_SEQUENCE_BINDING_QUERY_SESSION)
            5
#elif defined(E33_SEQUENCE_CAMERA_SESSION)
            4
#else
            3
#endif
            ) { p.error=1470; return; }
        p.state=state_;
#ifdef E33_SEQUENCE_FLIGHT_SESSION
        if(p.operation==10 || p.operation==11 || p.operation==12 || p.operation==13){
            if(state_!=1 || p.owner!=owner_ || !menu.menu.active() || menu.owner!=epoch_menu_owner_ ||
               std::memcmp(&menu.player,&origin_context_,sizeof(CallIdentity)) || !epoch_current(base)){p.error=1791;return;}
            if(p.operation==13){
                const auto* payload=reinterpret_cast<const uint8_t*>(&p.stop);uint32_t header[4]{};std::memcpy(header,payload,16);
                if(header[0]!=0x49533345 || header[1]!=1 || header[2] || header[3] || !empty(payload+16,sizeof(p.stop)+sizeof(p.destroy)-16)){p.error=1791;return;}
                double delta[3]{};flight_.drain_input(header[3],delta);
                std::memcpy(&p.stop,header,16);std::memcpy(reinterpret_cast<uint8_t*>(&p.stop)+16,delta,24);
            }else if(p.operation==12){
                p.error=flight_.bind(base,p.stop,p.destroy,plans_[0].target);
            }else if(p.operation==10){
                p.error=flight_.prepare(base,p.stop,p.destroy,plans_[0].target,pod);
                if(p.error==1793)state_=2;
            }else{
                const auto* payload=reinterpret_cast<const uint8_t*>(&p.stop);
                uint32_t header[4]{};std::memcpy(header,payload,16);
                if(header[0]!=0x46533345 || header[1]!=1 || header[2]>2 || header[3] ||
                   !empty(payload+16,sizeof(p.stop)+sizeof(p.destroy)-16)){p.error=1791;return;}
                if(header[2]==1)flight_.cancel();
                if(header[2]==2){p.error=flight_.restore_pose(base,pod);if(p.error==1793)state_=2;}
                header[3]=flight_.active()?1:0;std::memcpy(&p.stop,header,16);
                flight_.pose(reinterpret_cast<double*>(reinterpret_cast<uint8_t*>(&p.stop)+16));
            }
            p.state=state_;return;
        }
#endif
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        if(retiring_ && active() && p.operation!=3) {p.error=1595;return;}
#endif
#ifdef E33_SEQUENCE_ORIGIN_UPDATE_SESSION
        if(p.operation==9
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
           || p.operation==15
#endif
        ) {
            auto& query=p.stop;SequenceOriginPacket origin{};std::memcpy(&origin,&p.destroy,sizeof(origin));
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
            SequenceOriginTransformPacket transform{};std::memcpy(&transform,&p.destroy,sizeof(transform));
            const bool payload_ok=p.operation==15
                ? sequence_origin_transform_packet(transform) && empty(reinterpret_cast<const uint8_t*>(&p.destroy)+40,sizeof(p.destroy)-40)
                : sequence_origin_packet(origin) && empty(reinterpret_cast<const uint8_t*>(&p.destroy)+32,sizeof(p.destroy)-32);
#else
            const bool payload_ok=sequence_origin_packet(origin) && empty(reinterpret_cast<const uint8_t*>(&p.destroy)+32,sizeof(p.destroy)-32);
#endif
            const auto fn=call_identity(base,query.function);
            const auto fn_owner=fn ? local_read<uint64_t>(fn+32) : 0;
            if(state_!=1 || p.owner!=owner_ || !menu.menu.active() || menu.owner!=epoch_menu_owner_ ||
               std::memcmp(&menu.player,&origin_context_,sizeof(CallIdentity)) || !epoch_current(base) ||
               std::memcmp(&query.target,&plans_[0].target,sizeof(CallIdentity)) || validate_call_packet(query) ||
               query.parameter_size!=1 || query.allocation_extent!=1 || query.return_offset ||
               query.field_count!=1 || query.object_count || query.fields[0].kind!=CallBool ||
               query.fields[0].offset || query.fields[0].width!=1 || query.fields[0].dimension!=1 ||
               std::strcmp(query.fields[0].name,"ReturnValue") || !fn || !exact_name(base,fn+24,"IsPlaying") ||
               !call_is_class(base,fn_owner) || !exact_name(base,fn_owner+24,"MovieSceneSequencePlayer") ||
               !exact_name(base,local_read<uint64_t>(fn_owner+32)+24,"/Script/MovieScene") ||
               !payload_ok) {
                p.error=1591;return;
            }
            const auto error=reflected_call(base,query);
            if(error || query.outcome!=CallDispatchReturned) {
                if(query.outcome==CallNotDispatched){p.error=1591;return;}
                state_=2;p.error=1593;p.state=state_;return;
            }
            if(query.data[0] || !epoch_current(base)){p.error=1591;return;}
            state_=2;
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
            p.error=p.operation==15 ? origin_.update_transform(transform) : origin_.update(origin);
#else
            p.error=origin_.update(origin);
#endif
            if(p.error!=1593)state_=1;
            p.state=state_;return;
        }
#endif
#ifdef E33_SEQUENCE_SEEK_SESSION
        if(p.operation==8) {
            SequenceSeekPacket seek{};std::memcpy(&seek,&p.stop,sizeof(seek));
            const auto* payload=reinterpret_cast<const uint8_t*>(&p.stop);
            if(state_!=1 || p.owner!=owner_ || !menu.menu.active() || menu.owner!=epoch_menu_owner_ ||
               std::memcmp(&menu.player,&origin_context_,sizeof(CallIdentity)) || !epoch_current(base) ||
               !sequence_seek_request(seek) || !empty(payload+64,sizeof(p.stop)+sizeof(p.destroy)-64) ||
               !origin_.before_evaluation()) {p.error=1691;return;}
            state_=2;
            p.error=sequence_seek_execute(base,plans_[0].target,plans_[1].target,seek);
            if(seek.outcome!=CallOutcomeUnknown && epoch_current(base))state_=1;
            else {seek.outcome=CallOutcomeUnknown;p.error=1693;}
            std::memcpy(&p.stop,&seek,sizeof(seek));p.state=state_;return;
        }
#endif
#ifdef E33_SEQUENCE_ORIGIN_SESSION
        if(p.operation==6
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
           || p.operation==14
#endif
        ) {
            SequenceOriginPacket origin{};std::memcpy(&origin,&p.stop,sizeof(origin));
            const auto* payload=reinterpret_cast<const uint8_t*>(&p.stop);
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
            SequenceOriginTransformPacket transform{};std::memcpy(&transform,&p.stop,sizeof(transform));
            const bool payload_ok=p.operation==14
                ? sequence_origin_transform_packet(transform) && empty(payload+40,sizeof(p.stop)+sizeof(p.destroy)-40)
                : sequence_origin_packet(origin) && empty(payload+32,sizeof(p.stop)+sizeof(p.destroy)-32);
#else
            const bool payload_ok=sequence_origin_packet(origin) && empty(payload+32,sizeof(p.stop)+sizeof(p.destroy)-32);
#endif
            if(state_!=1 || p.owner!=owner_ || !menu.menu.active() ||
               std::memcmp(&menu.player,&origin_context_,sizeof(CallIdentity)) ||
               !call_identity(base,origin_context_) ||
               !call_identity(base,plans_[1].target) ||
               local_read<uint64_t>(origin_context_.address+32)!=local_read<uint64_t>(plans_[1].target.address+32) ||
               !payload_ok) {p.error=1591;return;}
            // A fault between the private-data write and verification must
            // quarantine the composite owner, including its strong leases.
            state_=2;
#ifdef E33_SEQUENCE_ORIGIN_TRANSFORM_SESSION
            p.error=p.operation==14 ? origin_.configure_transform(base,plans_[1].target,origin_context_,transform)
                                    : origin_.configure(base,plans_[1].target,origin_context_,origin);
#else
            p.error=origin_.configure(base,plans_[1].target,origin_context_,origin);
#endif
            if(p.error!=1593) state_=1;
            p.state=state_;return;
        }
#endif
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
        if(p.operation==5) {
            SequenceBindingQueryPacket query{};std::memcpy(&query,&p.stop,sizeof(query));
            const auto* payload=reinterpret_cast<const uint8_t*>(&p.stop);
            if(state_!=1 || p.owner!=owner_ || query.magic!=0x51423345 || query.version!=1 ||
               (query.profile!=1 && query.profile!=2) || query.reserved ||
               !empty(&query.completed,32) || !empty(payload+64,sizeof(p.stop)+sizeof(p.destroy)-64)) {p.error=1581;return;}
#ifdef E33_SEQUENCE_ORIGIN_SESSION
            if(!origin_.before_evaluation()) {p.error=1593;return;}
#endif
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
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        if(!capture_epoch(base,menu.player)) {p.error=1595;return;}
        epoch_menu_owner_=menu.owner;
        retiring_=false;
#endif
        owner_=p.owner; step_=0; state_=p.state=3;
#ifdef E33_SEQUENCE_ORIGIN_SESSION
        origin_=SequenceOriginOwner{};
        origin_context_={};
#endif
    }
    template<class Pool>
    uint32_t create(uint64_t base,uint64_t session,Pool& leases,const TargetMenuStorage& menu,
                    RetainedCallPacket& packet,const CallRetention* retention,const CallPodValidation* pod,
                    const CallEntryValidation* entry) {
        if(state_!=3 || !menu.menu.active()) return 1471;
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        if(retiring_ || !epoch_current(base) || !epoch_menu_owner_ || menu.owner!=epoch_menu_owner_) return 1595;
#endif
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
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        const auto level=local_read<uint64_t>(actor.address+32);
        if(level!=local_read<uint64_t>(menu.player.address+32) || !exact_class(base,level,"Level","/Script/Engine") ||
           !epoch_current(base)) return 1596;
#endif
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
#ifdef E33_SEQUENCE_ORIGIN_SESSION
        origin_context_=menu.player;
        origin_owner_=this;sequence_origin_play_preflight=&before_origin_play;
#endif
        state_=1; return 0;
    }
#ifdef E33_SEQUENCE_FLIGHT_SESSION
    void editor_tick(uint64_t base,const TargetMenuStorage& menu,const CallPodValidation* pod,bool input){
        if(state_!=1)return;
        if(state_!=1 || !menu.menu.active() || menu.owner!=epoch_menu_owner_ || !epoch_current(base) ||
           std::memcmp(&menu.player,&origin_context_,sizeof(CallIdentity))){flight_.cancel();return;}
        flight_.sample_input(input);
        if(!flight_.active())return;
        if(flight_.tick(base,pod)){flight_.cancel();state_=2;}
    }
    void editor_fault(){flight_.cancel();state_=2;}
#endif
};
