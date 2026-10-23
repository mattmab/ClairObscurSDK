#define E33_RETIRED_WORLD_SESSION
#include "retired_world_gate.h"
#include "retired_world_getter.h"
#include "retired_world_release.h"
#include "audio_pause_journal.h"
#include "menu_session.h"
#include <cassert>
#include <vector>
using namespace e33_retired_world;
struct Proof {
 Snapshot snapshots[2]{{{1,1001,0x1000},{2,1002,0x2000},{3,1003,0x3000}},{{1,1001,0x1000},{2,1002,0x2000},{3,1003,0x3000}}};
 unsigned observed=0,acquired=0,released=0;bool ready=true,controller=true;uint32_t release_error=0;
 bool observe(Snapshot&out){if(!ready)return false;out=snapshots[observed++%2];return true;}
 bool controller_world(CallIdentity,CallIdentity){return controller;}
 template<class P>uint32_t acquire(P&,uint64_t,CallIdentity,uint64_t&token){++acquired;token=42;return 0;}
 bool stabilize(CallIdentity&){return true;}
 template<class P>uint32_t release(P&,uint64_t,uint64_t){++released;return release_error;}
};
struct Audio {unsigned sets=0;bool unknown=false;bool inspect(size_t,bool&p,bool&paused){p=true;paused=false;return true;}AudioPauseResult set(size_t,bool){++sets;return unknown?AudioPauseResult::Unknown:AudioPauseResult::Ok;}};
struct MenuOps {
 bool retired=false;unsigned restores=0,deactivations=0,detaches=0,baseline_releases=0,epoch_releases=0;
 MenuResult baseline_result=MenuResult::Ok,epoch_result=MenuResult::Ok;
 bool validate_preparation(uint64_t,uint64_t,uint64_t,uint64_t){return true;}bool validate_owned(uint64_t,uint64_t,uint64_t,uint64_t){return true;}
 MenuResult admit_world_actions(){return retired?MenuResult::Invalid:MenuResult::Ok;}
 MenuContext context(){return MenuContext::Ready;}MenuResult capture_baseline(){return MenuResult::Ok;}
 MenuResult release_prepared_baseline(){return MenuResult::Ok;}MenuResult release_epoch_anchor(){++epoch_releases;return epoch_result;}
 MenuResult release_baseline_result(){++baseline_releases;return baseline_result;}
 MenuFocusOwner focus_owner(){return retired?MenuFocusOwner::Unrelated:MenuFocusOwner::Owned;}
 bool prior_target_valid(){return true;}bool attach(){return true;}bool focus(){return true;}
 bool restore(){++restores;return true;}bool deactivate(){++deactivations;return true;}bool detach(){++detaches;return true;}
};
int main(){
 {CallPacket packet{};packet.outcome=CallDispatchReturned;CallIdentity result{};
  assert(owning_player_output(packet,result)==OwningPlayerResult::Null);
  packet.object_count=1;packet.objects[0]={0,{7,1007,0x7000}};
  assert(owning_player_output(packet,result)==OwningPlayerResult::Valid&&result.address==0x7000&&packet.data[0]==0);
  packet.objects[0].offset=8;assert(owning_player_output(packet,result)==OwningPlayerResult::Invalid);
  packet.objects[0].offset=0;packet.objects[0].identity.serial=0;assert(owning_player_output(packet,result)==OwningPlayerResult::Invalid);}

 {std::vector<int>rows{1,2,3};std::vector<int>acks;unsigned attempts=0;
  auto release=[&](int value)->uint32_t{++attempts;if(value==2&&attempts==2)return 407;acks.push_back(value);return 0;};
  assert(release_reverse(rows,release)==407&&rows==std::vector<int>({1,2})&&acks==std::vector<int>({3}));
  assert(release_reverse(rows,release)==0&&rows.empty()&&acks==std::vector<int>({3,2,1}));
  rows={1,2};assert(release_reverse(rows,[](int)->uint32_t{return 2109;})==2109&&rows==std::vector<int>({1,2}));}

 {Proof p;int pool=0;Anchor a;assert(a.capture(p,pool,1,{4,1004,0x4000})==0);assert(a.prove(p)==Result::SameWorld);
  p.snapshots[0].world=p.snapshots[1].world={5,1005,0x5000};assert(a.prove(p)==Result::Retired);
  p.ready=false;assert(a.prove(p)==Result::Retired);
  assert(a.release(p,pool,1)==0&&a.token()==0&&p.acquired==1&&p.released==1);}
 {Proof p;p.release_error=407;int pool=0;Anchor a;
  assert(a.capture(p,pool,1,{4,1004,0x4000})==407&&!a.established()&&a.token()==42&&a.prove(p)==Result::Unknown);
  p.release_error=0;assert(a.release(p,pool,1)==0&&a.token()==0&&p.released==2);}

 {Proof p;auto old=p.snapshots[0].world;p.snapshots[1].world={5,1005,0x5000};assert(double_observe(p,old)==Result::Pending);
  p.snapshots[0].world=p.snapshots[1].world={3,2000,0x3000};assert(double_observe(p,old)==Result::Unknown);}
 {Audio ops;AudioPauseJournal<2> journal;assert(journal.open(ops,2)==AudioPauseResult::Ok&&ops.sets==2);
  assert(journal.abandon_retired_world()==AudioPauseResult::Ok&&!journal.active()&&ops.sets==2);}
 {Audio ops;ops.unknown=true;AudioPauseJournal<2> journal;assert(journal.open(ops,1)==AudioPauseResult::Unknown);
  assert(journal.abandon_retired_world()==AudioPauseResult::Unknown&&journal.active()&&ops.sets==1);}
 {MenuSession m;MenuOps o;assert(m.prepare(o,1,2,3,4)==MenuResult::Ok);assert(m.attach(o,1,2)==MenuResult::Ok);assert(m.focus(o,1,2)==MenuResult::Ok);
  o.retired=true;o.baseline_result=MenuResult::Deferred;assert(m.close_session(o)==MenuResult::Deferred&&m.active());
  assert(o.restores==0&&o.deactivations==1&&o.detaches==1&&o.epoch_releases==0);
  o.baseline_result=MenuResult::Ok;o.epoch_result=MenuResult::Deferred;assert(m.close_session(o)==MenuResult::Deferred&&m.active());
  assert(o.restores==0&&o.deactivations==1&&o.detaches==1&&o.baseline_releases==2);
  o.epoch_result=MenuResult::Ok;assert(m.close_session(o)==MenuResult::Ok&&!m.active()&&o.baseline_releases==2&&o.epoch_releases==2);}
 {MenuSession m;MenuOps o;assert(m.prepare(o,1,2,3,4)==MenuResult::Ok);assert(m.attach(o,1,2)==MenuResult::Ok);
  assert(m.close_session(o)==MenuResult::Ok&&o.restores==1);}
 {MenuSession m;MenuOps o;assert(m.prepare(o,1,2,3,4)==MenuResult::Ok);o.retired=true;
  assert(m.attach(o,1,2)==MenuResult::Invalid&&o.deactivations==0&&o.restores==0);
  assert(m.close_session(o)==MenuResult::Ok&&!m.active());}
 {MenuSession m;MenuOps o;assert(m.prepare(o,1,2,3,4)==MenuResult::Ok);m.quarantine();assert(m.close_session(o)==MenuResult::Quarantined&&m.active()&&o.epoch_releases==0);}
}
