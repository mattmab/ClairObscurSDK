#pragma once
#include <cstdint>
#include <cstring>
namespace e33_character_graph {
struct Skill {char id[96]{},package[256]{},asset[96]{};uint32_t cost=0,starter=0;};
struct Profile {char character[96]{},graph_package[256]{},graph_asset[96]{};uint32_t count=0;Skill skills[9]{};};
static_assert(sizeof(Profile)==4556);
template<size_t N>bool identifier(const char(&s)[N]){size_t i=0;for(;i<N&&s[i];++i){auto c=s[i];if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'))return false;}if(!i||i==N)return false;for(;i<N;++i)if(s[i])return false;return true;}
inline bool asset(const char(&package)[256],const char(&leaf)[96]){
 if(!identifier(leaf)||std::memcmp(package,"/Game/",6))return false;
 size_t i=6,start=6;for(;i<256&&package[i];++i){auto c=package[i];if(c=='/'){if(i==start)return false;start=i+1;}else if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'))return false;}
 if(i==256||start==i||std::strcmp(package+start,leaf))return false;for(;i<256;++i)if(package[i])return false;return true;
}
inline bool valid(const Profile&p){
 if(!identifier(p.character)||!asset(p.graph_package,p.graph_asset)||!p.count||p.count>9)return false;
 for(unsigned i=0;i<9;++i){const auto&s=p.skills[i];if(i>=p.count){const Skill empty{};if(std::memcmp(&s,&empty,sizeof(s)))return false;continue;}
  if(!identifier(s.id)||!asset(s.package,s.asset)||s.cost>99999||s.starter!=(i?0U:1U))return false;
  for(unsigned j=0;j<i;++j)if(!std::strcmp(s.id,p.skills[j].id)||!std::strcmp(s.package,p.skills[j].package))return false;
 }return true;
}
}
