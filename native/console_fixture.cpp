#include <Windows.h>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <iostream>
#include <stdexcept>
#include <string>
template<class T> T local_read(uint64_t address) { return *reinterpret_cast<T*>(address); }
#include "console_commands.h"
static unsigned forwarded=0, printed=0;
static void __fastcall original(void*,const ConsoleString*) { ++forwarded; }
static void __fastcall output(void*,const ConsoleString*) { ++printed; }
static void check(bool value) { if (!value) throw std::runtime_error("console fixture assertion failed"); }
static void submit(const wchar_t* value) {
    int length=static_cast<int>(wcslen(value)+1);
    ConsoleString text{value,length,length}; console_command_hook(reinterpret_cast<void*>(1),&text);
}
int main() {
    console_original_command=original; console_output=output;
    command_console=1; command_thread=GetCurrentThreadId();
    check(set_console_names(L"sdk.hello,test"));
    submit(L"stat fps"); check(forwarded==1 && console_count==0);
    submit(L"  Py print('ok')"); submit(L"SDK.HELLO value");
    wchar_t text[32769]; check(poll_console_command(text) && wcscmp(text,L"Py print('ok')")==0);
    check(poll_console_command(text) && wcscmp(text,L"SDK.HELLO value")==0);
    for(unsigned i=0;i<17;++i) submit(L"py 1");
    check(console_count==16 && console_dropped==1);
    check(!set_console_names(L"bad,,name") && console_count==16 && console_name_count==2);
    check(set_console_names(L"new.command") && console_count==0 && console_dropped==17);
    submit(L"sdk.hello old"); check(forwarded==2);
    submit(L"new.command new"); check(console_count==1);
    check(remove_console_commands(0,true));
    submit(L"py 2"); check(forwarded==3 && console_count==0);
    check(set_console_names(L"") && console_name_count==0);
    std::cout << "PASS native passthrough, Python/custom routing, queue bounds, registration transaction, stale queue removal, late fallback\n";
}
