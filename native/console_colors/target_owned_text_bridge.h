#pragma once
// Include after the shared native target_owned_text.h and runtime reader helpers.
#include "target_adapter.h"
namespace ConsoleNativeTarget {
static std::uintptr_t text_binding_base=0;
inline bool text_create_ready(){return text_binding_base && TargetOwnedTextOps{std::uint64_t(text_binding_base)}.can_create();}
inline bool text_release_ready(){return text_binding_base && TargetOwnedTextOps{std::uint64_t(text_binding_base)}.can_release();}
inline bool known_text_value(const ConsoleNativeAdapter::Text& text){
 TargetTextValue value{};std::memcpy(&value,&text,sizeof(value));
 return text_binding_base && TargetOwnedTextOps{std::uint64_t(text_binding_base)}.known_text(value);
}
inline void release_text_value(ConsoleNativeAdapter::Text& text){
 TargetTextValue value{};std::memcpy(&value,&text,sizeof(value));
 TargetOwnedTextOps ops{std::uint64_t(text_binding_base)};
 if(!ops.can_release() || !ops.known_text(value))throw std::runtime_error("Console FText release context changed");
 ops.release(value);
}
inline bool known_text_item(const void* item){
 const auto p=reinterpret_cast<std::uint64_t>(item);
 return text_binding_base && local_read<std::uint64_t>(p)==text_binding_base+0x71caea8 &&
  known_text_value(*reinterpret_cast<const ConsoleNativeAdapter::Text*>(static_cast<const std::byte*>(item)+0x198));
}
inline bool bind_owned_text(Api& api,std::uintptr_t base){
 if(!base || (text_binding_base && text_binding_base!=base))return false;
 text_binding_base=base;api.can_create=text_create_ready;api.can_release=text_release_ready;
 api.known_text=known_text_value;api.release_text=release_text_value;api.known_item=known_text_item;return true;
}
}
