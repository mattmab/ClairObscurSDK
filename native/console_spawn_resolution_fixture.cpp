#include "console_spawn_resolution.h"
#include <cassert>
#include <map>
#include <string>
using namespace ConsoleSpawnResolution;
struct Ops {
 Identity identity{FunctionIndex,0,0x10000};bool context_ok=true,provenance_ok=true,change_after_admit=false;
 unsigned serial_allocations=0;
 bool context()const{return context_ok;}
 Identity capture(std::int32_t index)const{return index==identity.index?identity:Identity{};}
 bool provenance(const Identity&){if(change_after_admit)++identity.serial;return provenance_ok;}
};
struct Node {std::string name;std::uint64_t cls=0,outer=0;bool valid=true;};
struct Provenance {
 std::map<std::uint64_t,Node> nodes{{1,{"SpawnObject",2,3}},{2,{"Function"}},{3,{"GameplayStatics",4,5}},{4,{"Class"}},{5,{"/Script/Engine",6}},{6,{"Package"}}};
 bool live(std::uint64_t p)const{auto i=nodes.find(p);return i!=nodes.end() && i->second.valid;}
 std::uint64_t class_of(std::uint64_t p)const{return nodes.at(p).cls;}
 std::uint64_t outer_of(std::uint64_t p)const{return nodes.at(p).outer;}
 bool named(std::uint64_t p,const char* n)const{return nodes.at(p).name==n;}
};
int main(){
 Provenance proper;assert(native_provenance(proper,1,3));
 for(int change=0;change<8;++change){
  Provenance bad;
  if(change==0)bad.nodes[5].name="/Game/World";
  if(change==1)bad.nodes[4].name="BlueprintGeneratedClass";
  if(change==2)bad.nodes[1].name="OtherFunction";
  if(change==3)bad.nodes[3].name="OtherOwner";
  if(change==4)bad.nodes[1].outer=5;
  if(change==5)bad.nodes[5].outer=6;
  if(change==6)bad.nodes[5].valid=false;
  if(change==7)bad.nodes[2].name="DelegateFunction";
  assert(!native_provenance(bad,1,3));
 }

 Ops zero;auto initial=resolve(zero);assert(initial.address && initial.serial==0 && zero.serial_allocations==0);assert(revalidate(zero,initial));
 Ops positive;positive.identity.serial=22001;auto assigned=resolve(positive);assert(assigned.serial==22001 && positive.serial_allocations==0);assert(revalidate(positive,assigned));
 zero.identity.serial=1002;assert(!revalidate(zero,initial)); // zero remains exact, never a wildcard
 positive.identity.address+=8;assert(!revalidate(positive,assigned));
 Ops changed;changed.change_after_admit=true;assert(!resolve(changed).address);
 Ops wrong_index;wrong_index.identity.index=FunctionIndex+1;assert(!resolve(wrong_index).address);
 Ops wrong_path;wrong_path.provenance_ok=false;assert(!resolve(wrong_path).address);
 Ops wrong_thread;wrong_thread.context_ok=false;assert(!resolve(wrong_thread).address);
 Ops negative;negative.identity.serial=-1;assert(!resolve(negative).address);
}
