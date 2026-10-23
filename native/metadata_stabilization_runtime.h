#pragma once
#include "metadata_stabilization_protocol.h"
namespace e33_metadata {
template<class Ops>void run(Packet&p,Ops&ops){
 if(!valid(p)){p.error=3920;return;}
 for(unsigned i=0;i<p.count;++i){auto error=ops.admit(p.rows[i].before);if(error){p.error=error;p.failed=i+1;p.active=ops.active();return;}}
 const auto capacity=ops.preflight(p.count);if(capacity){p.error=capacity;p.failed=1;p.active=ops.active();return;}
 for(unsigned i=0;i<p.count;++i){auto&r=p.rows[i];r.outcome=Unknown;r.after=r.before;
  auto error=ops.acquire(r.before,r.token);
  if(!error&&!ops.stabilize(r.before,r.after))error=3922;
  r.error=error;p.completed=i+1;
  if(error){p.error=error;p.failed=i+1;p.active=ops.active();return;}
  r.outcome=RetainedStable;
 }p.active=ops.active();
}
}
