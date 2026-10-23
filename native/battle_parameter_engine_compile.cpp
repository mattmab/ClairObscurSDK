// Compile the private adapter with actual runtime types; never run this unit.
#include "runtime_session.cpp"
#include "strong_lease_pool.h"
#include "target_battle_parameter_frame.h"
#include "target_battle_parameter_owner.h"
#include "target_battle_parameter_source.h"
#include "target_battle_parameter_policy.h"
#include "target_battle_entry.h"
template struct e33_enemy_spawn::TargetBattleParameterOps<StrongLeasePool<>>;
template struct e33_enemy_spawn::TargetBattleParameterOwnerOps<StrongLeasePool<>>;
template struct e33_enemy_spawn::TargetBattleParameterPolicyOps<StrongLeasePool<>>;
template struct e33_enemy_spawn::TargetBattleEntryOps<StrongLeasePool<>>;
