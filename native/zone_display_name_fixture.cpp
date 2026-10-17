#include <cstdint>
#include <cstring>
template<class T> T local_read(uint64_t at) { T value{};std::memcpy(&value,reinterpret_cast<void*>(at),sizeof(value));return value; }
inline bool exact_name(uint64_t,uint64_t at,const char* expected) {
 if(local_read<uint32_t>(at+4))return false;
 const auto id=local_read<uint32_t>(at);
 const char* names[]={"None","Level_Mini_BoatGraveyard","MiniLevel_BladesGraveyard","Level.SpawnPoint.Entry"};
 return id<4 && std::strcmp(names[id],expected)==0;
}
#include "zone_display_name.h"
int main() {
 uint32_t name[2]={1,3};const auto at=reinterpret_cast<uint64_t>(name);
 if(!zone_display_name(0,at,"Level_Mini_BoatGraveyard_2"))return 1;
 if(zone_display_name(0,at,"Level_Mini_BoatGraveyard_1") || zone_display_name(0,at,"Level_Mini_BoatGraveyard") || zone_display_name(0,at,"Level_Mini_BoatGraveyard_02"))return 2;
 name[1]=2;if(!zone_display_name(0,at,"Level_Mini_BoatGraveyard_1"))return 3;
 name[0]=2;name[1]=0;if(!zone_display_name(0,at,"MiniLevel_BladesGraveyard") || zone_display_name(0,at,"MiniLevel_BladesGraveyard_0"))return 4;
 name[0]=3;name[1]=1;if(!zone_display_name(0,at,"Level.SpawnPoint.Entry_0"))return 5;
 name[0]=0;name[1]=0;if(!zone_display_name(0,at,"None"))return 6;
 return 0;
}
