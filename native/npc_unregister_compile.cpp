// Compile the real target bridge against the unchanged full runtime and lease
// pool. This translation unit is never linked, loaded, injected or executed.
#include "runtime_session.cpp"
#include "npc_original_unregister.h"
#include "npc_original_construction.h"
#include "npc_original_lifecycle_bridge.h"
#include "npc_clea_assembly_observation.h"
#include "npc_real_renoir_assembly_observation.h"
#include "npc_curator_owned_interaction.h"
#include "npc_dialogue_local_references.h"
#include "npc_dialogue_instance_references.h"
#include "npc_dialogue_native_references.h"
#include "npc_dialogue_isolation_contract.h"
#include "npc_curator_source_contract.h"
#include "npc_curator_assembly_observation.h"
#include "npc_current_context_guard.h"
#include "npc_listener_observation.h"
#include "npc_quest_listener_observation.h"
#include "npc_condition_graph_observation.h"
#include "npc_francois_assembly_observation.h"
#include "npc_clea_owner.h"
namespace e33_npc_presentation {
struct CompileOnlyConditionVisitor {bool operator()(CallIdentity){return false;}};
template struct FrancoisConditionGraphOps<CompileOnlyConditionVisitor>;
template bool visit_francois_condition_roots<CompileOnlyConditionVisitor>(
    uint64_t,CallIdentity,const CallIdentity*,size_t,CompileOnlyConditionVisitor&);
struct CompileOnlyIdleGuard {bool operator()(){return false;}};
struct CompileOnlyDialogueIsolationGuard {
    bool current_context(){return false;}
    bool battle_quiescent(){return false;}
    bool original_dialogue_isolation_contract(CallIdentity,CallIdentity,CallIdentity){return false;}
};
template struct CuratorOwnedInteractionOps<StrongLeasePool<>,CompileOnlyDialogueIsolationGuard>;
struct CompileOnlyConstructionGuard {
    bool current_context(){return false;}
    bool battle_quiescent(){return false;}
    bool verify_original_assembly_and_identity(CallIdentity,const uint32_t*){return false;}
    bool verify_original_endplay_and_all_registrations_absent(CallIdentity){return false;}
};
template struct OriginalConstructionOps<StrongLeasePool<>,CompileOnlyConstructionGuard>;
template struct OriginalLifecycleOps<StrongLeasePool<>,CompileOnlyConstructionGuard>;
template UnregisterResult unregister_original<StrongLeasePool<>,CompileOnlyIdleGuard>(
    uint64_t,const UnregisterContext&,InteractionRegistry,StrongLeasePool<>&,CompileOnlyIdleGuard&,UnregisterJournal&);
// Force compile of both complete callback paths, without executing either.
void compile_npc_lifecycle_paths(Lifecycle& lifecycle,
        OriginalLifecycleOps<StrongLeasePool<>,CompileOnlyConstructionGuard>& ops){
    (void)lifecycle.stage(ops);
    (void)lifecycle.retire(ops);
}
void compile_clea_owner_paths(CleaOwner& owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,
        const ConstructionSource& source,const RetirementBindings& bindings,CallIdentity gi,CallIdentity condition_template){
    (void)owner.stage(base,session,pool,source,bindings,gi,condition_template);
    CallIdentity queries[10]{};
    (void)owner.place_preview_grounded(base,session,pool,queries);
    (void)owner.stage(base,session,pool,source,bindings,gi,condition_template,queries);
    uint64_t instance_name=0;
    (void)owner.owned_parameter_instance_name(base,session,pool,source.controller,instance_name);
    ResearchService service;
    (void)service.owned_parameter_instance_name(base,session,pool,1,source.controller,instance_name);
    CallIdentity arena_query[4]{};
    (void)owner.bind_preview_arena(base,session,pool,arena_query);
    (void)owner.note_entry_dispatch(base,session,pool,source.controller,source.controller,source.controller);
    owner.poll_entry(base);
    (void)owner.entry_phase();
    CallIdentity collision[4]{},overlap[11]{};uint32_t overlaps=0;
    (void)owner.enable_solid_collision(base,session,pool,collision);(void)owner.observe_overlap(base,session,pool,overlap,overlaps);
    double distance[7]{};(void)owner.observe_proximity(base,session,pool,queries,distance);
    (void)owner.close(base,session,pool);
}
}
