#pragma once
#include "validated_engine_profile_call.h"
#include "mesh_profile.h"
namespace e33_story_resource_names {
constexpr uint32_t operation=240,rejected=3980,uncertain=3981;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity cdo{},function{};uint64_t cdo_lease=0,function_lease=0;
 uint32_t count=0,reserved=0;uint64_t package_name=0,asset_name=0;
 uint16_t path[1024]{};uint8_t tail[18840]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"SDK resource-name packet");
inline bool valid(const Packet&p){
 if(p.version!=3||(p.op!=operation&&p.op!=243)||p.error||p.state||!p.owner||!p.cdo_lease||!p.function_lease||p.reserved||p.package_name||p.asset_name||
    p.count<16||p.count>1024||!valid_text_units(p.path,p.count)||!e33_story_inworld::identity(p.cdo)||!e33_story_inworld::identity(p.function))return false;
 const char*prefix=p.op==243?"/Game/":"/Game/SDK/";for(unsigned i=0;prefix[i];++i)if(p.path[i]!=uint16_t(prefix[i]))return false;
 unsigned dot=0;
 for(unsigned i=0;i+1<p.count;++i){const auto c=p.path[i];
  if(c=='.'){if(dot)return false;dot=i;}
  else if(c!='/'&&c!='_'&&!(c>='0'&&c<='9')&&!(c>='A'&&c<='Z')&&!(c>='a'&&c<='z'))return false;
 }
 if(p.op==243){
  unsigned slash=0;for(unsigned i=0;i<dot;++i){if(p.path[i]=='/'){if(i&&p.path[i-1]=='/')return false;slash=i;}}
  const auto n=dot-slash-1, m=p.count-dot-2;
  if(!n||(m!=n&&m!=n+2))return false;
  for(unsigned i=0;i<n;++i)if(p.path[slash+1+i]!=p.path[dot+1+i])return false;
  if(m==n+2&&(p.path[dot+1+n]!='_'||p.path[dot+2+n]!='C'))return false;
 }
 if(!dot||dot+2>=p.count||p.path[dot-1]=='/'||p.path[dot+1]=='/')return false;
 for(unsigned i=p.count;i<1024;++i)if(p.path[i])return false;
 for(auto c:p.tail)if(c)return false;return true;
}
struct Dispatcher {
 bool unknown=false;
 template<class Pool>void run(uint64_t b,uint64_t session,Pool&pool,Packet&p){
  if(!valid(p)||unknown||!pool.owns_object(session,p.cdo_lease,p.cdo.address)||!pool.owns_object(session,p.function_lease,p.function.address)){
   p.error=unknown?uncertain:rejected;return;}
  const auto cdo=call_identity(b,p.cdo),function=call_identity(b,p.function);
  if(!cdo||!function||!e33_mesh::named(b,cdo,"Default__KismetStringLibrary","/Script/Engine")){p.error=rejected;return;}
  alignas(8)uint8_t arguments[24]{};
  e33_engine_profile_call::TargetOps call{b,function,cdo,mesh_functions[15],arguments};
  if(!call.context()||!call.exact_profile()||!call.recipient_derives()||!call.dispatch_entry()){p.error=rejected;return;}
  unsigned dot=0;while(dot<p.count&&p.path[dot]!='.')++dot;
  uint16_t package[1024]{};std::memcpy(package,p.path,dot*2);
  const TargetStringValue inputs[]={{reinterpret_cast<uint64_t>(package),int(dot+1),int(dot+1)},
   {reinterpret_cast<uint64_t>(p.path+dot+1),int(p.count-dot-1),int(p.count-dot-1)}};
  unknown=true;
  for(unsigned i=0;i<2;++i){std::memset(arguments,0,sizeof(arguments));std::memcpy(arguments,&inputs[i],16);call.dispatch_once();
   const auto value=local_read<uint64_t>(reinterpret_cast<uint64_t>(arguments)+16);
   if(!value){p.error=uncertain;return;}if(i)p.asset_name=value;else p.package_name=value;
  }
  unknown=false;p.state=1;
 }
};
}
