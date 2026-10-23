#pragma once
#include <cstring>
// World Partition packages use a generated cell ID while retaining their map's
// World export name. This admits that exact pattern only, never a class load.
inline bool generated_world_export_matches(const char* package,const char* asset){
    if(!package||!asset||std::strncmp(package,"/Game/Levels/",13))return false;
    const char* marker=std::strstr(package,"/_Generated_/");
    if(!marker||std::strstr(marker+1,"/_Generated_/"))return false;
    const char* parent=marker;
    while(parent>package&&parent[-1]!='/')--parent;
    const auto length=static_cast<size_t>(marker-parent);
    if(!length||std::strlen(asset)!=length||_strnicmp(parent,asset,length))return false;
    const char* cell=marker+13;
    if(std::strlen(cell)!=25)return false;
    for(const char* at=cell;*at;++at)
        if(!((*at>='A'&&*at<='Z')||(*at>='0'&&*at<='9')))return false;
    return true;
}
// FName identity permits case variation; retain exact generated-class suffix.
inline bool asset_basename_matches(const char* package,const char* asset,bool class_load){
    if(!package||!asset)return false;
    const auto tail=std::strrchr(package,'/');
    if(!tail||!tail[1])return false;
    const auto length=std::strlen(tail+1);
    return class_load ? (std::strlen(asset)==length+2&&!_strnicmp(tail+1,asset,length)&&!std::strcmp(asset+length,"_C"))
                      : !_stricmp(tail+1,asset);
}
