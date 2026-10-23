#pragma once
#include "target_owned_text.h"
#include "console_colors/target_owned_text_bridge.h"
#include "console_colors/target_fingerprints.h"
#include <bcrypt.h>
#include "console_colors/callback_cpp_guard.h"
#pragma comment(lib,"bcrypt.lib")
static bool lifetime_valid();
namespace ConsoleColorsRuntime {
using namespace ConsoleNativeTarget;
static Api api;
static RenderStorage storage;
static std::uintptr_t owner_console=0;
static std::uint64_t owner_generation=0;
static bool initialized=false,unsupported=false,disabled=false;
static bool fallback_started=false;
static std::uint64_t frames=0,fallbacks=0,faults=0;
inline bool copy(std::uintptr_t at,void* out,std::size_t n){
 if(!at || !out || !n || n>1048576)return false;
 __try{std::memcpy(out,reinterpret_cast<const void*>(at),n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
inline bool span(std::uintptr_t at,std::size_t n){
 if(!at || !n || n>65538 || at>UINTPTR_MAX-n)return false;
 const auto end=at+n;while(at<end){MEMORY_BASIC_INFORMATION m{};if(!VirtualQuery(reinterpret_cast<void*>(at),&m,sizeof(m)) || m.State!=MEM_COMMIT || (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;const auto next=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize;if(next<=at)return false;at=next;}return true;
}
inline bool verify(std::uintptr_t base){
 // Pointer/module bounds and full helper bytes are checked before calling any
 // new target helper. No executable allocation or writable engine code exists.
 IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
 if(!copy(base,&dos,sizeof(dos)) || dos.e_magic!=IMAGE_DOS_SIGNATURE || dos.e_lfanew<=0 || dos.e_lfanew>1048576 || !copy(base+std::uintptr_t(dos.e_lfanew),&nt,sizeof(nt)) || nt.Signature!=IMAGE_NT_SIGNATURE || nt.OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC || nt.OptionalHeader.SizeOfImage!=166776832)return false;
 BCRYPT_ALG_HANDLE hash=nullptr;if(BCryptOpenAlgorithmProvider(&hash,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;
 bool valid=true;
 for(const auto& item:fingerprints){
  if(item.rva>=nt.OptionalHeader.SizeOfImage || item.size>nt.OptionalHeader.SizeOfImage-item.rva){valid=false;break;}
  unsigned char digest[32]{};
  if(BCryptHash(hash,nullptr,0,reinterpret_cast<PUCHAR>(base+item.rva),item.size,digest,32)<0 || std::memcmp(digest,item.sha.data(),32)){valid=false;break;}
 }
 BCryptCloseAlgorithmProvider(hash,0);return valid;
}
inline void status(e33_console_color::Packet& out){
 out=e33_console_color::Packet{};out.native_version=E33_RUNTIME_CINEMATIC_VERSION;
 out.bound=initialized?1u:0u;out.disabled=disabled?1u:0u;out.unsupported=unsupported?1u:0u;
 out.frames=frames;out.fallbacks=fallbacks;out.faults=faults;
}
inline void fallback(void* console,void* canvas){fallback_started=true;++fallbacks;console_original_render(console,canvas);}
inline void run(void* console,void* canvas){
 fallback_started=false;storage.emitted=false;
 try {
  const auto address=reinterpret_cast<std::uintptr_t>(console);
  // All new rendering work requires current strong console ownership, exact
  // current Session generation, the existing attachment check and GC readiness.
  if(!runtime_base || !lease_session || disabled || unsupported || GetCurrentThreadId()!=command_thread.load() || command_console.load()!=address || attached_console!=address || !lifetime_valid() || !attachment_valid(runtime_base) || !TargetOwnedTextOps{runtime_base}.can_create()){fallback(console,canvas);return;}
  if((owner_console && owner_console!=address) || (owner_generation && owner_generation!=lease_session)){
   if(storage.item_state!=State::Empty || storage.temporary_state!=State::Empty){disabled=true;fallback(console,canvas);return;}
  }
  owner_console=address;owner_generation=lease_session;
  if(!initialized){
   const Reader reader{copy,span};const VerifiedImage proof{runtime_base,verify};
   api=bind(proof,reader);
   if(!bind_owned_text(api,runtime_base) || !api.ready()){unsupported=true;fallback(console,canvas);return;}
   api.original=fallback; // Adapter fallback must share the no-replay marker.
   initialized=true;
  }
  const Authority authority{true,true,true,true,true};Captured captured;
  if(!capture(authority,VerifiedImage{runtime_base,verify},Reader{copy,span},api,address,reinterpret_cast<std::uintptr_t>(canvas),captured)){fallback(console,canvas);return;}
  storage.emitted=false;if(ConsoleNativeAdapter::render(authority,api,captured.snapshot,storage))++frames;
 }catch(...){
  ++faults;disabled=true;
  // Never replay a partial frame, constructor, move or release. Journal lives
  // in the pinned native module and preserves Unknown entries indefinitely.
  if(!storage.emitted && !fallback_started)fallback(console,canvas);
 }
 }
inline void run_cpp_guard(void* console,void* canvas) noexcept {
 ConsoleCallbackBoundary::contain_cpp([&]{run(console,canvas);},[]{++faults;disabled=true;});
}
inline void original_cpp_guard(void* console,void* canvas) noexcept {
 // Wrong-thread exceptions are contained without writing GT-owned state.
 ConsoleCallbackBoundary::contain_cpp([&]{console_original_render(console,canvas);},[]{});
}
}
static void __fastcall console_color_render(void* console,void* canvas){
 // An unexpected rendering thread delegates without touching GT-only journals,
 // counters or fallback markers. The immutable original address remains pinned.
 if(GetCurrentThreadId()!=command_thread.load()){
  __try{ConsoleColorsRuntime::original_cpp_guard(console,canvas);}__except(EXCEPTION_EXECUTE_HANDLER){}
  return;
 }
 __try {ConsoleColorsRuntime::run_cpp_guard(console,canvas);}
 __except(EXCEPTION_EXECUTE_HANDLER){++ConsoleColorsRuntime::faults;ConsoleColorsRuntime::disabled=true;}
}
