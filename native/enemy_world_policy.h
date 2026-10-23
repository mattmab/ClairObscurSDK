#pragma once
namespace e33_enemy_spawn {
// Context/identity/schema validation remains in Owner::current. This policy
// only selects which already validated worlds may use each transaction path.
inline bool world_path_allowed(bool qa_world, bool prepared_owner, bool prepare_or_read_only) {
    return qa_world || prepared_owner || prepare_or_read_only;
}
}
