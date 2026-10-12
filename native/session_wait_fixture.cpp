#include "session_wait.h"
#include <chrono>
#include <cstdio>

int main() {
    using Clock=std::chrono::steady_clock;
    DWORD before=0,after=0;
    if(!GetProcessHandleCount(GetCurrentProcess(),&before)) return 1;
    const auto start=Clock::now();
    {
        SessionWait timer;
        for(int i=0;i<100;++i) timer.wait();
    }
    if(!GetProcessHandleCount(GetCurrentProcess(),&after) || after!=before) return 2;
    auto elapsed=std::chrono::duration<double,std::milli>(Clock::now()-start).count();
    std::printf("100 bounded waits: %.3fms; handle baseline restored\n",elapsed);
    return 0;
}
