#pragma once
#include "mesh_profile.h"
// Reuse exact existing SDK profiles without copying or changing their schemas.
namespace e33_component_transform {
inline const MeshFunction& set_relative=mesh_functions[31];
inline const MeshFunction& get_relative=mesh_functions[32];
}
