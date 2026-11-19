#pragma once
#include "blueprint_direct_trace.h"
#include "picto_progression.h"
#include "damage_modifier_frame.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <string>

// Scoped observation only. The summary trace owns this collector; it never
// evaluates damage, modifies arguments, constructs FText, or calls gameplay.
// Only detached values leave the callback. File IO occurs in maintenance.
class DamageModifierEvidence {
    struct Row {
        uint64_t sequence{},tick{}; CallIdentity damage{},source{},target{};
        double before{},value{};uint8_t kind{},affects{},reason{};char label[256]{};
    };
    inline static std::array<Row,2048> rows_{};
    inline static size_t used_=0,hook_=0;
    inline static uint64_t base_=0,epoch_=0,sequence_=0,rejected_=0,dropped_=0;
    inline static CallIdentity function_{},owner_{};
    inline static uint64_t parameter_=0;
    inline static DWORD thread_=0;
    inline static wchar_t path_[4096]{};
    static bool named(uint64_t b,uint64_t o,const char* name,const char* package) {
        return call_identity(b,call_capture(b,o)) && exact_name(b,o+24,name) &&
            exact_name(b,local_read<uint64_t>(o+32)+24,package);
    }
    static uint64_t find_function(uint64_t b,uint64_t owner) {
        const auto count=local_read<int32_t>(b+0x9361b84);
        if(count<=0||count>1000000)return 0;
        const auto chunks=local_read<uint64_t>(b+0x9361b70);
        for(int32_t i=0;i<count;++i){
            const auto chunk=local_read<uint64_t>(chunks+uint64_t(i>>16)*8);
            if(!chunk)continue;
            const auto o=local_read<uint64_t>(chunk+uint64_t(i&65535)*24);
            if(o && local_read<uint64_t>(o+32)==owner && exact_name(b,o+24,"AddDamageModifier"))return o;
        }
        return 0;
    }
    static bool schema(uint64_t b,uint64_t cls,uint64_t fn,uint64_t& parameter) {
        if(!named(b,cls,"BP_BattleDamages_C","/Game/Gameplay/Battle/BP_BattleDamages") ||
           local_read<uint64_t>(fn+32)!=cls || local_read<uint32_t>(fn+0xb0)!=0x0c420000 ||
           local_read<uint16_t>(fn+0xb6)!=40 || local_read<uint16_t>(fn+0xb8)!=65535 ||
           local_read<uint64_t>(fn+0xd8)!=b+0x13937a0)return false;
        parameter=local_read<uint64_t>(fn+0x50);
        if(!parameter || local_read<uint64_t>(parameter+0x18) ||
           !exact_name(b,parameter+0x20,"Modifier") ||
           !exact_name(b,local_read<uint64_t>(parameter+8),"StructProperty") ||
           local_read<uint64_t>(parameter+0x10)!=(fn|1) ||
           local_read<uint64_t>(parameter+0x38)!=0x8000008000196ULL ||
           local_read<int32_t>(parameter+0x44)!=0 || local_read<int32_t>(parameter+0x34)!=40 ||
           local_read<int32_t>(parameter+0x30)!=1)return false;
        const auto type=local_read<uint64_t>(parameter+0x70);
        if(!named(b,type,"FDamageModifier","/Game/Gameplay/Battle/DamageSystem/FDamageModifier") || local_read<int32_t>(type+0x58)!=40)return false;
        const char* names[]={"Type_17_D3D597A64DBB288779AA699F7B627BFD","Value_8_90791EB54DF7200DA70444A0DFA79837",
            "AffectsBaseDamages_15_09C518CB4346167AA68220911465BAE9","Reason_6_E012904D400F0ED9CCE0808686489561"};
        const char* kinds[]={"ByteProperty","DoubleProperty","BoolProperty","TextProperty"};
        const int offsets[]={0,8,16,24},widths[]={1,8,1,16};
        auto prop=local_read<uint64_t>(type+0x50);
        for(unsigned i=0;i<4;++i){
            if(!prop||!exact_name(b,prop+0x20,names[i])||!exact_name(b,local_read<uint64_t>(prop+8),kinds[i])||
               local_read<uint64_t>(prop+0x10)!=(type|1)||local_read<int32_t>(prop+0x44)!=offsets[i]||
               local_read<int32_t>(prop+0x34)!=widths[i]||local_read<int32_t>(prop+0x30)!=1)return false;
            if(i==2&&local_read<uint32_t>(prop+0x70)!=0xff010001)return false;
            prop=local_read<uint64_t>(prop+0x18);
        }
        if(prop)return false;
        const char* field_names[]={"CurrentInputDamages_Base","SourceCharacter","TargetCharacter","DamageReason"};
        const char* field_types[]={"DoubleProperty","ObjectProperty","ObjectProperty","ByteProperty"};
        const int field_offsets[]={736,752,760,773},field_widths[]={8,8,8,1};
        for(unsigned i=0;i<4;++i){bool found=false;unsigned walked=0;
            for(auto f=local_read<uint64_t>(cls+0x50);f&&++walked<=512;f=local_read<uint64_t>(f+0x18)){
                if(!exact_name(b,f+0x20,field_names[i]))continue;
                found=local_read<uint64_t>(f+0x10)==(cls|1)&&exact_name(b,local_read<uint64_t>(f+8),field_types[i])&&
                    local_read<int32_t>(f+0x44)==field_offsets[i]&&local_read<int32_t>(f+0x34)==field_widths[i]&&local_read<int32_t>(f+0x30)==1;
                break;
            }
            if(!found)return false;
        }
        return true;
    }
    static void copy_text(uint64_t text,char(&out)[256]) {
        out[0]=0;
        const auto data=local_read<uint64_t>(text);
        if(!data||local_read<uint64_t>(data)!=base_+0x6da8c78 || local_read<int32_t>(data+8)<=0)return;
        // Audited base-text virtual+28 at 1410baa50: either inline FString
        // at +28 or shared display string +8 through the pointer at +38.
        const auto shared=local_read<uint64_t>(data+0x38),header=shared?shared+8:data+0x28;
        const auto count=local_read<int32_t>(header+8),capacity=local_read<int32_t>(header+12);
        if(count<1||count>128||capacity<count||capacity>4096)return;
        const auto chars=local_read<uint64_t>(header);
        if(!chars||local_read<uint16_t>(chars+uint64_t(count-1)*2))return;
        wchar_t copied[128]{};std::memcpy(copied,reinterpret_cast<const void*>(chars),size_t(count)*2);
        if(!WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,copied,count,out,256,nullptr,nullptr))out[0]=0;
    }
    static void collect_body(void* object,void* frame) {
        // Registry maintenance closes this hook when its owning summary trace
        // expires. A separate deadline would silently stop long, renewed fights.
        if(!hook_||GetCurrentThreadId()!=thread_||
           !call_identity(base_,function_)||!call_identity(base_,owner_)||
           local_read<uint8_t>(base_+0x9272cfc)||local_read<uint8_t>(base_+0x934e968)||local_read<uint8_t>(base_+0x9272cea))return;
        const auto o=reinterpret_cast<uint64_t>(object),f=reinterpret_cast<uint64_t>(frame);
        if(!o||local_read<uint64_t>(o+16)!=owner_.address){++rejected_;return;}
        const auto param=e33_damage_evidence::parameter(target_trace_read,f,function_.address,o,
            local_read<uint64_t>(function_.address+0x60),parameter_,blueprint_direct_frame);
        if(!param){++rejected_;return;}
        Row row{};row.sequence=++sequence_;row.tick=GetTickCount64();row.damage=call_capture(base_,o);
        row.source=call_capture(base_,local_read<uint64_t>(o+752));row.target=call_capture(base_,local_read<uint64_t>(o+760));
        row.before=local_read<double>(o+736);row.reason=local_read<uint8_t>(o+773);
        uint8_t data[40]{};
        if(!target_trace_read(param,data,40)||!e33_damage_evidence::values(data,row.kind,row.value,row.affects)||
           !call_identity(base_,row.damage)||!call_identity(base_,row.source)||!call_identity(base_,row.target)||!std::isfinite(row.before)){++rejected_;return;}
        copy_text(param+24,row.label);
        if(used_==rows_.size()){++dropped_;return;}
        rows_[used_++]=row;
    }
    static void callback(void*,void* object,void* frame,void*) {
        __try{collect_body(object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){++rejected_;}
    }
    static std::string quoted(const char* text) {
        std::string out="\"";
        for(const auto* p=reinterpret_cast<const unsigned char*>(text);*p;++p){
            if(*p=='"'||*p=='\\'){out+='\\';out+=char(*p);}else if(*p>=32)out+=char(*p);
        }
        return out+'"';
    }
    static std::string id(const CallIdentity& value) {
        return '['+std::to_string(value.index)+','+std::to_string(value.serial)+','+std::to_string(value.address)+']';
    }
    static void status(const char* event,bool enabled) {
        if(!path_[0])return;
        auto file=CreateFileW(path_,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(file==INVALID_HANDLE_VALUE)return;
        auto line="{\"event\":"+quoted(event)+",\"pid\":"+std::to_string(GetCurrentProcessId())+",\"epoch\":"+std::to_string(epoch_)+
            ",\"enabled\":"+(enabled?"true":"false")+",\"rejected\":"+std::to_string(rejected_)+",\"dropped\":"+std::to_string(dropped_)+"}\n";
        DWORD written=0;WriteFile(file,line.data(),static_cast<DWORD>(line.size()),&written,nullptr);CloseHandle(file);
    }
    static bool arm(uint64_t base,CallIdentity owner) {
        __try{
            const auto fn=find_function(base,owner.address);
            if(!fn||!schema(base,owner.address,fn,parameter_))return false;
            function_=call_capture(base,fn);
            if(!function_.address||!BlueprintDirectTrace::retain_modifier(base,fn))return false;
            hook_=e33_trace::TraceSlots<>::install(reinterpret_cast<void* volatile*>(fn+0xd8),
                reinterpret_cast<e33_trace::Entry>(base+0x13937a0),callback,nullptr,true,false);
            if(!hook_){BlueprintDirectTrace::release_modifier();return false;}
        }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
        return true;
    }
public:
    static bool begin(uint64_t base,CallIdentity owner) {
        if(hook_)return base_==base && owner_.address==owner.address;
        base_=base;owner_=owner;thread_=GetCurrentThreadId();epoch_=GetTickCount64();sequence_=rejected_=dropped_=0;used_=0;
        wchar_t exe[4096]{};const auto n=GetModuleFileNameW(nullptr,exe,4096);
        if(n&&n<4096){auto* slash=wcsrchr(exe,L'\\');if(slash)*slash=0;
            std::wstring candidate=std::wstring(exe)+L"\\..\\..\\..\\SDK\\logs\\damage-modifiers.jsonl";
            if(!GetFullPathNameW(candidate.c_str(),4096,path_,nullptr))path_[0]=0;}
        const bool armed=arm(base,owner);status("capture_started",armed);return armed;
    }
    static void flush() {
        if(!used_||!path_[0]||GetCurrentThreadId()!=thread_)return;
        auto file=CreateFileW(path_,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(file==INVALID_HANDLE_VALUE)return;
        for(size_t i=0;i<used_;++i){const auto& r=rows_[i];char numbers[256]{};
            std::snprintf(numbers,sizeof(numbers),",\"before\":%.17g,\"value\":%.17g,\"kind\":%u,\"affects_base\":%u,\"damage_reason\":%u",r.before,r.value,unsigned(r.kind),unsigned(r.affects),unsigned(r.reason));
            auto line="{\"pid\":"+std::to_string(GetCurrentProcessId())+",\"epoch\":"+std::to_string(epoch_)+",\"sequence\":"+std::to_string(r.sequence)+",\"tick\":"+std::to_string(r.tick)+
                ",\"damage\":"+id(r.damage)+",\"source\":"+id(r.source)+",\"target\":"+id(r.target)+numbers+",\"reason\":"+quoted(r.label)+",\"rejected\":"+std::to_string(rejected_)+",\"dropped\":"+std::to_string(dropped_)+"}\n";
            DWORD written=0;if(!WriteFile(file,line.data(),static_cast<DWORD>(line.size()),&written,nullptr)||written!=line.size()){
                dropped_+=used_-i;break;
            }
        }
        CloseHandle(file);used_=0;
    }
    static void close() {
        flush();if(hook_){e33_trace::TraceSlots<>::detach(hook_);status("capture_ended",false);}
        hook_=0;BlueprintDirectTrace::release_modifier();
    }
};
