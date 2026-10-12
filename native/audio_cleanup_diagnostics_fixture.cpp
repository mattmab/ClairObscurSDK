#include "audio_cleanup_diagnostics.h"
#include <cassert>
#include <array>
int main() {
 AudioCleanupDiagnostics d;d.counts(3,4,5);
 d.phase(AudioCleanupPhase::Stop,2,0);d.dispatching();
 assert(d.snapshot(2).outcome==2);
 d.returned(201,0); // Known non-dispatch can advance after retry.
 d.phase(AudioCleanupPhase::Destroy,2,1);d.returned(209,0);d.failure(1);
 d.phase(AudioCleanupPhase::Complete);d.counts(0,0,0);d.returned(0,1);
 auto s=d.snapshot(2);assert(s.phase==10 && s.native_error==209 && s.outcome==0);
 assert(s.index==2 && s.step==1 && s.owned_count==5 && s.original_count==3);
 d.pause(1513,209);d.pause(0,0);assert(d.snapshot(2).pause_error==1513);
 std::array<unsigned char,256> wire{};std::memcpy(wire.data()+32,&s,sizeof(s));
 uint32_t magic{};std::memcpy(&magic,wire.data()+32,4);assert(magic==0x44413345);
 for(size_t i=96;i<wire.size();++i) assert(wire[i]==0);
 d.reset();d.pause(407,201);d.pause(1513,209);d.pause(407,201);
 assert(d.snapshot(2).pause_error==1513 && d.snapshot(2).pause_native_error==209);
 d.reset();d.phase(AudioCleanupPhase::Complete);s=d.snapshot(0);
 assert(s.version==1 && s.size==64 && !s.reserved && s.phase==14 && !s.native_error);
}
