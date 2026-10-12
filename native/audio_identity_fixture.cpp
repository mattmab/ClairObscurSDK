#include "stable_identity.h"
#include <cassert>
#include "call_rejection_diagnostics.h"
struct Ops {
 CallIdentity current{17,0,0x1000};bool assign=true;unsigned minted=0;
 bool can_assign()const{return assign;}
 CallIdentity capture(uint64_t)const{return current;}
 int32_t allocate_serial(int32_t index){assert(index==17);++minted;if(!current.serial)current.serial=1001;return current.serial;}
 bool exact(const CallIdentity& id)const{return id.index==current.index&&id.serial==current.serial&&id.address==current.address;}
 void stop_creates_weak_reference(){if(!current.serial)allocate_serial(current.index);}
};
int main(){
 assert(call_identity_rejection_detail(true,true,false)==0);
 assert(call_identity_rejection_detail(false,false,false)==0x20200000u);
 assert(call_identity_rejection_detail(true,false,false)==0x20200001u);
 assert(call_identity_rejection_detail(false,true,false)==0x20200002u);
 assert(call_identity_rejection_detail(true,true,true)==0x20200007u);
 {Ops ops;auto id=ops.current;ops.stop_creates_weak_reference();assert(!ops.exact(id));}
 {Ops ops;auto id=ops.current;assert(stabilize_retained_identity(ops,id));ops.stop_creates_weak_reference();assert(ops.exact(id)&&ops.minted==1);}
 {Ops ops;auto id=ops.current;ops.current.serial=1234;assert(!stabilize_retained_identity(ops,id));assert(id.serial==0&&!ops.minted);}
 {Ops ops;auto id=ops.current;ops.current.address+=8;assert(!stabilize_retained_identity(ops,id));assert(!ops.minted);}
 {Ops ops;auto id=ops.current;ops.assign=false;assert(!stabilize_retained_identity(ops,id));assert(!ops.minted);}
}
