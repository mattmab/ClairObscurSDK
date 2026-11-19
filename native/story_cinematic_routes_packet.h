#pragma once
namespace e33_story_cinematics {
constexpr uint32_t operation=269,rejected=4380,uncertain=4381,count=16,max_routes=5;
#pragma pack(push,1)
struct Packet{uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[count]{};uint64_t leases[count]{};uint32_t mode=0,nkeys=0,keys[64][4]{};CallIdentity menu[2]{};uint32_t selected=0,choices=0,target=0,routed=0,vanilla=0,route_count=0;CallIdentity menu_direction{};uint8_t tail[20984-1512]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984);
inline unsigned active_count(const Packet&p){return 6+2*p.route_count;}
inline bool valid_bounds(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>4||p.nkeys>64||p.routed||p.vanilla||!p.route_count||p.route_count>max_routes)return false;
 for(auto v:p.tail)if(v)return false;
 const auto& direction=p.menu_direction;
 if((direction.index||direction.serial||direction.address)&&
    (p.mode!=3||direction.index<0||direction.serial<=0||!direction.address))return false;
 for(unsigned i=0;i<count;++i){const auto&id=p.ids[i];if(i<active_count(p)){
   if(id.index<0||id.serial<=0||!id.address||!p.leases[i])return false;
  }else if(id.index||id.serial||id.address||p.leases[i])return false;
 }
 for(unsigned i=0;i<64;++i){if(i<p.nkeys){if(p.keys[i][0]!=0xe33c5701U)return false;}else for(auto v:p.keys[i])if(v)return false;}
 if(p.mode==3){
  if(!p.choices||p.choices>32||p.selected>=p.choices||p.target>=p.choices)return false;
  for(const auto&id:p.menu)if(id.index<0||id.serial<=0||!id.address)return false;
 }else{
  for(const auto&id:p.menu)if(id.index||id.serial||id.address)return false;
  if(p.selected||p.choices||p.target)return false;
 }
 return true;
}
}
