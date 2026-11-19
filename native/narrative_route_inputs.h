#pragma once
#include <cstddef>
#include <cstdint>
namespace e33_narrative_routes {
// Named Blueprint dispatch is shared by FName, while transform hooks retain
// each exact UFunction separately. One owner retains/releases each name once.
template<std::size_t N,class NameOf>
bool unique_inputs(const unsigned(&inputs)[N],unsigned count,unsigned(&selected)[N],unsigned&used,NameOf name_of){
 used=0;if(count>N)return false;
 uint64_t names[N]{};
 for(unsigned i=0;i<count;++i){
  const auto name=name_of(inputs[i]);if(!name){used=0;return false;}
  bool found=false;for(unsigned j=0;j<used;++j)if(names[j]==name){found=true;break;}
  if(!found){names[used]=name;selected[used++]=inputs[i];}
 }
 return true;
}
}
