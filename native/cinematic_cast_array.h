#pragma once
#include <cstring>

// Larger stored prefixes are confined to MovieScene's three cast declarations.
// Other reflected arrays retain their ordinary observation bound.
inline int cinematic_cast_array_limit(const char* owner_package,const char* owner,
                                      const char* field,const char* inner_package,const char* inner) {
    if(!owner_package||!owner||!field||!inner_package||!inner ||
       std::strcmp(owner_package,"/Script/MovieScene")||std::strcmp(owner,"MovieScene")||
       std::strcmp(inner_package,"/Script/MovieScene"))return 256;
    return ((!std::strcmp(field,"Spawnables")&&!std::strcmp(inner,"MovieSceneSpawnable")) ||
            (!std::strcmp(field,"Possessables")&&!std::strcmp(inner,"MovieScenePossessable")) ||
            (!std::strcmp(field,"ObjectBindings")&&!std::strcmp(inner,"MovieSceneBinding"))) ? 4096 : 256;
}
