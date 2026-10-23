#include "asset_path_match.h"
#include <cstdio>
int main(){
    struct Example{const char* package;const char* asset;bool class_load;bool expected;};
    const Example examples[]={
        {"/Game/Test/BP_Test","BP_Test_C",true,true},
        {"/Game/Test/BP_Test_ALPHA","BP_Test_Alpha_C",true,true},
        {"/Game/Test/BP_Test_Alpha","bp_test_alpha_C",true,true},
        {"/Game/Test/BP_Test","Other_C",true,false},
        {"/Game/Test/BP_Test","BP_Test_c",true,false},
        {"/Game/Test/BP_Test","BP_Test_C_Extra",true,false},
        {"/Game/Test/","_C",true,false},
        {nullptr,"BP_Test_C",true,false},
        {"/Game/Test/BP_Test",nullptr,true,false},
        {"/Game/Test/TestMesh","testmesh",false,true},
        {"/Game/Test/TestMesh","OtherMesh",false,false}};
    for(const auto& e:examples)if(asset_basename_matches(e.package,e.asset,e.class_load)!=e.expected)return 1;
    std::puts("11 asset basename validation cases passed");return 0;
}
