#pragma once
#include "bound_object_frame.h"
#include "bound_camera_proof.h"

namespace e33_camera_binding {
enum class AdoptionResult {ok,rejected,unknown};
inline Guid profile_guid(Profile profile,uint32_t index) {
    constexpr Guid values[]{
        {{3988227725u,1180247986u,2957613748u,2506576614u}},
        {{3323003479u,1294590874u,1110749852u,1552315500u}},
        {{2344242829u,1133825144u,963959480u,2788480762u}},
        {{101576481u,1074155408u,1436868279u,3861576507u}},
        {{3868951513u,1230066568u,4000387518u,2702779930u}}};
    return profile==Profile::locomotive && index==0 ? values[4] :
        profile==Profile::scavenger && index<5 ? values[index] : Guid{};
}
// Durable batch: no callback or allocated return frame lives on a request stack.
// A returned array is freed before result publication; output holders survive
// deferred release. Unknown dispatch/acquisition never retries or guesses free.
template<class Identity> class BindingQueryBatch {
    BoundObjectFrame<Identity> frame_;
    Profile profile_=Profile::none;
    uint32_t completed_=0,matched_=0,outcome_=0;
    enum State {idle,querying,adopting,releasing,done,rejected,unknown} state_=idle;
    bool reject_after_release_=false;
public:
    uint32_t completed()const{return completed_;}
    uint32_t matched()const{return matched_;}
    uint32_t outcome()const{return outcome_;}
    bool uncertain()const{return state_==adopting || state_==unknown || frame_.quarantined();}
    bool begin(Profile profile) {
        if(state_!=idle || (profile!=Profile::locomotive && profile!=Profile::scavenger))return false;
        profile_=profile;state_=querying;return true;
    }
    template<class Ops> QueryResult run(Ops& ops) {
        if(uncertain()) {outcome_=2;return QueryResult::unknown;}
        if(state_==done)return QueryResult::ok;
        if(state_==rejected || state_==idle)return QueryResult::rejected;
        const uint32_t limit=profile_==Profile::locomotive ? 1u : 5u;
        while(completed_<limit || state_==releasing) {
            if(!ops.context())return QueryResult::deferred;
            if(state_==querying) {
                const auto guid=profile_guid(profile_,completed_);
                BindingValue input{};std::memcpy(input.guid,guid.words,16);input.resolve_parent_index=-1;
                auto& query=ops.query_ops();
                const auto result=frame_.query(query,input);
                if(result==QueryResult::unknown) {state_=unknown;outcome_=2;return result;}
                if(result==QueryResult::deferred)return result;
                if(result==QueryResult::rejected) {state_=rejected;return result;}
                outcome_=1;
                if(frame_.count()>1)reject_after_release_=true;
                else if(!frame_.count()) {
                    state_=adopting;
                    const auto empty=ops.empty_binding(guid);
                    if(empty==AdoptionResult::unknown) {state_=unknown;outcome_=2;return QueryResult::unknown;}
                    if(empty==AdoptionResult::rejected)reject_after_release_=true;
                }
                else if(frame_.count()==1) {
                    state_=adopting;
                    const auto adoption=ops.adopt(guid,frame_.identities()[0]);
                    if(adoption==AdoptionResult::unknown) {state_=unknown;outcome_=2;return QueryResult::unknown;}
                    if(adoption==AdoptionResult::rejected)reject_after_release_=true;
                    else ++matched_;
                }
                ++completed_;state_=releasing;
            }
            if(state_==releasing) {
                const auto release=ops.release_outputs();
                if(release!=QueryResult::ok) {
                    if(release!=QueryResult::deferred) {state_=unknown;outcome_=2;}
                    return release;
                }
                if(!frame_.reset(ops.query_ops())) {state_=unknown;outcome_=2;return QueryResult::unknown;}
                if(reject_after_release_) {state_=rejected;return QueryResult::rejected;}
                if(completed_==limit) {state_=done;return QueryResult::ok;}
                if(!ops.prepare_outputs()) {state_=unknown;outcome_=2;return QueryResult::unknown;}
                state_=querying;
            }
        }
        state_=done;return QueryResult::ok;
    }
    template<class Ops> QueryResult close(Ops& ops) {
        if(uncertain()) {outcome_=2;return QueryResult::unknown;}
        if(!ops.context())return QueryResult::deferred;
        auto release=ops.release_outputs();
        if(release!=QueryResult::ok) {if(release!=QueryResult::deferred){state_=unknown;outcome_=2;}return release;}
        if(!frame_.reset(ops.query_ops())) {state_=unknown;outcome_=2;return QueryResult::unknown;}
        release=ops.release_proofs();
        if(release!=QueryResult::ok) {if(release!=QueryResult::deferred){state_=unknown;outcome_=2;}return release;}
        *this={};return QueryResult::ok;
    }
};
}
