#pragma once
namespace e33_owned_actor {
// Release-only proof for an actor already destroyed by the engine. A changed
// map/controller is never sufficient, nor does this authorize DestroyActor.
inline bool externally_retired(bool game_thread,bool exact_identity,bool held_lease,
        bool original_class,bool original_world,bool engine_retired) {
    return game_thread&&exact_identity&&held_lease&&original_class&&original_world&&engine_retired;
}
inline bool purged(bool game_thread,bool actor_absent,bool world_absent,bool owned_storage){
    return game_thread&&actor_absent&&world_absent&&owned_storage;
}
}
