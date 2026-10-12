#pragma once
#include "target_bound_object_query.h"
#include "authored_camera_spawn.h"
#include "binding_query_batch.h"
#include "target_spawn_register_membership.h"

#pragma pack(push,1)
struct SequenceBindingQueryPacket {
    uint32_t magic,version,profile,reserved;
    CallIdentity function;
    uint32_t completed,matched,private_active,private_peak,outcome,zeros[3];
};
#pragma pack(pop)
static_assert(sizeof(SequenceBindingQueryPacket)==64);

class SequenceBindingQueryOwner {
    using Result=e33_camera_binding::QueryResult;
    using Profile=e33_camera_binding::Profile;
    using Guid=e33_camera_binding::Guid;
    using Query=TargetBoundObjectQuery<StrongLeasePool<8>>;
    // Four immutable context/function holders + five authored cameras. Transient
    // return array elements have an independent eight-holder hard bound.
    StrongLeasePool<9> proofs_;
    StrongLeasePool<8> outputs_;
    e33_camera_binding::BindingQueryBatch<CallIdentity> batch_;
    uint64_t tokens_[4]{};
    CallIdentity cameras_[5]{};
    Guid camera_bindings_[5]{};
    uint64_t camera_tokens_[5]{};
    uint32_t cameras_count_=0,peak_=0;
    bool started_=false,acquiring_=false;
    Query query_{0,0,{},{},{},{},Profile::none,outputs_,this,owns,asset_profile,binding_profile};
    static bool same(const CallIdentity& a,const CallIdentity& b) {return !std::memcmp(&a,&b,sizeof(a));}
    static bool owns(void* instance,const CallIdentity& player,const CallIdentity& actor,const CallIdentity& asset) {
        auto& self=*static_cast<SequenceBindingQueryOwner*>(instance);
        return same(player,self.query_.player) && same(actor,self.query_.actor) && same(asset,self.query_.asset) &&
            self.proofs_.owns_object(self.query_.session,self.tokens_[0],player.address) &&
            self.proofs_.owns_object(self.query_.session,self.tokens_[1],actor.address) &&
            self.proofs_.owns_object(self.query_.session,self.tokens_[2],asset.address) &&
            self.proofs_.owns_object(self.query_.session,self.tokens_[3],self.query_.function.address);
    }
    static bool asset_profile(uint64_t base,Profile profile,const CallIdentity& id) {
        if(!call_identity(base,id))return false;
        const char* name=profile==Profile::locomotive ? "CS_GPE_MonolithInterior_Locomotive_MonocoToLumiere" :
            profile==Profile::scavenger ? "CS_OrangeForest_ScavengerIntro" : "";
        const char* package=profile==Profile::locomotive ? "/Game/Cinematics/MonolithInterior/Locomotive/CS_GPE_MonolithInterior_Locomotive_MonocoToLumiere" :
            "/Game/Cinematics/OrangeForest/CS_OrangeForest_ScavengerIntro";
        auto outer=call_capture(base,local_read<uint64_t>(id.address+32));
        return *name && outer.address && call_identity(base,outer) && exact_name(base,id.address+24,name) &&
            exact_name(base,outer.address+24,package);
    }
    static bool binding_profile(const Query& query,const Guid& guid) {
        CallIdentity object_template{};
        return authored_camera_spawn(query,guid,object_template);
    }
    void account() {const auto current=private_active();if(current>peak_)peak_=current;}
    bool hold(CallIdentity& id,uint64_t& token) {
        TargetStrongReferenceOps ops{query_.base,id};acquiring_=true;
        const auto result=proofs_.acquire(ops,query_.session,id.address,token);account();
        if(result!=StrongLeaseResult::Ok || !stabilize_retained_identity(ops,id))return false;
        acquiring_=false;return true;
    }
    static Result release_result(StrongLeaseResult result) {
        return result==StrongLeaseResult::Ok ? Result::ok :
            result==StrongLeaseResult::Deferred || result==StrongLeaseResult::InvalidContext ? Result::deferred : Result::unknown;
    }
public:
    bool active()const{return started_;}
    bool uncertain()const{return acquiring_ || batch_.uncertain();}
    uint32_t private_active()const{return proofs_.active()+outputs_.active();}
    uint32_t private_peak()const{return peak_;}
    bool context()const{return query_.context();}
    Query& query_ops(){return query_;}
    bool prepare_outputs(){return outputs_.begin(query_.session)==StrongLeaseResult::Ok;}
    Result release_outputs() {
        account();if(!outputs_.owns(query_.session))return outputs_.active() ? Result::unknown : Result::ok;
        TargetStrongReferenceOps ops{query_.base,{}};return release_result(outputs_.close(ops,query_.session));
    }
    Result release_proofs() {
        account();if(!proofs_.owns(query_.session))return proofs_.active() ? Result::unknown : Result::ok;
        TargetStrongReferenceOps ops{query_.base,{}};return release_result(proofs_.close(ops,query_.session));
    }
    e33_camera_binding::AdoptionResult empty_binding(const Guid& guid) {
        TargetSpawnRegisterMembership<Query> membership{query_,guid};
        e33_camera_binding::WeakIdentity observed{};
        return e33_camera_binding::spawn_register_lookup(membership,guid,observed)==e33_camera_binding::MembershipResult::empty ?
            e33_camera_binding::AdoptionResult::ok : e33_camera_binding::AdoptionResult::rejected;
    }
    e33_camera_binding::AdoptionResult adopt(const Guid& guid,const CallIdentity& candidate) {
        using Adoption=e33_camera_binding::AdoptionResult;
        CallIdentity object_template{};
        if(cameras_count_>=5 || !query_.valid(candidate) || !authored_camera_spawn(query_,guid,object_template) ||
           candidate.address==object_template.address || !query_.named(local_read<uint64_t>(candidate.address+16),"CineCameraActor","/Script/CinematicCamera"))return Adoption::rejected;
        for(uint32_t i=0;i<cameras_count_;++i)if(same(cameras_[i],candidate))return Adoption::rejected;
        TargetSpawnRegisterMembership<Query> membership{query_,guid};
        if(!e33_camera_binding::spawn_register_member(membership,guid,candidate))return Adoption::rejected;
        cameras_[cameras_count_]=candidate;
        if(!hold(cameras_[cameras_count_],camera_tokens_[cameras_count_]))return Adoption::unknown;
        // Retention may enter the engine. Publish historical proof only after
        // the exact membership and full identity have been revalidated.
        if(!e33_camera_binding::spawn_register_member(membership,guid,cameras_[cameras_count_]))return Adoption::unknown;
        camera_bindings_[cameras_count_]=guid;
        ++cameras_count_;return Adoption::ok;
    }
    uint32_t close() {
        if(!started_)return 0;
        if(uncertain())return 1583;
        const auto result=batch_.close(*this);
        if(result==Result::deferred)return 407;
        if(result!=Result::ok)return 1583;
        started_=false;tokens_[0]=tokens_[1]=tokens_[2]=tokens_[3]=0;cameras_count_=0;
        for(unsigned i=0;i<5;++i) {cameras_[i]={};camera_bindings_[i]={};camera_tokens_[i]=0;}
        return 0;
    }
    void report(SequenceBindingQueryPacket& p) {
        account();p.completed=batch_.completed();p.matched=batch_.matched();p.private_active=private_active();
        p.private_peak=peak_;p.outcome=uncertain() ? 2u : batch_.outcome();
    }
    uint32_t run(uint64_t base,uint64_t session,const CallIdentity& player,const CallIdentity& actor,
                 const CallIdentity& asset,SequenceBindingQueryPacket& packet) {
        const auto profile=static_cast<Profile>(packet.profile);
        if(started_) {report(packet);return uncertain() ? 1583 : 1581;} // One query per owner; no hidden redispatch.
        query_.base=base;query_.session=session;query_.player=player;query_.actor=actor;query_.asset=asset;
        query_.function=packet.function;query_.profile=profile;
        if(!session || !context() || !query_.valid(player) || !query_.valid(actor) || !query_.valid(asset) ||
           !query_.valid(packet.function) || !asset_profile(base,profile,asset))return 1581;
        started_=true;peak_=0;
        if(proofs_.begin(session)!=StrongLeaseResult::Ok || !prepare_outputs() || !batch_.begin(profile))return 1583;
        if(!hold(query_.player,tokens_[0]) || !hold(query_.actor,tokens_[1]) || !hold(query_.asset,tokens_[2]) ||
           !hold(query_.function,tokens_[3])) {report(packet);return 1583;}
        const auto result=batch_.run(*this);report(packet);
        return result==Result::ok || result==Result::empty ? 0 : result==Result::deferred ? 407 : result==Result::unknown ? 1583 : 1581;
    }
};
