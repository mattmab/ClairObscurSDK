#pragma once
#include <array>
#include <cstdint>

namespace e33_action_clone {
// Research-only transaction policy. No command/handshake advertises this yet.
// A target adapter MUST prove the entire inherited source override inventory;
// SpawnObject defaults alone are not a source clone.
enum class Result { returned, not_dispatched, unknown };
enum class Kind { sequential, cinematic, battle };
struct Node {unsigned source;Kind kind;};
// Source slots: exact original root followed by all ten authored wrappers.
// Clone only changed nodes. The five campaign-tail references remain originals.
inline constexpr Node simon_nodes[]={{0,Kind::sequential},{1,Kind::cinematic},
    {2,Kind::battle},{3,Kind::cinematic},{4,Kind::battle},{5,Kind::cinematic}};
inline constexpr unsigned simon_wrapper_sources[]={1,2,3,4,5,6,7,8,9,10};
inline constexpr bool simon_wrapper_inline[]={false,true,false,true,false,true,true,true,true,true};
enum class HoldState { empty, uncertain, held, released };
template<class Identity> struct Hold {Identity identity{};uint64_t token=0;HoldState state=HoldState::empty;};

template<class Identity> class SimonCloneOwner {
    // Context, eleven source objects, six owned clones. No arbitrary graph size.
    std::array<Hold<Identity>,18> holds_{};
    bool attempted_=false,ready_=false,quarantined_=false;
    enum Execution { never, uncertain, running, retired } execution_=never;
    template<class Ops> bool accept(Ops& ops,unsigned slot,Result result) {
        auto& h=holds_[slot];
        if(result==Result::not_dispatched && !h.token && ops.null(h.identity)) {h.state=HoldState::empty;return false;}
        if(result!=Result::returned || !h.token || ops.null(h.identity)) {quarantined_=true;return false;}
        h.state=HoldState::held;return true;
    }
public:
    bool ready() const {return ready_;}
    bool quarantined() const {
        if(quarantined_ || execution_==uncertain) return true;
        for(const auto& h:holds_) if(h.state==HoldState::uncertain) return true;
        return false;
    }
    const Hold<Identity>& hold(unsigned slot) const {return holds_.at(slot);}
    template<class Ops> bool open(Ops& ops) {
        if(attempted_ || !ops.admit_complete_simon_profile()) return false;
        attempted_=true;
        for(unsigned slot=0;slot<12;++slot) {
            auto& h=holds_[slot];h.state=HoldState::uncertain;
            const auto result=slot ? ops.acquire_source(slot-1,h.identity,h.token) : ops.acquire_context(h.identity,h.token);
            if(!accept(ops,slot,result)) return false;
        }
        for(unsigned node=0;node<6;++node) {
            auto& h=holds_[12+node];h.state=HoldState::uncertain;
            // Output identity/token are published directly into owner storage
            // before construction/retention can fault. Root uses the owned
            // context; all changed children have the private root as Outer.
            const auto& outer=holds_[node ? 12 : 0].identity;
            if(!accept(ops,12+node,ops.construct_owned(simon_nodes[node],outer,h.identity,h.token))) return false;
            if(!ops.prove_owned(simon_nodes[node],holds_[1+simon_nodes[node].source].identity,outer,h.identity,h.token)) {
                quarantined_=true;return false;
            }
            // The target copies every audited source override, including
            // inherited flags, with native field-aware lifetime semantics.
            quarantined_=true;
            const auto copied=ops.copy_complete_profile(simon_nodes[node],holds_[1+simon_nodes[node].source].identity,h.identity);
            if(copied==Result::unknown) {quarantined_=true;return false;}
            quarantined_=false;
            if(copied!=Result::returned) return false;
        }
        // Install all ten wrappers in owned root storage. Both original wrapper
        // choices and five unchanged tail actions are retained exactly.
        quarantined_=true;
        const auto linked=ops.link_complete_simon_wrappers(holds_);
        if(linked==Result::unknown) {quarantined_=true;return false;}
        if(linked!=Result::returned) {quarantined_=false;return false;}
        if(!ops.verify_complete_clone_and_unchanged_sources(holds_)) return false;
        quarantined_=false;
        ready_=true;return true;
    }
    template<class Ops> bool execute(Ops& ops) {
        if(!ready_ || quarantined_ || execution_!=never || !ops.current_clone_context(holds_)) return false;
        execution_=uncertain; // Publish before dispatch; never blindly retry.
        const auto result=ops.dispatch_exact_owned_root(holds_[12].identity);
        if(result==Result::not_dispatched) {execution_=retired;return false;}
        if(result!=Result::returned) {quarantined_=true;return false;}
        execution_=running;return true;
    }
    template<class Ops> bool close(Ops& ops) {
        if(quarantined_ || execution_==uncertain) return false;
        if(execution_==running) {
            // Idle is insufficient. Ops requires exact original completion
            // callback identity or positive world-retirement proof.
            if(!ops.prove_owned_execution_retired(holds_[12].identity)) return false;
            execution_=retired;
        }
        ready_=false;
        for(unsigned n=18;n;--n) {
            auto& h=holds_[n-1];
            if(h.state==HoldState::empty || h.state==HoldState::released) continue;
            if(h.state!=HoldState::held) {quarantined_=true;return false;}
            h.state=HoldState::uncertain;
            const auto result=ops.release(h.identity,h.token);
            if(result==Result::not_dispatched) {h.state=HoldState::held;return false;}
            if(result!=Result::returned) {quarantined_=true;return false;}
            h.state=HoldState::released;
        }
        return true;
    }
};
}
