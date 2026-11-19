#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
struct CallIdentity {int32_t index=1,serial=2;uint64_t address=0;};
static std::map<uint64_t,uint64_t> memory;
static std::map<uint64_t,std::string> names;
static bool fixture_selected=true,owned=true;
static constexpr uint64_t fixture_gi=0xa000,fixture_world=0xb000,name_array=0xc000,object_array=0xd000,fixture_automatic=0xe000;
template<class T>T local_read(uint64_t a){auto i=memory.find(a);if(i!=memory.end())return static_cast<T>(i->second);T value{};std::memcpy(&value,reinterpret_cast<void*>(a),sizeof(value));return value;}
bool call_identity(uint64_t,const CallIdentity&i){return i.address!=0;}
CallIdentity call_capture(uint64_t,uint64_t a){return {1,2,a};}
bool picto_class(uint64_t,uint64_t,const char*,const char*){return true;}
bool exact_name(uint64_t,uint64_t at,const char*n){return names[at]==n;}
uint64_t zone_ref(uint64_t,uint64_t,const char*){return fixture_gi;}
uint64_t picto_field(uint64_t,uint64_t object,const char*name,const char*,int offset,int,uint64_t*descriptor=nullptr){
 if(descriptor)*descriptor=std::string(name)=="CharacterSaveStateRowName"?name_array:std::string(name)=="AutoAddToParty"?fixture_automatic:object_array;
 return object+uint64_t(offset);
}
namespace e33_mesh {bool named(uint64_t,uint64_t,const char*,const char*){return true;}}
namespace e33_story_action {struct Dispatcher {uint64_t base=0;CallIdentity gi{};uint32_t guid[4]{};bool bound(){return fixture_selected;}};}
namespace e33_retired_world {struct Snapshot {CallIdentity world{};};struct TargetOps {uint64_t base;bool observe(Snapshot&s){s.world={1,2,::fixture_world};return true;}};}
namespace e33_blueprint_names {bool resolve(uint64_t,const char*name,uint64_t&role){role=std::string(name)=="TestScholar"?0x1234:0x5678;return std::string(name)=="TestScholar"||std::string(name)=="TestGuardian";}}
#include "story_party_join_data.h"
struct Pool {bool owns_object(uint64_t,uint64_t,uint64_t){return owned;}};
void metadata(){
 for(auto row:{std::make_pair(name_array,"NameProperty"),std::make_pair(object_array,"ObjectProperty")}){
  const auto inner=row.first+0x100;memory[row.first+0x70]=0;memory[row.first+0x78]=inner;memory[inner+0x10]=row.first;memory[inner+8]=inner+0x200;
  names[inner+0x200]=row.second;memory[inner+0x30]=1;memory[inner+0x34]=8;memory[inner+0x44]=0;memory[inner+0x70]=0xf000;
 }
 memory[fixture_automatic+0x70]=0xff010001U;memory[fixture_world+32]=0;
}
void setup(std::array<uint8_t,256>&action,std::array<uint8_t,256>&executor){
 action.fill(0);executor.fill(0);action[64]=1;
 std::memcpy(action.data()+32,&fixture_gi,8);std::memcpy(executor.data()+32,&fixture_world,8);
}
e33_story_party_join_data::Packet request(std::array<uint8_t,256>&a,std::array<uint8_t,256>&e,uint32_t mode=0){
 e33_story_party_join_data::Packet p{};p.owner=1;p.ids[0]={1,2,reinterpret_cast<uint64_t>(a.data())};p.ids[1]={3,4,fixture_gi};p.ids[2]={5,6,reinterpret_cast<uint64_t>(e.data())};
 p.leases[0]=1;p.leases[1]=2;p.leases[2]=3;p.guid[0]=0xe33c5701U;p.mode=mode;std::memcpy(p.character,"TestScholar",12);return p;
}
int main(){
 using namespace e33_story_party_join_data;metadata();Pool pool;std::array<uint8_t,256>a{},e{};setup(a,e);Dispatcher d;
 auto p=request(a,e);d.run(1,2,pool,p);assert(!p.error&&p.state==1&&d.active()&&d.protects(1));
 assert(local_read<uint64_t>(local_read<uint64_t>(reinterpret_cast<uint64_t>(a.data())+48))==0x1234);
 auto inspect=request(a,e,1);d.run(1,2,pool,inspect);assert(!inspect.error&&inspect.state==2);
 // A running instance referencing this action prevents restoration/release.
 std::array<uint8_t,64>instance{};auto action=reinterpret_cast<uint64_t>(a.data());std::memcpy(instance.data()+40,&action,8);
 const auto instance_address=reinterpret_cast<uint64_t>(instance.data()),data=reinterpret_cast<uint64_t>(&instance_address);const uint32_t count=1;
 std::memcpy(e.data()+168,&data,8);std::memcpy(e.data()+176,&count,4);std::memcpy(e.data()+180,&count,4);
 auto close=request(a,e,2);d.run(1,2,pool,close);assert(close.error==busy&&d.active()&&!d.unknown);
 std::memset(e.data()+168,0,16);close=request(a,e,2);d.run(1,2,pool,close);assert(!close.error&&!d.active());
 for(unsigned i=48;i<64;++i)assert(a[i]==0);
 // A different consumer-defined ID uses the same owner implementation.
 setup(a,e);p=request(a,e);std::memcpy(p.character,"TestGuardian",13);d.run(1,2,pool,p);assert(!p.error);
 assert(local_read<uint64_t>(local_read<uint64_t>(reinterpret_cast<uint64_t>(a.data())+48))==0x5678);
 close=request(a,e,2);d.run(1,2,pool,close);assert(close.error==rejected&&d.active());
 close=request(a,e,2);std::memcpy(close.character,"TestGuardian",13);d.run(1,2,pool,close);assert(!close.error&&!d.active());
 for(int invalid=0;invalid<5;++invalid){
  setup(a,e);fixture_selected=owned=true;
  if(invalid==0)fixture_selected=false;if(invalid==1)owned=false;if(invalid==2)a[48]=1;if(invalid==3)a[64]=0;if(invalid==4)a[8]=0x10;
  p=request(a,e);d.run(1,2,pool,p);assert(p.error==rejected&&!d.active());
 }
 fixture_selected=owned=true;setup(a,e);p=request(a,e);d.run(1,2,pool,p);assert(!p.error);
 a[48]^=1;close=request(a,e,2);d.run(1,2,pool,close);assert(close.error==uncertain&&d.unknown&&d.protects(1));
}
