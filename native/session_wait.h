#pragma once
#include <windows.h>
#include <stdexcept>

// A controller-local high-resolution timer avoids rounding every short IPC
// wait up to the system's coarse Sleep interval. No spin loop, timer-resolution
// setting, target-process mutation or change to the existing timeout policy.
class SessionWait {
    HANDLE timer_=nullptr;
public:
    SessionWait() {
        timer_=CreateWaitableTimerExW(nullptr,nullptr,0x00000002,
                                     TIMER_MODIFY_STATE|SYNCHRONIZE);
        if(!timer_) throw std::runtime_error("SESSION_WAIT_TIMER_CREATE_FAILED");
    }
    SessionWait(const SessionWait&)=delete;
    SessionWait& operator=(const SessionWait&)=delete;
    ~SessionWait() { if(timer_) CloseHandle(timer_); }
    void wait() {
        LARGE_INTEGER due{};
        due.QuadPart=-5000; // 0.5ms, relative, in 100ns units.
        if(!SetWaitableTimer(timer_,&due,0,nullptr,nullptr,FALSE) ||
           WaitForSingleObject(timer_,1000)!=WAIT_OBJECT_0)
            throw std::runtime_error("SESSION_WAIT_TIMER_FAILED");
    }
};
