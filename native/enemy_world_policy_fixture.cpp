#include "enemy_world_policy.h"
#include <cassert>
int main() {
    using e33_enemy_spawn::world_path_allowed;
    // QA retains legacy behavior. Ordinary-map unprepared spawning stays blocked.
    assert(world_path_allowed(true,false,false));
    assert(!world_path_allowed(false,false,false));
    // Read-only pose query and staged preparation may validate current-world context.
    assert(world_path_allowed(false,false,true));
    assert(world_path_allowed(false,true,false));
    assert(world_path_allowed(false,true,true));
    assert(!e33_enemy_spawn::timeline_world_allowed(false,false));
    assert(e33_enemy_spawn::timeline_world_allowed(true,false));
    assert(e33_enemy_spawn::timeline_world_allowed(false,true));
    assert(e33_enemy_spawn::timeline_world_allowed(true,true));
#if defined(E33_TIMELINE_ACTOR_POOL_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 226
    static_assert(e33_enemy_spawn::timeline_current_world_enabled);
#else
    static_assert(!e33_enemy_spawn::timeline_current_world_enabled);
#endif
    // No value here substitutes for identity/world checks performed by the caller.
}
