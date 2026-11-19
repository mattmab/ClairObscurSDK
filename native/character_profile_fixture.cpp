#include "character_restore_profile.h"
#include "wardrobe_config.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <initializer_list>
template<size_t N>void text(char(&out)[N],const char*value){assert(std::strlen(value)<N);std::memset(out,0,N);std::memcpy(out,value,std::strlen(value));}
int main(){
 using namespace e33_character_graph;
 Profile p;text(p.character,"TestScholar");text(p.graph_package,"/Game/SDK/Sample/Graph");text(p.graph_asset,"Graph");
 for(unsigned n:{1U,3U,9U}){
  p.count=n;std::memset(p.skills,0,sizeof(p.skills));
  for(unsigned i=0;i<n;++i){char id[32]{},path[96]{};sprintf_s(id,"Skill%u",i);sprintf_s(path,"/Game/SDK/Sample/Skill%u",i);text(p.skills[i].id,id);text(p.skills[i].package,path);text(p.skills[i].asset,id);p.skills[i].starter=i?0:1;p.skills[i].cost=i;}
  assert(valid(p));text(p.character,"TestGuardian");assert(valid(p));
  auto bad=p;bad.count=0;assert(!valid(bad));bad=p;bad.skills[0].starter=0;assert(!valid(bad));
 }
 auto bad=p;text(bad.skills[1].id,"Skill0");assert(!valid(bad));bad=p;bad.graph_package[255]='X';assert(!valid(bad));
 e33_wardrobe_config::Profile w;const char*paths[]={"/Game/SDK/Sample/Preview.Preview_C","/Game/SDK/Sample/Body.Body_C","/Game/SDK/Sample/FaceAnim.FaceAnim_C","/Game/SDK/Sample/Face.Face","/Game/SDK/Sample/Icon.Icon"};for(unsigned i=0;i<5;++i)text(w.paths[i],paths[i]);
 text(w.character,"TestScholar");text(w.template_character,"Template");text(w.template_component,"TemplateChild");text(w.anchor_component,"AnchorChild");text(w.anchor_tag,"Anchor");text(w.default_skin,"SkinTest");text(w.default_face,"FaceTest");w.party_offset[0]=55;assert(e33_wardrobe_config::valid(w));
 text(w.character,"TestGuardian");w.party_offset[0]=-80;w.party_offset[1]=30;assert(e33_wardrobe_config::valid(w));
 w.party_offset[0]=std::numeric_limits<double>::quiet_NaN();assert(!e33_wardrobe_config::valid(w));w.party_offset[0]=55;w.paths[0][383]='X';assert(!e33_wardrobe_config::valid(w));
 std::puts("Generic character graph and wardrobe profile checks passed");
}
