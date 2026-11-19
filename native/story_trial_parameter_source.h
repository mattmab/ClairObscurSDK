#pragma once
#if defined(E33_RUNTIME_CINEMATIC_VERSION) && E33_RUNTIME_CINEMATIC_VERSION>=311
#include "story_trial_data_registry.h"
#endif
namespace e33_enemy_spawn {
inline uint32_t story_trial_parameter_offset(uint64_t base,const CallIdentity&root,const CallIdentity&source,uint64_t expected_type=0){
#if defined(E33_RUNTIME_CINEMATIC_VERSION) && E33_RUNTIME_CINEMATIC_VERSION>=311
 return e33_story_trial_data::registration.offset(base,root,source,expected_type);
#else
 (void)base;(void)root;(void)source;(void)expected_type;return 0;
#endif
}
}
