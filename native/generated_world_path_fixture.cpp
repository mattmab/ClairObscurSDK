#include "asset_path_match.h"
#include <cassert>
#include <cstdio>
int main(){
    const char* package="/Game/Levels/Visages/Level_Visages_Main_V1/_Generated_/5SUTX1DFKM038D1G5VU2S4T1E";
    assert(generated_world_export_matches(package,"Level_Visages_Main_V1"));
    assert(!asset_basename_matches(package,"Level_Visages_Main_V1",false));
    assert(!asset_basename_matches(package,"Level_Visages_Main_V1_C",true));
    assert(!generated_world_export_matches(package,"Other"));
    assert(!generated_world_export_matches(package,"Level_Visages_Main_V1_C"));
    assert(!generated_world_export_matches("/Game/Levels/Map/_Generated_/ABC","Map"));
    assert(!generated_world_export_matches("/Game/Other/Map/_Generated_/5SUTX1DFKM038D1G5VU2S4T1E","Map"));
    assert(!generated_world_export_matches("/Game/Levels/Map/_Generated_/5SUTX1DFKM038D1G5VU2S4T1E/Extra","Map"));
    assert(!generated_world_export_matches(nullptr,"Map"));
    assert(!generated_world_export_matches(package,nullptr));
    std::puts("Generated World exact path guards passed; canonical matching unchanged");
}
