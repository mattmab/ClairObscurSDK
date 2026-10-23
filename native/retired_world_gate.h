#pragma once
#include "invocation_protocol.h"
namespace e33_retired_world {
enum class Result {SameWorld,Retired,Pending,Unknown};
inline bool same(const CallIdentity&a,const CallIdentity&b){return a.index==b.index&&a.serial==b.serial&&a.address==b.address;}
struct Snapshot {CallIdentity engine{},viewport{},world{};};
template<class Ops> Result double_observe(Ops&ops,const CallIdentity&old_world,Snapshot*out=nullptr){
 Snapshot a{},b{};
 if(!old_world.address||old_world.serial<=0)return Result::Unknown;
 if(!ops.observe(a)||!ops.observe(b))return Result::Pending;
 if(!same(a.engine,b.engine)||!same(a.viewport,b.viewport)||!same(a.world,b.world))return Result::Pending;
 if(out)*out=b;
 if(same(old_world,b.world))return Result::SameWorld;
 // A same-address/index serial change is not authority to retire a world.
 if(old_world.address==b.world.address)return Result::Unknown;
 return Result::Retired;
}
class Anchor {
 CallIdentity engine_{},viewport_{},world_{};uint64_t token_=0;bool established_=false,retired_=false,unrecoverable_=false;
public:
 const CallIdentity&engine()const{return engine_;}const CallIdentity&viewport()const{return viewport_;}
 const CallIdentity&world()const{return world_;}uint64_t token()const{return token_;}
 bool established()const{return established_;}bool retired()const{return retired_;}
 template<class Ops,class Pool>uint32_t capture(Ops&ops,Pool&pool,uint64_t session,CallIdentity controller){
  if(established_||token_)return 2051;
  Snapshot current{};if(!ops.observe(current)||!ops.controller_world(controller,current.world))return 2051;
  world_=current.world;
  // Token storage belongs to the owner before any engine registration/serial
  // allocation. Pool journals unknown registration even when token stays zero.
  auto error=ops.acquire(pool,session,world_,token_);if(error){if(error==408)unrecoverable_=true;return error;}
  if(!ops.stabilize(world_))return 2052;
  Snapshot fresh{};if(!ops.observe(fresh)||!same(fresh.engine,current.engine)||!same(fresh.viewport,current.viewport)||
     !same(fresh.world,world_)||!ops.controller_world(controller,world_))return 2052;
  engine_=fresh.engine;viewport_=fresh.viewport;
  // A World is only temporarily retained to stabilize its weak serial. Never
  // hold it across map travel: Unreal must be able to collect the old World.
  error=release(ops,pool,session);if(error)return error;
  Snapshot acknowledged{};
  if(!ops.observe(acknowledged)||!same(fresh.engine,acknowledged.engine)||
     !same(fresh.viewport,acknowledged.viewport)||!same(world_,acknowledged.world)||
     !ops.controller_world(controller,world_))return 2052;
  established_=true;return 0;
 }
 template<class Ops>Result prove(Ops&ops){
  if(retired_)return Result::Retired;
  if(!established_)return Result::Unknown;
  Snapshot fresh{};auto result=double_observe(ops,world_,&fresh);
  if(result==Result::SameWorld){engine_=fresh.engine;viewport_=fresh.viewport;}
  if(result==Result::Retired)retired_=true;
  return result;
 }
 template<class Ops,class Pool>uint32_t release(Ops&ops,Pool&pool,uint64_t session){
  if(unrecoverable_)return 2053;
  if(!token_)return 0;
  auto error=ops.release(pool,session,token_);if(!error)token_=0;
  return error;
 }
 void reset(){engine_={};viewport_={};world_={};token_=0;established_=retired_=unrecoverable_=false;}
};
}
