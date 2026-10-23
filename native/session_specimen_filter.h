#pragma once
#include <string_view>

// The controller needs only these persistent native specimens. Filtering by
// object name before chasing class dependencies avoids inspecting unrelated
// objects/classes appended while the process is still initializing.
// This is not authority for invocation; exact class/owner/schema follows.
inline bool session_specimen_candidate(std::string_view name) {
    return name == "Default__Actor" || name == "IsActorBeingDestroyed";
}
