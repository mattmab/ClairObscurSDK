#include "battle_completion_receipt.h"
#include "battle_completion_frame.h"
#include "battle_completion_schema.h"
#include <string>
#include <set>
#include <tuple>
#include <cassert>
#include <map>
#include <cstring>
using namespace e33_battle_completion;
struct Memory{
 std::map<uint64_t,uint8_t> bytes;
 template<class T>void put(uint64_t at,T value){const auto* p=reinterpret_cast<const uint8_t*>(&value);for(unsigned i=0;i<sizeof(T);++i)bytes[at+i]=p[i];}
 bool operator()(uint64_t at,void* out,unsigned n){auto* p=static_cast<uint8_t*>(out);for(unsigned i=0;i<n;++i){auto it=bytes.find(at+i);if(it==bytes.end())return false;p[i]=it->second;}return true;}
};

struct SchemaMemory:Memory {
 uint64_t base=0x10000000;std::map<uint64_t,std::string> names;
 std::map<uint64_t,std::pair<std::string,std::string>> objects;std::set<uint64_t> classes;
 template<class T>T read(uint64_t at){T value{};assert((*this)(at,&value,sizeof(value)));return value;}
 bool named(uint64_t at,const char* name){return names.count(at)&&names[at]==name;}
 bool live(uint64_t at){return objects.count(at)!=0;}
 bool is_class(uint64_t at){return classes.count(at)!=0;}
 bool object_name(uint64_t at,const char* name,const char* package){return objects.count(at)&&objects[at]==std::make_pair(std::string(name),std::string(package));}
};
static void schema_fixture(){
 SchemaMemory m;const uint64_t fn=0x2000,pc=0x3000,cls=0x4000,p0=0x5000,p1=0x6000,en=0x7000,values=0x8000;
 m.objects[fn]={"ResumeExplorationOnBattleEnd","Function"};m.objects[pc]={"Controller","Actor"};
 m.objects[cls]={"BP_PlayerController_WorldMap_C","/Game/Gameplay/WorldMap/BP_PlayerController_WorldMap"};m.classes.insert(cls);
 m.objects[en]={"EBattleEndResult","/Game/Gameplay/Battle/EBattleEndResult"};
 m.names[fn+24]="ResumeExplorationOnBattleEnd";m.put(fn+32,cls);m.put(pc+16,cls);m.put(fn+0xb0,uint32_t(0x0c020000));
 m.put(fn+0xb6,uint16_t(9));m.put(fn+0xb8,uint16_t(65535));m.put(fn+0x58,uint32_t(9));m.put(fn+0xd8,m.base+0x13937a0);m.put(fn+0x50,p0);
 for(unsigned i=0;i<2;++i){const auto p=i?p1:p0;m.put(p+0x18,i?uint64_t(0):p1);m.put(p+0x10,fn|1);
  m.put(p+0x38,uint64_t(0x8001040000294));m.put(p+0x30,uint32_t(1));m.put(p+0x34,uint32_t(i?1:8));m.put(p+0x44,uint32_t(i?8:0));
  m.put(p,m.base+(i?0x6e10420ULL:0x6e13040ULL));m.put(p+8,uint64_t(i?0x9000:0xa000));m.names[i?0x9000:0xa000]=i?"ByteProperty":"NameProperty";
  m.names[p+0x20]=i?"BattleEndResult":"EnemyGlobalID";
 }
 m.put(p1+0x70,en);m.put(en+0x40,values);m.put(en+0x48,int32_t(5));m.put(en+0x4c,int32_t(5));
 const char* names[]={"EBattleEndResult::NewEnumerator0","EBattleEndResult::NewEnumerator1","EBattleEndResult::NewEnumerator2","EBattleEndResult::NewEnumerator3","EBattleEndResult::EBattleEndResult_MAX"};
 for(unsigned i=0;i<5;++i){m.names[values+i*16]=names[i];m.put(values+i*16+8,int64_t(i));}
 assert(completion_schema(m,fn,pc,true));assert(!completion_schema(m,fn,pc,false));
 {auto bad=m;bad.put(p1+0x44,uint32_t(9));assert(!completion_schema(bad,fn,pc,true));}
 {auto bad=m;bad.put(p1+0x38,uint64_t(0x8001040000394));assert(!completion_schema(bad,fn,pc,true));}
 {auto bad=m;bad.put(values+16+8,int64_t(2));assert(!completion_schema(bad,fn,pc,true));}
 {auto bad=m;bad.names[values+16]="AnotherEnum::NewEnumerator1";assert(!completion_schema(bad,fn,pc,true));}
 {auto bad=m;bad.put(fn+0xd8,m.base+0x13937b0);assert(!completion_schema(bad,fn,pc,true));}
 {auto bad=m;bad.put(p1+0x18,p0);assert(!completion_schema(bad,fn,pc,true));}
 {auto bad=m;bad.names[p0+0x20]="OtherID";assert(!completion_schema(bad,fn,pc,true));}
}
int main(){
 schema_fixture();
 const Context context{{1,2,0x1000},{2,3,0x2000},{3,4,0x3000},{4,5,0x4000},91,123};
 Receipt receipt;Journal j;assert(!j.arm(context,false));assert(j.arm(context,true));
 assert(!j.arm(context,true));assert(!j.take(91,receipt));
 assert(!j.observe_post(context,999,1,true,true));assert(j.state()==State::armed);
 assert(j.observe_post(context,123,1,true,true));assert(!j.observe_post(context,123,1,true,true));
 assert(!j.take(92,receipt));assert(j.take(91,receipt));assert(receipt.result==1&&receipt.battle==91);
 assert(!j.take(91,receipt));assert(!j.arm(context,true));
 Journal defeat;assert(defeat.arm(context,true));assert(defeat.observe_post(context,123,2,true,true));assert(defeat.take(91,receipt));assert(receipt.result==2);
 for(unsigned kind=0;kind<6;++kind){Journal bad;assert(bad.arm(context,true));auto next=context;
  if(kind==0)++next.world.serial;if(kind==1)++next.controller.address;if(kind==2)++next.source.serial;
  if(kind==3)++next.arena.address;if(kind==4)++next.battle;if(kind==5)++next.private_name;
  assert(!bad.observe_post(next,123,1,true,true));assert(bad.state()==State::revoked);assert(!bad.take(91,receipt));}
 Journal unknown;assert(unknown.arm(context,true));assert(!unknown.observe_post(context,123,1,false,true));assert(unknown.state()==State::uncertain);assert(!unknown.take(91,receipt));
 Journal invalid;assert(invalid.arm(context,true));assert(!invalid.observe_post(context,123,3,true,true));assert(invalid.state()==State::uncertain);
 Journal closed;assert(closed.arm(context,true));closed.revoke();assert(!closed.observe_post(context,123,1,true,true));
 Memory m;const uint64_t frame=0x1000,fn=0x2000,obj=0x3000,script=0x4000,locals=0x5000;
 m.put(frame+0x10,fn);m.put(frame+0x90,uint64_t(0));m.put(frame+0x18,obj);m.put(frame+0x20,script+60);
 m.put(frame+0x28,locals);m.put(frame+0x80,uint64_t(0));m.put(locals,uint64_t(123));m.put(locals+8,uint8_t(1));
 FrameInput input;assert(copy_post_frame(m,frame,fn,obj,script,67,true,input));assert(input.private_name==123&&input.result==1);
 assert(!copy_post_frame(m,frame,fn,obj,script,67,false,input));
 m.put(frame+0x20,script+68);assert(!copy_post_frame(m,frame,fn,obj,script,67,true,input));
 m.put(frame+0x20,script+60);m.put(frame+0x80,uint64_t(9));assert(!copy_post_frame(m,frame,fn,obj,script,67,true,input));
}
