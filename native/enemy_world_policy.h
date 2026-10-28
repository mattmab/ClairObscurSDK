#pragma once
namespace e33_enemy_spawn {
// Context/identity/schema validation remains in Owner::current. This policy
// only selects which already validated worlds may use each transaction path.
inline bool world_path_allowed(bool qa_world, bool prepared_owner, bool prepare_or_read_only) {
    return qa_world || prepared_owner || prepare_or_read_only;
}
inline bool timeline_world_allowed(bool qa_world, bool current_world_capability) {
    return qa_world || current_world_capability;
}
#if defined(E33_TIMELINE_ACTOR_POOL_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 226
constexpr bool timeline_current_world_enabled=true;
#else
constexpr bool timeline_current_world_enabled=false;
#endif
}
