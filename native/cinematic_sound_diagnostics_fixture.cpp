#include "cinematic_sound_diagnostics.h"
#include <array>
#include <cassert>
int main(){
 using namespace e33_cinematic;
 SoundEventDiagnostics d{1,2,3,4,5,6};std::array<unsigned char,128> payload;payload.fill(0xff);
 assert(!sound_diagnostics_payload(nullptr,payload.size(),d));
 assert(!sound_diagnostics_payload(payload.data(),23,d));assert(payload[0]==0xff);
 assert(sound_diagnostics_payload(payload.data(),payload.size(),d));
 uint32_t words[6]{};std::memcpy(words,payload.data(),24);
 for(unsigned i=0;i<6;++i)assert(words[i]==i+1);
 for(size_t i=24;i<payload.size();++i)assert(payload[i]==0);
 d.eligible_game_thread_calls=UINT32_MAX;sound_count(d.eligible_game_thread_calls);assert(d.eligible_game_thread_calls==UINT32_MAX);
 d.failures=UINT32_MAX-1;sound_count(d.failures);sound_count(d.failures);assert(d.failures==UINT32_MAX);
 d={};assert(sound_diagnostics_payload(payload.data(),payload.size(),d));for(auto byte:payload)assert(byte==0);
}
