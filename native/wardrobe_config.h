#pragma once
#include "character_restore_profile.h"
#include <cmath>
namespace e33_wardrobe_config {
#pragma pack(push,1)
struct Profile {char paths[5][384]{};char character[96]{},template_character[96]{},template_component[96]{},anchor_component[96]{},anchor_tag[96]{},default_skin[96]{},default_face[96]{};double party_offset[3]{};};
#pragma pack(pop)
static_assert(sizeof(Profile)==2616);
inline bool valid_path(const char(&path)[384],bool cls){
 size_t length=0;for(;length<384&&path[length];++length){}if(!length||length==384)return false;for(size_t i=length;i<384;++i)if(path[i])return false;
 const char*dot=std::strchr(path,'.');if(!dot||std::strchr(dot+1,'.'))return false;
 const size_t package_length=size_t(dot-path),leaf_length=length-package_length-1;if(package_length>=256||!leaf_length||leaf_length>=96)return false;
 char package[256]{},leaf[96]{};std::memcpy(package,path,package_length);std::memcpy(leaf,dot+1,leaf_length);
 if(cls){if(leaf_length<3||std::strcmp(leaf+leaf_length-2,"_C"))return false;leaf[leaf_length-2]=0;leaf[leaf_length-1]=0;}
 return e33_character_graph::asset(package,leaf);
}
inline bool valid(const Profile&p){
 for(unsigned i=0;i<5;++i)if(!valid_path(p.paths[i],i<3))return false;
 if(!e33_character_graph::identifier(p.character)||!e33_character_graph::identifier(p.template_character)||!e33_character_graph::identifier(p.template_component)||!e33_character_graph::identifier(p.anchor_component)||!e33_character_graph::identifier(p.anchor_tag)||!e33_character_graph::identifier(p.default_skin)||!e33_character_graph::identifier(p.default_face))return false;
 for(auto x:p.party_offset)if(!std::isfinite(x)||std::abs(x)>1000)return false;return true;
}
inline const char* path(const Profile&p,unsigned i,const char*fallback){switch(i){case 2:return p.paths[0];case 6:return p.paths[1];case 7:return p.paths[2];case 30:return p.paths[3];case 32:return p.paths[4];default:return fallback;}}
}
