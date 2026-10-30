#pragma once
#include "authored_binding_query_authority.h"
#include "authored_guid_membership.h"
#include "authored_portable_resolver.h"
#include "target_authored_sequence_occurrence.h"

// Concrete research adapter for Authority<CallIdentity>.  It joins the
// previously separate exact-build proofs; it is deliberately NOT a session
// command. An enclosing native owner must first retain all identities, keep
// this adapter alive, and supply an epoch/player ownership callback that is
// tied to its factory receipt. No wire-supplied sequence ID is accepted.
template<class Query,class Pool>
class TargetAuthoredBindingAuthorityOps {
    Query& query_;
    Pool& leases_;
    e33_authored_binding::PortableInputs inputs_;
    CallIdentity player_{},actor_{};
    uint64_t player_token_=0,actor_token_=0;
    void* owner_=nullptr;
    bool (*owner_proof_)(void*,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&)=nullptr;
    bool (*outputs_released_)(void*)=nullptr;
    e33_authored_binding::PortableResolver resolver_;
    // Proof owns two bounded snapshots: never allocate these on the game stack.
    e33_authored_occurrence::Proof<CallIdentity> occurrence_;
    uint32_t occurrence_failure_=0;
public:
    TargetAuthoredBindingAuthorityOps(Query& query,Pool& leases,
            const e33_authored_binding::PortableInputs& inputs,
            const CallIdentity& player,const CallIdentity& actor,
            uint64_t player_token,uint64_t actor_token,void* owner,
            bool (*owner_proof)(void*,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&),
            bool (*outputs_released)(void*))
        :query_(query),leases_(leases),inputs_(inputs),player_(player),actor_(actor),
         player_token_(player_token),actor_token_(actor_token),owner_(owner),
         owner_proof_(owner_proof),outputs_released_(outputs_released) {}
    TargetAuthoredBindingAuthorityOps(const TargetAuthoredBindingAuthorityOps&)=delete;
    TargetAuthoredBindingAuthorityOps& operator=(const TargetAuthoredBindingAuthorityOps&)=delete;
    bool context()const {return query_.context() && owner_ && owner_proof_ && outputs_released_;}
    bool same(const CallIdentity& a,const CallIdentity& b)const {return query_.same(a,b);}
    bool outputs_released()const {return context() && outputs_released_(owner_);}
    uint32_t occurrence_failure()const{return occurrence_failure_;}
    bool owned_player(uint64_t session,const CallIdentity& player,const CallIdentity& actor,const CallIdentity& root)const {
        if(!context() || !session || session!=query_.session || !same(player,player_) || !same(actor,actor_) ||
           !same(root,inputs_.root) || !query_.valid(player) || !query_.valid(actor) || !query_.valid(root) ||
           !leases_.owns_object(session,player_token_,player.address) ||
           !leases_.owns_object(session,actor_token_,actor.address) ||
           !leases_.owns_object(session,inputs_.root_token,root.address) ||
           !owner_proof_(owner_,session,player,actor,root))return false;
        // The caller's owner proof carries epoch and factory authority. These
        // observed associations are checked on both sides of the resolver.
        return local_read<uint64_t>(player.address+32)==actor.address &&
            local_read<uint64_t>(actor.address+720)==player.address &&
            local_read<uint64_t>(actor.address+728)==root.address && context();
    }
    bool unique_reachable_source(uint64_t session,const CallIdentity& root,const CallIdentity& source) {
        occurrence_failure_=0;
        if(session!=query_.session || !same(root,inputs_.root) || !same(source,inputs_.source) ||
           !leases_.owns_object(session,inputs_.root_token,root.address) ||
           !leases_.owns_object(session,inputs_.source_token,source.address)) {occurrence_failure_=22;return false;}
        TargetAuthoredOccurrenceReader<Query> reader{query_};
        const auto result=occurrence_.unique(reader,root,source);
        if(!result)occurrence_failure_=reader.failure ? reader.failure : 23;
        return result;
    }
    bool authored_binding(uint64_t session,const CallIdentity& source,const uint32_t (&guid)[4])const {
        return session==query_.session && same(source,inputs_.source) &&
            leases_.owns_object(session,inputs_.source_token,source.address) &&
            authored_guid_membership(query_,source,guid);
    }
    e33_camera_binding::QueryResult resolve(uint64_t session,const CallIdentity& root,
            const CallIdentity& source,const uint32_t (&guid)[4],e33_camera_binding::BindingValue& out) {
        if(session!=query_.session || !same(root,inputs_.root) || !same(source,inputs_.source))
            return e33_camera_binding::QueryResult::rejected;
        e33_authored_binding::PortableResolverOps<Pool> ops{query_.base,session,leases_};
        return resolver_.resolve(ops,inputs_,guid,out);
    }
    bool uncertain()const{return resolver_.uncertain();}
};
