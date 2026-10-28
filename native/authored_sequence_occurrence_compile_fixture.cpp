#define NOMINMAX
#include <windows.h>
#include "target_authored_sequence_occurrence.h"

using Query=TargetAuthoredBindingQuery<StrongLeasePool<>>;
using Reader=TargetAuthoredOccurrenceReader<Query>;
template struct TargetAuthoredOccurrenceReader<Query>;
template bool e33_authored_occurrence::Proof<CallIdentity>::unique<Reader>(Reader&,const CallIdentity&,const CallIdentity&);
int main(){return 0;}
