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
    // No value here substitutes for identity/world checks performed by the caller.
}
