#pragma once
#include <windows.h>
#include <cwchar>
#include <cstdint>

// Optional connection-local wakeups. Names contain the existing unpredictable
// session nonce; an event never authorizes a command or replaces its state CAS.
class SessionHandoff {
public:
    HANDLE request=nullptr,complete=nullptr,timer=nullptr;
    SessionHandoff()=default;
    SessionHandoff(const SessionHandoff&)=delete;
    SessionHandoff& operator=(const SessionHandoff&)=delete;
    ~SessionHandoff(){close();}
    void close(){
        if(request)CloseHandle(request);
        if(complete)CloseHandle(complete);
        if(timer)CloseHandle(timer);
        request=complete=timer=nullptr;
    }
    bool connect(DWORD controller,uint64_t nonce,bool create){
        if(request||complete)return false;
        wchar_t name[128];
        swprintf_s(name,L"Local\\E33SessionHandoff314_%lu_%016llx_request",controller,nonce);
        request=create?CreateEventW(nullptr,FALSE,FALSE,name):OpenEventW(SYNCHRONIZE|EVENT_MODIFY_STATE,FALSE,name);
        if(!request || (create&&GetLastError()==ERROR_ALREADY_EXISTS)){close();return false;}
        swprintf_s(name,L"Local\\E33SessionHandoff314_%lu_%016llx_complete",controller,nonce);
        complete=create?CreateEventW(nullptr,FALSE,FALSE,name):OpenEventW(SYNCHRONIZE|EVENT_MODIFY_STATE,FALSE,name);
        if(!complete || (create&&GetLastError()==ERROR_ALREADY_EXISTS)){close();return false;}
        if(!create)timer=CreateWaitableTimerExW(nullptr,nullptr,0x00000002,TIMER_MODIFY_STATE|SYNCHRONIZE);
        return true;
    }
    bool deadline(DWORD milliseconds) {
        LARGE_INTEGER due{};due.QuadPart=-10000LL*milliseconds;
        return timer&&SetWaitableTimer(timer,&due,0,nullptr,nullptr,FALSE);
    }
};

// A loading hold can service the next sequential request without waiting a
// whole render frame. Bound both the wait and the total time in this hook;
// ordinary play, pending menu work and all teardown keep the original path.
struct SessionHandoffBudget {
    LARGE_INTEGER start{},frequency{};
    unsigned count=0;
    SessionHandoffBudget(){QueryPerformanceFrequency(&frequency);QueryPerformanceCounter(&start);}
    DWORD wait_ms() const {
        LARGE_INTEGER now{};QueryPerformanceCounter(&now);
        if(!frequency.QuadPart||count>=32)return 0;
        const double remaining=8.-1000.*double(now.QuadPart-start.QuadPart)/double(frequency.QuadPart);
        // Allow a freshly validated read projection to finish between requests.
        // The total per-engine-frame admission budget remains eight ms.
        return remaining>=4.?4:remaining>=3.?3:remaining>=2.?2:remaining>=1.?1:0;
    }
};
