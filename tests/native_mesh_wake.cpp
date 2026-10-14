// Exercise the real transport watcher without attaching to any game process.
#define E33_MESH_SESSION
#include "../native/session_transport.h"
#include <cassert>
#include <cstdio>
uint32_t backend_open(SessionPacket*){return 0;}
uint32_t backend_command(SessionPacket*){return 0;}
uint32_t backend_close(){return 0;}
bool backend_shutting_down(){return false;}
void backend_message(MSG*){}
bool backend_mesh_wake_needed(){return false;}
static unsigned drain(){MSG m{};unsigned n=0;while(PeekMessageW(&m,nullptr,WM_NULL,WM_NULL,PM_REMOVE))++n;return n;}
int main(){
    MSG m{};PeekMessageW(&m,nullptr,0,0,PM_NOREMOVE);
    for(unsigned cycle=0;cycle<20;++cycle){
        auto* w=new session_transport::Watch;
        w->owner=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        w->stop=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        w->animation_changed=CreateEventW(nullptr,FALSE,FALSE,nullptr);
        w->target_thread=GetCurrentThreadId();w->wake_nonce=1234;
        InterlockedIncrement(&w->refs);
        auto thread=CreateThread(nullptr,0,session_transport::watch_owner,w,0,nullptr);assert(thread);
        Sleep(25);assert(drain()==0); // inactive: no background message traffic
        InterlockedExchange(&w->animation_active,1);SetEvent(w->animation_changed);
        Sleep(60);assert(drain()==1); // a stalled pump retains at most ONE wake
        Sleep(25);assert(drain()==0); // no additional wake until acknowledgement
        InterlockedExchange(&w->wake_pending,0);
        Sleep(25);assert(drain()==1);
        InterlockedExchange(&w->animation_active,0);SetEvent(w->animation_changed);
        InterlockedExchange(&w->wake_pending,0);
        Sleep(25);assert(drain()==0);
        if(cycle%2)SetEvent(w->owner);else SetEvent(w->stop);
        assert(WaitForSingleObject(thread,1000)==WAIT_OBJECT_0);
        assert(drain()==(cycle%2)); // owner loss emits one cleanup notification
        assert(w->disconnected==LONG(cycle%2));
        CloseHandle(thread);session_transport::release(w);
    }
    puts("PASS: 20 watcher lifecycles, inactive sleep, bounded queue, resume, stop and owner loss");
}
