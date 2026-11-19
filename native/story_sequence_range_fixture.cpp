// Pure local-memory fixture; no process access or engine calls.
#include <cassert>
#include <array>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <utility>
struct CallIdentity {int32_t index=1,serial=2;uint64_t address=0;};
static std::map<uint64_t,uint64_t> memory;
static std::map<uint64_t,std::string> names;
static std::map<uint64_t,std::pair<std::string,std::string>> objects;
static bool selected=true,owned=true;
static uint64_t fixture_time=0;
uint64_t GetTickCount64(){return fixture_time;}
template<class T>T local_read(uint64_t address){auto it=memory.find(address);if(it!=memory.end())return static_cast<T>(it->second);T v{};std::memcpy(&v,reinterpret_cast<void*>(address),sizeof(v));return v;}
bool call_identity(uint64_t,const CallIdentity& id){return id.address!=0;}
bool exact_name(uint64_t,uint64_t at,const char* n){return names[at]==n;}
bool picto_class(uint64_t,uint64_t,const char*,const char*){return true;}
namespace e33_mesh {
 bool named(uint64_t,uint64_t at,const char*name,const char*path){return objects[at]==std::make_pair(std::string(name),std::string(path));}
 bool candidate_name(uint64_t,uint64_t,const char*name){return std::string(name)=="MovieScene_0";}
}
namespace e33_story_action {struct Dispatcher{uint64_t base=0;CallIdentity gi{};uint32_t guid[4]{};bool bound(){return selected;}};}
#define E33_PICTO_SCHEMA_FIXTURE
#include "picto_inventory.h"
#define E33_STORY_SEQUENCE_RANGE_FIXTURE
#include "story_sequence_range.h"
static e33_story_sequence_range::SaveContext save_context=e33_story_sequence_range::SaveContext::Selected;
namespace e33_story_sequence_range {SaveContext selected_context(uint64_t,CallIdentity,const uint32_t*){return save_context;}}
struct Pool {bool owns_object(uint64_t,uint64_t,uint64_t){return owned;}};
static constexpr uint64_t fixture_class=0x1000,playback=0x2000,rate=0x3000,rate_struct=0x4000,range_struct=0x5000,num=0x6000,den=0x7000,type=0x8000,int_type=0x9000;
void property(uint64_t f,uint64_t owner,const char*name,uint64_t kind,int offset,int width,uint64_t next=0){
 memory[f+0x10]=owner|1;memory[f+8]=kind;memory[f+0x44]=offset;memory[f+0x34]=width;memory[f+0x30]=1;memory[f+0x18]=next;names[f+0x20]=name;
}
void metadata(){
 memory[fixture_class+0x50]=playback;memory[fixture_class+0x58]=0x180;names[type]="StructProperty";names[int_type]="IntProperty";
 property(playback,fixture_class,"PlaybackRange",type,0x108,16,rate);property(rate,fixture_class,"TickResolution",type,0x120,8);
 memory[rate+0x70]=rate_struct;memory[playback+0x70]=range_struct;
 objects[range_struct]={"MovieSceneFrameRange","/Script/MovieScene"};objects[rate_struct]={"FrameRate","/Script/CoreUObject"};
 memory[rate_struct+0x50]=num;property(num,rate_struct,"Numerator",int_type,0,4,den);property(den,rate_struct,"Denominator",int_type,4,4);
}
void setup(std::array<uint8_t,512>& bytes,int index){
 bytes.fill(0);auto a=reinterpret_cast<uint64_t>(bytes.data());memory[a+16]=fixture_class;memory[a+32]=uint64_t(0xa000+index*0x100);
 const auto& p=e33_story_sequence_range::profiles[index];objects[memory[a+32]]={p.name,p.path};bytes[0x108]=1;
 std::memcpy(bytes.data()+0x10c,&p.lower,4);std::memcpy(bytes.data()+0x114,&p.expected,4);
 const int n=24000,d=1;std::memcpy(bytes.data()+0x120,&n,4);std::memcpy(bytes.data()+0x124,&d,4);
}
e33_story_sequence_range::Packet packet(std::array<uint8_t,512>& bytes,int index,uint32_t mode=0){
 e33_story_sequence_range::Packet p{};p.owner=uint64_t(10+index);p.scene={index+1,2,reinterpret_cast<uint64_t>(bytes.data())};p.gi={3,2,0xb000};p.leases[0]=uint64_t(20+index);p.leases[1]=30;p.guid[0]=0xe33c5701U;p.guid[1]=9;p.mode=mode;
 p.expected=e33_story_sequence_range::profiles[index].expected;p.replacement=e33_story_sequence_range::profiles[index].replacement;return p;
}
int main(){
 using namespace e33_story_sequence_range;metadata();Pool pool;std::array<uint8_t,512> g{},b{};setup(g,0);setup(b,1);Dispatcher dispatcher;
 auto apply=packet(g,0);dispatcher.run(1,2,pool,apply);assert(!apply.error&&apply.state==1&&apply.readback==7261600&&dispatcher.attached&&dispatcher.protects(20));
 auto beach=packet(b,1);dispatcher.run(1,2,pool,beach);assert(!beach.error&&beach.readback==5885600&&dispatcher.protects(21));
 auto wrong=packet(b,1,2);wrong.guid[1]++;dispatcher.run(1,2,pool,wrong);assert(wrong.error==rejected&&dispatcher.attached);
 auto restore=packet(g,0,2);dispatcher.run(1,2,pool,restore);assert(!restore.error&&restore.readback==6493600&&dispatcher.attached&&!dispatcher.protects(20));
 restore=packet(b,1,2);dispatcher.run(1,2,pool,restore);assert(!restore.error&&restore.readback==5501600&&!dispatcher.attached);
 // A travel/not-ready context preserves the range. Proven title, vanilla or
 // different-save context restores it without losing the exact close journal.
 setup(b,1);beach=packet(b,1);dispatcher.run(1,2,pool,beach);assert(dispatcher.active());
 save_context=SaveContext::Pending;dispatcher.poll();assert(dispatcher.active()&&!dispatcher.owners[1].restored);
 fixture_time+=50;save_context=SaveContext::Selected;dispatcher.poll();assert(dispatcher.active());
 save_context=SaveContext::Changed;dispatcher.poll();assert(dispatcher.active()); // throttle, no repeated map scan this message
 fixture_time+=50;dispatcher.poll();assert(!dispatcher.active()&&dispatcher.attached&&dispatcher.protects(21));
 auto inspected=packet(b,1,1);dispatcher.run(1,2,pool,inspected);assert(!inspected.error&&inspected.state==4&&inspected.readback==5501600);
 auto duplicate=packet(b,1);dispatcher.run(1,2,pool,duplicate);assert(duplicate.error==rejected);
 restore=packet(b,1,2);dispatcher.run(1,2,pool,restore);assert(!restore.error&&!dispatcher.attached);
 save_context=SaveContext::Selected;
 // Wrong rate, wrong lower bound, wrong movie, missing ownership and save proof
 // all reject before modifying the original upper endpoint.
 for(int which=0;which<5;++which){
  setup(b,1);selected=owned=true;
  if(which==0)b[0x120]^=1;if(which==1)b[0x10c]^=1;
  if(which==2)objects[memory[reinterpret_cast<uint64_t>(b.data())+32]].first="OtherMovie";
  if(which==3)owned=false;if(which==4)selected=false;
  auto p=packet(b,1);dispatcher.run(1,2,pool,p);assert(p.error==rejected&&!dispatcher.attached);
  uint32_t upper=0;std::memcpy(&upper,b.data()+0x114,4);assert(upper==5501600);
 }
 selected=owned=true;setup(b,1);beach=packet(b,1);dispatcher.run(1,2,pool,beach);assert(!beach.error);
 b[0x114]^=1;restore=packet(b,1,2);dispatcher.run(1,2,pool,restore);assert(restore.error==uncertain&&dispatcher.unknown&&dispatcher.protects(21));assert(!dispatcher.close());
 assert(profile_for(5501600,7261600)==-1);
}
