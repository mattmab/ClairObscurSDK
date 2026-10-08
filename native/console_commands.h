#pragma once
#include <cwctype>
#include <atomic>

struct ConsoleString { const wchar_t* data; int32_t count, capacity; };
using ConsoleTextFn = void(__fastcall*)(void*,const ConsoleString*);
static uint64_t console_shadow[124]{}; // RTTI locator plus 123 primary virtual slots.
static ConsoleTextFn console_original_command=nullptr, console_output=nullptr;
static std::atomic<uint64_t> command_console{0};
static uint64_t command_table=0;
static std::atomic<DWORD> command_thread{0};
static wchar_t console_queue[16][4097]{};
static unsigned console_head=0, console_count=0, console_dropped=0;
static wchar_t console_names[256][65]{};
static unsigned console_name_count=0;
inline bool set_console_names(const wchar_t* text) {
    wchar_t candidate[256][65]{};
    unsigned count=0, length=0;
    for (size_t i=0; i<32769; ++i) {
        wchar_t c=text[i];
        if (!c || c==L',') {
            if (!length) { if (!c && !count) break; return false; }
            if (++count>256) return false;
            length=0;
            if (!c) break;
        } else {
            if (count>=256 || length>=64 || !((c>=L'a'&&c<=L'z') ||
                (length && ((c>=L'0'&&c<=L'9') || c==L'_' || c==L'.' || c==L'-')))) return false;
            candidate[count][length++]=c;
        }
    }
    std::memcpy(console_names,candidate,sizeof(candidate)); console_name_count=count;
    // A queued command must never transfer to a replacement registration owner.
    console_dropped+=console_count; console_head=console_count=0;
    return true;
}
inline bool sdk_console_command(const wchar_t* value) {
    size_t length=0;
    while (value[length] && value[length]!=L' ' && value[length]!=L'\t' && length<=64) ++length;
    if (length==2 && _wcsnicmp(value,L"py",2)==0) return true;
    for (unsigned i=0;i<console_name_count;++i)
        if (wcslen(console_names[i])==length && _wcsnicmp(value,console_names[i],length)==0) return true;
    return false;
}
inline void console_write(uint64_t object, const wchar_t* text) {
    int32_t length=static_cast<int32_t>(wcsnlen_s(text,32769));
    ConsoleString value{text,length+1,length+1};
    console_output(reinterpret_cast<void*>(object),&value);
}
static void __fastcall console_command_hook(void* object,const ConsoleString* text) {
    // Only the owner thread may touch the queue or session-specific state.
    if (GetCurrentThreadId()==command_thread.load() && reinterpret_cast<uint64_t>(object)==command_console.load() &&
        text && text->data && text->count>0 && text->count<=4097 && text->capacity>=text->count &&
        text->data[text->count-1]==0) {
        const wchar_t* value=text->data;
        while (*value==L' ' || *value==L'\t') ++value;
        if (sdk_console_command(value)) {
            if (console_count<16) {
                wcscpy_s(console_queue[(console_head+console_count)%16],value);
                ++console_count;
                console_write(reinterpret_cast<uint64_t>(object),value);
            } else {
                ++console_dropped;
                console_write(reinterpret_cast<uint64_t>(object),L"SDK command queue full; command rejected.");
            }
            return;
        }
    }
    console_original_command(object,text);
}
inline bool install_console_commands(uint64_t base,uint64_t object) {
    uint64_t table=base+0x7818778;
    if (local_read<uint64_t>(object)!=table || local_read<uint64_t>(table+0x2c8)!=base+0x3dc4d30 ||
        local_read<uint64_t>(table+0x2d8)!=base+0x3dde5a0) return false;
    if (!console_original_command) {
        std::memcpy(console_shadow,reinterpret_cast<void*>(table-8),sizeof(console_shadow));
        console_original_command=reinterpret_cast<ConsoleTextFn>(base+0x3dc4d30);
        console_output=reinterpret_cast<ConsoleTextFn>(base+0x3dde5a0);
        console_shadow[1+0x2c8/8]=reinterpret_cast<uint64_t>(&console_command_hook);
    }
    command_console=object; command_table=table; command_thread=GetCurrentThreadId();
    console_head=console_count=console_dropped=0;
    console_name_count=0;
    if (InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(object),console_shadow+1,
            reinterpret_cast<void*>(table))!=reinterpret_cast<void*>(table)) { command_console=0; return false; }
    return true;
}
inline bool remove_console_commands(uint64_t object,bool shutting_down) {
    bool success=true;
    if (!shutting_down && object) {
        void* old=InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(object),
            reinterpret_cast<void*>(command_table),console_shadow+1);
        success=old==console_shadow+1 || old==reinterpret_cast<void*>(command_table);
    }
    command_console=0; console_head=console_count=console_dropped=0;
    console_name_count=0;
    // Code and shadow storage remain pinned for any prefetched virtual call.
    return success;
}
inline bool poll_console_command(wchar_t (&text)[32769]) {
    if (!console_count) { text[0]=0; return false; }
    wcscpy_s(text,console_queue[console_head]);
    console_head=(console_head+1)%16; --console_count;
    return true;
}
