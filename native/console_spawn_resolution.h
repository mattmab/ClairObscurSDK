#pragma once
#include <cstdint>
namespace ConsoleSpawnResolution {
constexpr std::int32_t FunctionIndex=18293;
struct Identity {std::int32_t index=-1,serial=0;std::uint64_t address=0;};
inline bool same(const Identity&a,const Identity&b){return a.index==b.index && a.serial==b.serial && a.address==b.address;}
template<class Ops> inline bool native_provenance(const Ops& ops,std::uint64_t function,std::uint64_t owner){
 if(!ops.live(function) || !ops.live(owner))return false;
 const auto function_cls=ops.class_of(function),owner_cls=ops.class_of(owner),package=ops.outer_of(owner);
 if(!ops.live(function_cls) || !ops.live(owner_cls) || !ops.live(package))return false;
 const auto package_cls=ops.class_of(package);
 return ops.live(package_cls) && ops.named(function_cls,"Function") && ops.named(function,"SpawnObject") &&
  ops.outer_of(function)==owner && ops.named(owner_cls,"Class") && ops.named(owner,"GameplayStatics") &&
  ops.named(package_cls,"Package") && !ops.outer_of(package) && ops.named(package,"/Script/Engine");
}
template<class Ops> inline Identity resolve(Ops& ops){
 if(!ops.context())return {};
 const auto current=ops.capture(FunctionIndex);
 if(current.index!=FunctionIndex || current.serial<0 || !current.address || !ops.provenance(current) || !ops.context() || !same(ops.capture(FunctionIndex),current))return {};
 return current;
}
template<class Ops> inline bool revalidate(Ops& ops,const Identity& expected){
 return expected.index==FunctionIndex && expected.serial>=0 && expected.address && ops.context() && same(ops.capture(FunctionIndex),expected) && ops.provenance(expected);
}
}
