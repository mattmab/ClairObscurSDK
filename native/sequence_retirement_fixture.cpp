#include "sequence_retirement.h"
#include "sequence_camera_journal.h"
#include "media_owner_protocol.h"
#include "retired_collector_release.h"
#include <cassert>
#include <stdexcept>
using e33_camera::Result;
struct CameraOps {
    bool live=true,throw_release=false;unsigned reads=0,restores=0,releases=0;
    Result result=Result::ok;
    bool context(){return live;}
    bool same(int a,int b){return a==b;}
    Result capture(int&,int& out){out=2;return Result::ok;}
    Result current(int,int&){++reads;throw std::runtime_error("Old camera read forbidden");}
    Result restore(int,int){++restores;throw std::runtime_error("Old camera restoration forbidden");}
    bool proven_owned(int){return true;}
    bool retain_owned(int){return true;}
    Result release(){++releases;if(throw_release)throw std::runtime_error("Unknown release");return result;}
};
struct CollectorPool {
    bool own=false;unsigned count=0,calls=0;StrongLeaseResult result=StrongLeaseResult::Ok;
    bool owns(uint64_t){return own;}
    unsigned active(){return count;}
    template<class Ops> StrongLeaseResult close(Ops&,uint64_t){++calls;return result;}
};
int main(){
    using e33_retired_world::Snapshot;
    const Snapshot old{{1,2,0x10000},{2,3,0x20000},{3,4,0x30000}};
    const Snapshot fresh{{1,2,0x10000},{2,3,0x20000},{4,5,0x40000}};
    assert(e33_sequence_retirement::different_world(old,fresh,fresh));
    assert(!e33_sequence_retirement::different_world(old,old,old));
    {auto bad=fresh;bad.world.address=old.world.address;assert(!e33_sequence_retirement::different_world(old,bad,bad));}
    {auto bad=fresh;bad.world.serial=0;assert(!e33_sequence_retirement::different_world(old,bad,bad));}
    {auto bad=old;bad.world.serial=0;assert(!e33_sequence_retirement::different_world(bad,fresh,fresh));}
    {auto bad=fresh;++bad.engine.serial;assert(!e33_sequence_retirement::different_world(old,bad,bad));}
    {auto bad=fresh;++bad.viewport.address;assert(!e33_sequence_retirement::different_world(old,bad,bad));}
    {auto bad=fresh;++bad.world.serial;assert(!e33_sequence_retirement::different_world(old,fresh,bad));}
    {CameraOps o;e33_camera::Journal<int> j;assert(j.arm(o,1)==Result::ok);assert(j.created());
     assert(j.retire(o,false)==Result::rejected);assert(j.active());assert(!o.reads&&!o.restores&&!o.releases);
     assert(j.retire(o,true)==Result::ok);assert(!j.active());assert(!o.reads&&!o.restores&&o.releases==1);}
    {CameraOps o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.live=false;
     assert(j.retire(o,true)==Result::deferred);assert(!o.releases);o.live=true;o.result=Result::deferred;
     assert(j.retire(o,true)==Result::deferred);assert(j.active());o.result=Result::ok;
     assert(j.retire(o,true)==Result::ok);assert(o.releases==2&&!o.reads&&!o.restores);}
    {CameraOps o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.throw_release=true;
     try{j.retire(o,true);assert(false);}catch(const std::runtime_error&){}
     assert(j.quarantined());assert(j.retire(o,true)==Result::unknown);assert(o.releases==1);}
    {CameraOps o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.result=Result::unknown;
     assert(j.retire(o,true)==Result::unknown);assert(j.retire(o,true)==Result::unknown);assert(o.releases==1);}
    {MediaCleanupState media;media.state=1;assert(media.retire(false,true)==1404);assert(media.state==1);
     assert(media.retire(true,false)==1403);assert(media.state==1);assert(!media.retire(true,true));assert(!media.state&&media.step==2);}
    {MediaCleanupState media;media.state=2;assert(media.retire(true,true)==1403);assert(media.state==2);}
    {CollectorPool p;CameraOps o;assert(release_retired_collectors(p,o,42)==StrongLeaseResult::Ok);assert(!p.calls);}
    {CollectorPool p;CameraOps o;p.count=1;assert(release_retired_collectors(p,o,42)==StrongLeaseResult::Quarantined);assert(!p.calls);}
    {CollectorPool p;CameraOps o;p.own=true;p.count=1;p.result=StrongLeaseResult::Deferred;
     assert(release_retired_collectors(p,o,42)==StrongLeaseResult::Deferred);assert(p.calls==1);}
}
