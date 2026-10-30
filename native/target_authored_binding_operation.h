#pragma once
#include "target_authored_binding_query.h"
#include "target_authored_binding_authority.h"

// Single-use, retained diagnostic operation for an already owned sequence.
// This is not a session command. The enclosing sequence owner must own every
// supplied proof token, keep this object alive across uncertain dispatches,
// and forbid destruction of the player/actor or proof pool until close() has
// acknowledged release. Neither a wire binding ID nor an arbitrary caller's
// claimed source occurrence is accepted as authority.
template<class ProofPool>
class TargetAuthoredBindingOperation {
    using Result=e33_camera_binding::QueryResult;
    using Query=TargetAuthoredBindingQuery<StrongLeasePool<8>>;
    StrongLeasePool<8> outputs_;
    Query query_;
    TargetAuthoredBindingAuthorityOps<Query,ProofPool> proof_;
    e33_authored_binding::Authority<CallIdentity> authority_;
    e33_camera_binding::BoundObjectFrame<CallIdentity> frame_;
    ProofPool& proofs_;
    e33_authored_binding::PortableInputs inputs_;
    uint64_t function_token_;
    void* factory_owner_;
    bool (*factory_proof_)(void*,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&);
    bool started_=false;
    uint32_t rejection_stage_=0;

    static bool same(const CallIdentity& a,const CallIdentity& b) {
        return !std::memcmp(&a,&b,sizeof(a));
    }
    static bool factory(void* owner,uint64_t session,const CallIdentity& player,
                        const CallIdentity& actor,const CallIdentity& root) {
        auto& self=*static_cast<TargetAuthoredBindingOperation*>(owner);
        return self.factory_owner_ && self.factory_proof_ &&
            self.proofs_.owns_object(session,self.function_token_,self.query_.function.address) &&
            self.query_.valid(self.query_.function) &&
            self.factory_proof_(self.factory_owner_,session,player,actor,root);
    }
    static bool released(void* owner) {
        return static_cast<TargetAuthoredBindingOperation*>(owner)->outputs_.active()==0;
    }
    static bool owns(void* owner,const CallIdentity& player,const CallIdentity& actor,const CallIdentity& root) {
        auto& self=*static_cast<TargetAuthoredBindingOperation*>(owner);
        return same(player,self.query_.player) && same(actor,self.query_.actor) && same(root,self.query_.asset) &&
            self.proof_.owned_player(self.query_.session,player,actor,root);
    }
    static bool approved(void* owner,const e33_camera_binding::BindingValue& binding) {
        auto& self=*static_cast<TargetAuthoredBindingOperation*>(owner);
        return self.authority_.matches(self.proof_,self.query_.session,self.query_.player,
                                       self.query_.actor,self.query_.asset,binding);
    }
public:
    TargetAuthoredBindingOperation(uint64_t base,uint64_t session,ProofPool& proofs,
            const CallIdentity& player,const CallIdentity& actor,const CallIdentity& function,
            uint64_t player_token,uint64_t actor_token,uint64_t function_token,
            const e33_authored_binding::PortableInputs& inputs,void* factory_owner,
            bool (*factory_proof)(void*,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&))
        :query_{base,session,player,actor,inputs.root,function,outputs_,this,owns,approved},
         proof_{query_,proofs,inputs,player,actor,player_token,actor_token,this,factory,released},
         proofs_(proofs),inputs_(inputs),function_token_(function_token),
         factory_owner_(factory_owner),factory_proof_(factory_proof) {}
    TargetAuthoredBindingOperation(const TargetAuthoredBindingOperation&)=delete;
    TargetAuthoredBindingOperation& operator=(const TargetAuthoredBindingOperation&)=delete;
    bool active()const{return started_;}
    bool uncertain()const{return authority_.uncertain() || proof_.uncertain() || frame_.quarantined();}
    uint32_t rejection_stage()const{return rejection_stage_;}
    uint32_t occurrence_failure()const{return proof_.occurrence_failure();}
    uint32_t output_count()const{return outputs_.active();}
    bool protects(uint64_t token)const {
        return started_ && token && (token==function_token_ || token==inputs_.target_token ||
            token==inputs_.function_token || token==inputs_.root_token || token==inputs_.source_token);
    }

    Result run(const uint32_t (&guid)[4]) {
        rejection_stage_=0;
        if(started_) {rejection_stage_=1;return Result::rejected;}
        if(!query_.session || !query_.context() || !factory_owner_ || !factory_proof_ ||
           !proofs_.owns_object(query_.session,function_token_,query_.function.address) ||
           !query_.valid(query_.function)) {rejection_stage_=1;return Result::rejected;}
        // Publish ownership before creating the output pool or issuing either
        // engine call; this object and its proof pool must survive every fault.
        started_=true;
        if(outputs_.begin(query_.session)!=StrongLeaseResult::Ok)return Result::unknown;
        if(!authority_.derive(proof_,query_.session,query_.player,query_.actor,
                              inputs_.root,inputs_.source,guid)) {
            rejection_stage_=1+authority_.rejection_stage();
            return uncertain() ? Result::unknown : Result::rejected;
        }
        const auto* binding=authority_.value();
        if(!binding)return Result::unknown;
        const auto result=frame_.query(query_,*binding);
        if(result==Result::rejected)rejection_stage_=7;
        return result;
    }
    // These borrowed views are available only while ownership and the exact
    // authored binding remain valid; the private output pool retains objects.
    const CallIdentity* identities(uint32_t& count) {
        count=0;const auto* binding=authority_.value();
        if(!started_ || uncertain() || !binding || !approved(this,*binding))return nullptr;
        const auto* objects=frame_.identities();const auto n=frame_.count();
        if(!objects || n!=outputs_.active())return nullptr;
        for(uint32_t i=0;i<n;++i)if(!query_.valid(objects[i]))return nullptr;
        if(!approved(this,*binding))return nullptr;
        count=n;return objects;
    }
    Result close() {
        if(!started_)return Result::ok;
        if(uncertain())return Result::unknown;
        if(outputs_.owns(query_.session)) {
            TargetStrongReferenceOps ops{query_.base,{}};
            const auto result=outputs_.close(ops,query_.session);
            if(result==StrongLeaseResult::Deferred || result==StrongLeaseResult::InvalidContext)return Result::deferred;
            if(result!=StrongLeaseResult::Ok)return Result::unknown;
        } else if(outputs_.active())return Result::unknown;
        if(!frame_.reset(query_) || !authority_.clear(proof_))return Result::deferred;
        started_=false;return Result::ok;
    }
};
