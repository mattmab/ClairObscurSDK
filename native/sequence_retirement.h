#pragma once
#include "retired_world_gate.h"
namespace e33_sequence_retirement {
// Only a positive different World in the same captured engine/viewport admits
// abandonment. Same-address serial changes, names and controller guesses do not.
inline bool different_world(const e33_retired_world::Snapshot& old,
                            const e33_retired_world::Snapshot& a,
                            const e33_retired_world::Snapshot& b) {
    using e33_retired_world::same;
    return old.world.address && old.world.serial>0 && a.world.address && a.world.serial>0 &&
        b.world.address && b.world.serial>0 && same(old.engine,a.engine) && same(old.viewport,a.viewport) &&
        same(a.engine,b.engine) && same(a.viewport,b.viewport) && same(a.world,b.world) &&
        old.world.address!=a.world.address && !same(old.world,a.world);
}
}
