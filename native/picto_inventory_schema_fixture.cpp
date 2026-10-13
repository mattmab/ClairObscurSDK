// Test the production schema predicates against a bounded synthetic field chain.
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <unordered_map>
static std::unordered_map<uint64_t,std::string> names;
template<class T> T local_read(uint64_t at) { T v{};std::memcpy(&v,reinterpret_cast<void*>(at),sizeof(v));return v; }
static bool exact_name(uint64_t,uint64_t at,const char* value) {return names[at]==value;}
#define E33_PICTO_SCHEMA_FIXTURE
#include "picto_inventory.h"
template<class T> void put(uint64_t at,T value) {std::memcpy(reinterpret_cast<void*>(at),&value,sizeof(value));}
int main() {
 alignas(16) std::array<uint8_t,128> st{};
 alignas(16) std::array<std::array<uint8_t,128>,4> fields{};
 const auto owner=reinterpret_cast<uint64_t>(st.data());
 const char* labels[]={"Item_HardcodedName_90_C7F763B74AAB28EF890A66854D7D95AA","Item_Type_88_2F24F8FB4235429B4DE1399DBA533C78","Pictos_Data_103_EE44D66B4E4F16A7FD44FF9F25777CF4","HideInInventory_105_28F500C94EA8D5C6632F7E8E4A85586E"};
 const char* types[]={"NameProperty","ByteProperty","ObjectProperty","BoolProperty"};
 const int offsets[]={0,24,192,296},widths[]={8,1,8,1};
 names[owner+24]="S_jRPG_Item_StaticData";
 put<int32_t>(owner+0x58,298);
 put<uint64_t>(owner+0x50,reinterpret_cast<uint64_t>(fields[0].data()));
 for(size_t n=0;n<4;++n) {
  const auto f=reinterpret_cast<uint64_t>(fields[n].data());
  names[f+32]=labels[n];names[100+n]=types[n];
  put<uint64_t>(f+8,100+n);put<uint64_t>(f+16,owner|1);
  put<uint64_t>(f+24,n<3?reinterpret_cast<uint64_t>(fields[n+1].data()):0);
  put<int32_t>(f+48,1);put<int32_t>(f+52,widths[n]);put<int32_t>(f+68,offsets[n]);
 }
 if(!picto_static_schema(0,owner))return 1;
 for(int bad:{297,299,304}) {put<int32_t>(owner+0x58,bad);if(picto_static_schema(0,owner))return 2;}
 put<int32_t>(owner+0x58,298);
 const auto f=reinterpret_cast<uint64_t>(fields[3].data());
 names[f+32]="Missing";if(picto_static_schema(0,owner))return 3;names[f+32]=labels[3];
 put<uint64_t>(f+16,owner);if(picto_static_schema(0,owner))return 4;put<uint64_t>(f+16,owner|1);
 put<int32_t>(f+68,297);if(picto_static_schema(0,owner))return 5;put<int32_t>(f+68,296);
 names[103]="ByteProperty";if(picto_static_schema(0,owner))return 6;names[103]="BoolProperty";
 if(!picto_static_schema(0,owner))return 7;
 std::cout<<"Picto raw extent / aligned stride and field identity guards passed\n";
}
