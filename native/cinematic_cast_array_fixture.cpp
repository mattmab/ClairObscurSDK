#include "cinematic_cast_array.h"
#include <cassert>
#include <cstdio>
int main() {
    assert(cinematic_cast_array_limit("/Script/MovieScene","MovieScene","ObjectBindings","/Script/MovieScene","MovieSceneBinding")==4096);
    assert(cinematic_cast_array_limit("/Script/MovieScene","MovieScene","Possessables","/Script/MovieScene","MovieScenePossessable")==4096);
    assert(cinematic_cast_array_limit("/Script/MovieScene","MovieScene","Spawnables","/Script/MovieScene","MovieSceneSpawnable")==4096);
    assert(cinematic_cast_array_limit("/Game/Other","MovieScene","ObjectBindings","/Script/MovieScene","MovieSceneBinding")==256);
    assert(cinematic_cast_array_limit("/Script/MovieScene","MovieScene","ObjectBindings","/Game/Other","MovieSceneBinding")==256);
    assert(cinematic_cast_array_limit("/Script/MovieScene","Other","ObjectBindings","/Script/MovieScene","MovieSceneBinding")==256);
    assert(cinematic_cast_array_limit("/Script/MovieScene","MovieScene","Tracks","/Script/MovieScene","MovieSceneBinding")==256);
    assert(cinematic_cast_array_limit("/Script/MovieScene","MovieScene","ObjectBindings","/Script/MovieScene","MovieScenePossessable")==256);
    assert(cinematic_cast_array_limit(nullptr,"MovieScene","ObjectBindings","/Script/MovieScene","MovieSceneBinding")==256);
    std::puts("Cinematic cast array policy passed");
}
