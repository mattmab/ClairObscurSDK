#include "cinematic_widget_diagnostics.h"
#include <array>
#include <cassert>
#include <iostream>
int main() {
    using namespace e33_cinematic;
    WidgetDiagnostics counters{};
    widget_count(counters.eligible_game_thread_calls);assert(counters.eligible_game_thread_calls==1);
    counters.eligible_game_thread_calls=UINT32_MAX-1;
    widget_count(counters.eligible_game_thread_calls);widget_count(counters.eligible_game_thread_calls);
    assert(counters.eligible_game_thread_calls==UINT32_MAX);
    counters.exact_frames=7;counters.root_misses=2;counters.owned_matches=5;counters.failed=1;
    std::array<uint8_t,128> payload{};payload.fill(0xff);
    assert(widget_diagnostics_payload(payload.data(),payload.size(),counters));
    WidgetDiagnostics decoded{};std::memcpy(&decoded,payload.data(),sizeof(decoded));
    assert(!std::memcmp(&decoded,&counters,sizeof(counters)));
    for(size_t i=sizeof(counters);i<payload.size();++i) assert(payload[i]==0);
    assert(!widget_diagnostics_payload(nullptr,payload.size(),counters));
    assert(!widget_diagnostics_payload(payload.data(),19,counters));
    std::cout<<"Widget diagnostic saturation and bounded zero-tail snapshot checks passed\n";
}
