#include <cstdio>
#ifdef LEGACY_LEASE_MEASUREMENT
#include "baseline_lease_pool.h"
#else
#include "strong_lease_pool.h"
#endif
int main() {
    std::printf("pool=%zu storage=%zu holder=%zu\n",sizeof(StrongLeasePool<>),
        sizeof(StrongReferenceStorage),sizeof(TargetStrongReference));
}
