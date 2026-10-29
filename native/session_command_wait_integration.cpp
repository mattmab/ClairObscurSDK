// Exercise the actual controller against a local synthetic busy message thread.
// This fixture never attaches to or modifies a game process.
#define main e33_unused_probe_main
#include "research_probe.cpp"
#undef main
#include <thread>
#include <atomic>
#include <cassert>
int main(){
    RuntimeSessionController connection;
    connection.mapping=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,sizeof(SessionPacket),nullptr);
    assert(connection.mapping);
    connection.packet=static_cast<SessionPacket*>(MapViewOfFile(connection.mapping,FILE_MAP_ALL_ACCESS,0,0,sizeof(SessionPacket)));
    assert(connection.packet);
    connection.target_process=OpenProcess(SYNCHRONIZE|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,GetCurrentProcessId());
    assert(connection.target_process);connection.opened=true;
    HANDLE ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);assert(ready);
    std::atomic<unsigned> dispatched{0};
    auto output=std::ostringstream{};auto* original=std::cout.rdbuf(output.rdbuf());
    std::thread worker([&](){
        MSG message{};PeekMessageW(&message,nullptr,0,0,PM_NOREMOVE);
        connection.tid=GetCurrentThreadId();SetEvent(ready);
        Sleep(6200); // Keep the original request queued beyond the old 5s limit.
        for(unsigned i=0;i<2;++i){
            assert(GetMessageW(&message,nullptr,0,0)>0);++dispatched;
            InterlockedExchange(&connection.packet->request.state,kRunning);
            connection.packet->request.result=42;
            InterlockedExchange(&connection.packet->request.state,kComplete);
        }
    });
    assert(WaitForSingleObject(ready,5000)==WAIT_OBJECT_0);CloseHandle(ready);
    connection.command(SessionDrain);assert(dispatched==1 && connection.packet->request.result==42);
    connection.command(SessionDrain);worker.join();connection.opened=false;
    std::cout.rdbuf(original);
    assert(dispatched==2 && connection.command_sequence==2);
    const auto notices=output.str();
    assert(notices.find("session_pending")!=std::string::npos);
    assert(notices.find("\"sequence\":1")!=std::string::npos);
    assert(notices.find("\"state\":1")!=std::string::npos);
    std::cout << "6.2s queued stall survived; exactly two original commands dispatched; subsequent command acknowledged" << std::endl;
    return 0;
}
